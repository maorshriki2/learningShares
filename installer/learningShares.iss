; Windows installer for learningShares desktop (Inno Setup 6).
; 1) Build EXE:  python -m PyInstaller --noconfirm learningSharesDesktop.spec
; 2) Compile:   ISCC.exe installer\learningShares.iss
;    (ISCC default path: C:\Program Files (x86)\Inno Setup 6\ISCC.exe)

#define MyAppName "learningShares"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "learningShares"
#define MyAppExeName "learningSharesDesktop.exe"

[Setup]
AppId={{C8F3A1B2-9D4E-4F60-8A7C-1E2D3F4A5B6C}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/
DefaultDirName={localappdata}\Programs\{#MyAppName}
DisableProgramGroupPage=no
AllowNoIcons=yes
PrivilegesRequired=lowest
OutputDir=..\installer_output
OutputBaseFilename=learningShares-Setup-{#MyAppVersion}
SetupIconFile=
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvPath, ExamplePath: String;
begin
  if CurStep = ssPostInstall then
  begin
    EnvPath := ExpandConstant('{app}\.env');
    ExamplePath := ExpandConstant('{app}\.env.example');
    if (not FileExists(EnvPath)) and FileExists(ExamplePath) then
      CopyFile(ExamplePath, EnvPath, False);
  end;
end;
