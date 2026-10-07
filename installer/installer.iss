#define MyAppName "PyToNingans"
#define MyAppVersion "0.7.1"
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

; Added a specific component for the API
Name: "mods\api"; Description: "Modding API Base (api.py)"; Types: full custom
Name: "mods\default_mod"; Description: "Include Default Pet Mod"; Types: full custom
Name: "mods\example_mods"; Description: "Include All Example Mods"; Types: full custom

[Files]
; Core Application
Source: "..\build\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: core
Source: "..\assets\icon.ico"; DestDir: "{app}"; Flags: ignoreversion; Components: core

; Modding API
; By listing 'mods\api mods\default_mod mods\example_mods', this file installs if ANY of those three boxes are checked.
Source: "..\src\pytoningans\core\api.py"; DestDir: "{userdocs}\{#MyAppName}\mods"; DestName: "api.py"; Flags: ignoreversion uninsneveruninstall; Components: mods\api mods\default_mod mods\example_mods

; Default Mod
Source: "..\assets\mods\default_pet\*"; DestDir: "{userdocs}\{#MyAppName}\mods\default_pet"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall; Components: mods\default_mod

; Example Mods
Source: "..\assets\mods\*"; DestDir: "{userdocs}\{#MyAppName}\mods"; Flags: ignoreversion recursesubdirs createallsubdirs uninsneveruninstall; Components: mods\example_mods

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}\PyToNingans.dist"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}\PyToNingans.dist"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent