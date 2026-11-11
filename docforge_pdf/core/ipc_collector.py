"""
Módulo de comunicação inter-processos (IPC) para tratar múltiplas instâncias
disparadas pelo Windows Explorer ao selecionar múltiplos arquivos.
"""

import json
import logging
import os
import socket
import sys
import time
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_PORT = 59123
DEFAULT_DEBOUNCE = 0.4  # 400 milissegundos


def _send_payload(sock: socket.socket, payload: dict) -> None:
    data = json.dumps(payload).encode("utf-8") + b"\n"
    sock.sendall(data)


def _read_payload(sock: socket.socket, max_bytes: int = 65536) -> Optional[dict]:
    buffer = b""
    while b"\n" not in buffer:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buffer += chunk
        if len(buffer) > max_bytes:
            break
    if not buffer:
        return None
    line = buffer.split(b"\n")[0].decode("utf-8")
    return json.loads(line)


def collect_files_via_ipc(
    action: str,
    incoming_files: List[str],
    port: int = DEFAULT_PORT,
    debounce_seconds: float = DEFAULT_DEBOUNCE,
    exit_on_client: bool = True
) -> Tuple[bool, str, List[str]]:
    """
    Coordena instâncias via socket TCP local:
    1. Tenta se conectar à porta IPC local.
    2. Se conectar (Mestre já existe):
       - Envia {action, files} via JSON.
       - Espera ACK.
       - Encerra o processo (sys.exit(0) se exit_on_client=True).
    3. Se não conseguir conectar:
       - Torna-se a instância Mestre e abre o socket de escuta.
       - Acumula incoming_files.
       - Inicia temporizador de debounce (400ms padrão).
       - A cada nova conexão recebida, incorpora os arquivos e reinicia o debounce.
       - Quando o debounce expira sem novas conexões, fecha o socket e retorna a lista completa.

    Retorna:
      (is_master: bool, resolved_action: str, collected_files: List[str])
    """
    # Normalizar caminhos dos arquivos de entrada
    normalized_files: List[str] = [os.path.abspath(f) for f in incoming_files if f]

    # Se a lista de arquivos for vazia (abertura normal do aplicativo pela interface),
    # não precisamos iniciar socket nem esperar debounce de instâncias de Explorer.
    if not normalized_files:
        return True, action, []

    payload = {
        "action": action,
        "files": normalized_files
    }

    max_attempts = 5
    for attempt in range(max_attempts):
        # 1. Tentar conectar como Cliente
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.settimeout(0.3)
        try:
            client_sock.connect(("127.0.0.1", port))
            # Conexão bem-sucedida: existe um Mestre ativo!
            _send_payload(client_sock, payload)
            # Aguardar confirmação (ACK)
            _read_payload(client_sock)
            client_sock.close()

            if exit_on_client:
                sys.exit(0)
            return False, action, []
        except (ConnectionRefusedError, socket.timeout, OSError):
            client_sock.close()

        # 2. Conexão falhou: tentar se tornar a instância Mestre
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server_sock.bind(("127.0.0.1", port))
            server_sock.listen(128)
            # Conseguiu bindar: este processo é o MESTRE!
            return _run_master_loop(
                server_sock=server_sock,
                initial_action=action,
                initial_files=normalized_files,
                debounce_seconds=debounce_seconds
            )
        except OSError:
            server_sock.close()
            # Outro processo pode ter acabado de bindar no exato mesmo milissegundo.
            # Aguardar breve pausa antes de tentar se conectar novamente como cliente.
            time.sleep(0.05 * (attempt + 1))

    # Fallback se todas as tentativas falharem (muito improvável)
    return True, action, normalized_files


def _run_master_loop(
    server_sock: socket.socket,
    initial_action: str,
    initial_files: List[str],
    debounce_seconds: float
) -> Tuple[bool, str, List[str]]:
    """
    Executa o loop de escuta do Mestre até que transcorra o período de debounce
    sem nenhuma nova conexão.
    """
    collected: List[str] = list(initial_files)
    seen: set = set(initial_files)
    effective_action = initial_action

    try:
        server_sock.settimeout(debounce_seconds)
        while True:
            try:
                conn, _ = server_sock.accept()
            except socket.timeout:
                # O debounce de 400ms expirou sem novas conexões: encerra a coleta!
                break
            except OSError:
                break

            try:
                conn.settimeout(1.0)
                data = _read_payload(conn)
                if data and isinstance(data, dict):
                    client_files = data.get("files", [])
                    client_action = data.get("action")
                    if client_action and effective_action in (None, "", "merge"):
                        effective_action = client_action

                    for f in client_files:
                        if f not in seen:
                            seen.add(f)
                            collected.append(f)

                    # Enviar ACK
                    _send_payload(conn, {"status": "ok", "count": len(collected)})
            except Exception as e:
                logger.warning(f"Erro ao processar cliente IPC: {e}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    finally:
        try:
            server_sock.close()
        except Exception:
            pass

    return True, effective_action, collected
