; Inno Setup script for KherveMol.
;
; Produces Setup_KherveMol_<version>.exe: installs the one-folder PyInstaller
; build under Program Files\KherveMol with a Start-menu entry, an optional
; desktop icon, an optional .kmol association and an uninstaller.
;
; Normally driven by build_release.ps1, which passes /DMyAppVersion=... and
; stages the files in a short path (Inno hits MAX_PATH under a long OneDrive
; path). By hand: pyinstaller KherveMol.spec --noconfirm, then ISCC.exe on
; this file (Inno Setup 6 - https://jrsoftware.org/isinfo.php).
;
; Copyright (C) 2026 Gwilherm Kerherve. GPL-3.0.

#define MyAppName        "KherveMol"
#define MyAppPublisher   "Gwilherm Kerherve"
#define MyAppExeName     "KherveMol.exe"
#ifndef MyAppVersion
  #define MyAppVersion   "0.1"
#endif

[Setup]
AppId={{5C3E8A17-9D24-4B6F-A1E0-7F2B94D6C381}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=Setup_KherveMol_{#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=LICENSE
SetupIconFile=packaging\khervemol.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc_kmol"; Description: "Open .kmol files with {#MyAppName}"; GroupDescription: "File associations:"; Flags: unchecked

[InstallDelete]
; Inno never removes files a newer build dropped, and Python packages
; (numpy, PyQt5, rdkit) are ABI-bound to each other: an upgrade must not leave
; the old _internal tree beside the new one. It is all build output - no user
; data lives under {app}.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\KherveMol\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}";              Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}";    Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";        Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.kmol\OpenWithProgids"; ValueType: string; ValueName: "KherveMol.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc_kmol
Root: HKA; Subkey: "Software\Classes\KherveMol.Document"; ValueType: string; ValueData: "KherveMol Structure"; Flags: uninsdeletekey; Tasks: fileassoc_kmol
Root: HKA; Subkey: "Software\Classes\KherveMol.Document\DefaultIcon"; ValueType: string; ValueData: "{app}\{#MyAppExeName},0"; Tasks: fileassoc_kmol
Root: HKA; Subkey: "Software\Classes\KherveMol.Document\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: fileassoc_kmol
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\shell\open\command"; ValueType: string; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
