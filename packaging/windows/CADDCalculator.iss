; Inno Setup 6 script for the Windows installer (ADR-0022, distribution slice d3).
; It wraps the standalone folder that packaging/build.py makes, so it's compiled by
;   uv run python packaging/build.py --installer
; which passes the defines below to ISCC. Don't compile it by hand without them.
;
; A per-user install by default: no admin rights, into %LOCALAPPDATA%\Programs. Users
; may choose a per-machine install instead (the installer asks, or /ALLUSERS).

#ifndef SourceDir
  #error SourceDir must name the built app folder (packaging/build.py --installer)
#endif
#ifndef AppVersion
  #error AppVersion must be the app's version
#endif
#ifndef NumericVersion
  #error NumericVersion must be the version as four numbers
#endif
#ifndef IconFile
  #error IconFile must name the executable's .ico
#endif
#ifndef OutputDir
  #error OutputDir must name where the installer is written
#endif
#ifndef OutputBase
  #error OutputBase must name the installer's file, without .exe
#endif

#define AppName "CADD Calculator"
#define AppExe "CADDCalculator.exe"

[Setup]
; The AppId never changes: it's how Windows knows a new version upgrades this app.
AppId={{B2EF94B1-E799-438B-AEF3-A34EFB0048A2}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=CADD Calculator contributors
AppPublisherURL=https://github.com/inmymoonsuit/CADD-Calculator
AppSupportURL=https://github.com/inmymoonsuit/CADD-Calculator/issues
AppUpdatesURL=https://github.com/inmymoonsuit/CADD-Calculator/releases
VersionInfoVersion={#NumericVersion}
VersionInfoProductVersion={#NumericVersion}
VersionInfoDescription={#AppName} installer
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#SourceDir}\LICENSE.md
SetupIconFile={#IconFile}
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBase}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
