import socket
import threading
import time
import pytest
from docforge_pdf.core.ipc_collector import collect_files_via_ipc


def _get_free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_ipc_empty_files_returns_immediately():
    start = time.time()
    is_master, action, files = collect_files_via_ipc(
        action="merge",
        incoming_files=[],
        port=_get_free_port(),
        debounce_seconds=0.4
    )
    elapsed = time.time() - start
    assert is_master is True
    assert action == "merge"
    assert files == []
    assert elapsed < 0.1  # Fast return without waiting debounce


def test_ipc_single_instance_master():
    port = _get_free_port()
    start = time.time()
    is_master, action, files = collect_files_via_ipc(
        action="merge",
        incoming_files=["/test/file1.pdf"],
        port=port,
        debounce_seconds=0.2
    )
    elapsed = time.time() - start
    assert is_master is True
    assert action == "merge"
    assert len(files) == 1
    assert files[0].endswith("file1.pdf")
    assert elapsed >= 0.18  # Waited for debounce


def test_ipc_multi_instance_coordination():
    port = _get_free_port()
    master_result = {}

    def run_master():
        is_master, action, files = collect_files_via_ipc(
            action="merge",
            incoming_files=["/test/master_doc.pdf"],
            port=port,
            debounce_seconds=0.3
        )
        master_result["is_master"] = is_master
        master_result["action"] = action
        master_result["files"] = files

    t = threading.Thread(target=run_master)
    t.start()

    # Give master a moment to bind
    time.sleep(0.08)

    # Client 1 connects and sends file2
    c1_is_master, _, c1_files = collect_files_via_ipc(
        action="merge",
        incoming_files=["/test/client1_doc.pdf"],
        port=port,
        exit_on_client=False
    )
    assert c1_is_master is False
    assert c1_files == []

    # Client 2 connects and sends file3
    time.sleep(0.05)
    c2_is_master, _, c2_files = collect_files_via_ipc(
        action="fast-merge",
        incoming_files=["/test/client2_doc.pdf"],
        port=port,
        exit_on_client=False
    )
    assert c2_is_master is False
    assert c2_files == []

    t.join(timeout=2.0)

    assert master_result["is_master"] is True
    collected = master_result["files"]
    assert len(collected) == 3
    assert any("master_doc.pdf" in f for f in collected)
    assert any("client1_doc.pdf" in f for f in collected)
    assert any("client2_doc.pdf" in f for f in collected)
