#define MyAppName "PyToNingans"
#define MyAppVersion "0.8.2"
#define MyAppPublisher "MetaDusk Inc."
#define MyAppURL "https://github.com/Meta-Dusk/pytoningans"
#define MyAppExeName "PyToNingans.dist\PyToNingans.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".pyto"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
AppId={{F467C371-D29D-489F-83F2-564EDCEDCE26}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=no
DisableProgramGroupPage=yes
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\installer
OutputBaseFilename={#MyAppName}-v{#MyAppVersion}-Win64-Installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\icon.ico
SignTool=signtool
SignedUninstaller=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Types]
Name: "full"; Description: "Full installation"
Name: "custom"; Description: "Custom installation"; Flags: iscustom

[Components]
; The core app is fixed and cannot be unchecked
Name: "core"; Description: "Core Engine Files"; Types: full custom; Flags: fixed

; Modding API package
Name: "mods\api"; Description: "Modding API Package (api/)"; Types: full custom; Flags: fixed

[Files]
; Core Application
Source: "..\build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion; Components: core
Source: "..\cloud_config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist; Components: core

; Modding API
Source: "..\src\pytoningans\core\api\*"; DestDir: "{userdocs}\{#MyAppName}\mods\api"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall; Components: api

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}\PyToNingans.dist"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}\PyToNingans.dist"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent