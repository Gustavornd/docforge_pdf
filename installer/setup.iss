; ==============================================================================
; Inno Setup Script - DocForge PDF Setup
; Compila um instalador executável profissional (.exe) para distribuição.
; ==============================================================================

#define MyAppName "DocForge PDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Gustavornd"
#define MyAppURL "https://github.com/Gustavornd/docforge_pdf"
#define MyAppExeName "DocForge PDF.exe"
#define MyAppSourceDir "..\dist\DocForge PDF"

[Setup]
AppId={{9F1D8A27-B6E4-4D2A-B962-9842F55756C1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; Permite ao usuário instalar sem privilégios de Administrador ou para Todos os Usuários
PrivilegesRequiredOverridesAllowed=dialog commandline
OutputDir=..\dist_installer
OutputBaseFilename=DocForge_PDF_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "contextmenu"; Description: "Integrar ao menu do botão direito no Windows Explorer (PDFs e Pastas)"; GroupDescription: "Integrações do Windows:"

[Files]
Source: "{#MyAppSourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Registra o menu de contexto no Windows durante a instalação se selecionado
Filename: "{app}\{#MyAppExeName}"; Parameters: "--register-menu"; Flags: runhidden; Tasks: contextmenu
; Oferece abrir o programa ao finalizar
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove o menu de contexto antes de apagar os arquivos
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister-menu"; Flags: runhidden
