[Setup]
AppId=EdgeReader
AppName=EdgeReader
AppVersion=2.0.1
DefaultDirName={localappdata}\Programs\EdgeReader
DefaultGroupName=EdgeReader
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=EdgeReader-2.0.1-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\EdgeReader.exe
[Files]
Source: "dist\EdgeReader-2.0.exe"; DestDir: "{app}"; DestName: "EdgeReader.exe"; Flags: ignoreversion
[Icons]
Name: "{group}\EdgeReader"; Filename: "{app}\EdgeReader.exe"
[Run]
Filename: "{app}\EdgeReader.exe"; Description: "Start EdgeReader"; Flags: nowait postinstall skipifsilent
