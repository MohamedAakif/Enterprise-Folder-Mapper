# Enterprise Folder Mapper

A lightweight Windows desktop application for mapping, removing, and remapping shared network folders through a simple PySide6 interface. Folder names and server details are kept outside the source code in an `.env` configuration file, making the tool reusable across different environments.

<img width="290" height="454" alt="image" src="https://github.com/user-attachments/assets/8e01ffe5-b370-4e6e-b9f1-e3105e8d52b8" />

## Features

- Display an IT-managed list of available shared folders.
- Map one or more selected folders as persistent Windows network drives.
- Automatically choose an available drive letter, starting with the first letter of the share name.
- Detect shares that are already mapped and skip duplicates.
- Remove mapped drives that match the configured remap checklist.
- Replace an old server name with the current file-server hostname and remap matching shares.
- Check TCP port 445 and folder availability before mapping.
- Show success, warning, and failure notifications in the application.

## The Three Options

### 1. Map Selected

1. Select one or more folders from the list.
2. Click **Map Selected**.
3. The application verifies that the configured file server is reachable.
4. Each selected folder is mapped persistently using the first available drive letter.
5. A notification reports mapped, skipped, and failed folders.

A share that is already mapped is skipped rather than mapped again.

### 2. Remove

Click **Remove** to delete mapped network drives whose UNC paths contain a value listed in `remap_checklist`.

> **Important:** This option does not remove every mapped drive on the computer. It only removes mappings matched by the configured checklist.

### 3. Remap

Click **Remap** to:

1. Find existing mapped drives whose UNC paths match `remap_checklist`.
2. Remove those mappings.
3. Replace each matched old server value with `fileserver_hostname`.
4. Map the updated UNC paths persistently using available drive letters.

Use this option during file-server migrations or when users still have mappings that reference an old server name.

## Requirements

- Windows 10 or Windows 11
- Access to the target SMB file server and shared folders
- TCP port 445 available between the workstation and file server
- Appropriate share and NTFS permissions for the signed-in Windows user
- Python 3.10 or later when running from source
- Python packages:
  - `PySide6`
  - `python-dotenv`

The application uses the signed-in user's Windows credentials. It does not collect or store usernames or passwords.

## Project Files

Keep these files together in the same folder:

```text
Enterprise-Folder-Mapper/
├── Folder Mapper.py
├── GUI_Folder Mapper.ui
├── .env
├── requirements.txt
├── folder-mapper-preview.png
└── README.md
```

If distributing a packaged executable, keep the executable, UI file, and `.env` file together:

```text
Enterprise-Folder-Mapper/
├── Folder Mapper.exe
├── GUI_Folder Mapper.ui
└── .env
```

## Configuration

Create a file named `.env` in the same directory as the Python script or packaged executable.

Use the variable names exactly as shown because the current application reads them with the same capitalization:

```dotenv
fileserver_hostname=fileserver01.example.local
FOLDER_NAMES=Accounts,HR,Projects,Public
remap_checklist=oldfileserver01,oldfileserver02
```

### Configuration fields

#### `fileserver_hostname`

The current file-server hostname, without leading backslashes.

```dotenv
fileserver_hostname=fileserver01.example.local
```

The application builds folder paths in this format:

```text
\\fileserver01.example.local\Accounts
```

#### `FOLDER_NAMES`

A comma-separated list of share names to display in the application.

```dotenv
FOLDER_NAMES=Accounts,HR,Projects,Public
```

Each value must be the actual SMB share name. Do not include a full UNC path in this field.

#### `remap_checklist`

A comma-separated list of old server names or identifying text used to find mappings eligible for removal or remapping.

```dotenv
remap_checklist=oldfileserver01,oldfileserver02
```

For safety, use specific old server names. Avoid broad values such as `server`, `share`, or a short domain fragment because any mapped UNC path containing that text could be selected.

### Public `.env.example`

Do not commit the real `.env` file. Add a sanitized `.env.example` instead:

```dotenv
fileserver_hostname=fileserver01.example.local
FOLDER_NAMES=Accounts,HR,Projects,Public
remap_checklist=oldfileserver01,oldfileserver02
```

Copy it locally and rename the copy to `.env` before running the application.

## Installation From Source

1. Clone or download the repository.
2. Open Command Prompt or PowerShell in the project directory.
3. Create a virtual environment:

```powershell
python -m venv .venv
```

4. Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

5. Install the dependencies:

```powershell
pip install -r requirements.txt
```

6. Create `.env` from `.env.example` and update it with your environment settings.

7. Run the application:

```powershell
python "Folder Mapper.py"
```

## Building a Standalone Executable

Install PyInstaller:

```powershell
pip install pyinstaller
```

Create a single-folder executable:

```powershell
pyinstaller --noconfirm --windowed --name "Folder Mapper" "Folder Mapper.py"
```

Generated files:

```text
build/
dist/
```

The executable will be created in:

```text
dist/Folder Mapper/
```

Copy the following files into the same folder as the executable:

```text
Folder Mapper.exe
GUI_Folder Mapper.ui
.env
```

Final folder structure:

```text
Folder Mapper/
├── Folder Mapper.exe
├── GUI_Folder Mapper.ui
└── .env
```

Launch:

```powershell
.\Folder Mapper.exe
```

## Requirements

Example `requirements.txt`:

```text
PySide6>=6.8.0
python-dotenv>=1.0.0
```

## IT Deployment From a Common Folder

IT can place a packaged release in a read-only network share or managed software folder, for example:

```text
\\software-server\Applications\Enterprise-Folder-Mapper\
```

Place these deployment files together:

```text
Folder Mapper.exe
GUI_Folder Mapper.ui
.env
```
Create a shortcut for the .exe file and share across users

Recommended deployment process:

1. Create a dedicated application folder that regular users can read but cannot modify.
2. Place the executable, UI file, and environment file in that folder.
3. Configure `.env` with the approved file-server hostname, share names, and old-server checklist.
4. Test all three actions with a standard user account.
5. Share a shortcut to the executable through the Start menu, desktop, Company Portal package, Group Policy, or another approved endpoint-management method.
6. Update the central copy when the folder list or server hostname changes.

### Network-location consideration

Some Windows security controls may block or warn when an executable is launched directly from a UNC path. If that occurs, deploy the application locally, such as under `C:\Program Files\Enterprise Folder Mapper`, while managing the release through the organization's approved software-distribution platform.

### Per-user behavior

Windows drive mappings created with `net use /persistent:yes` belong to the Windows user context that runs the application. Run the tool as the intended user. Running it under a different administrator account may create the mapping in that account's context instead.

## Security Notes

- Restrict write access to the shared deployment folder so users cannot replace the executable, UI, or configuration.
- Test removal and remapping with non-production sample shares before broad deployment.

## Troubleshooting

### File server is not reachable

- Confirm that `fileserver_hostname` is correct.
- Confirm the workstation is connected to the correct corporate network or VPN.
- Confirm TCP port 445 is allowed.
- Confirm DNS can resolve the hostname.

### Folder does not exist or is unreachable

- Confirm that each `FOLDER_NAMES` value exactly matches an existing SMB share name.
- Confirm that the signed-in user has permission to access the share.
- Test the UNC path manually in File Explorer.

### Nothing is removed or remapped

- Check that `remap_checklist` contains text that appears in the existing mapped UNC paths.
- Run `net use` in Command Prompt to inspect the current mappings.
- Use specific old-server hostnames rather than friendly descriptions.

### The interface does not open

- Confirm that `GUI_Folder Mapper.ui` is in the same directory as the script or executable.
- Confirm the project dependencies are installed when running from source.
- Confirm `.env` exists and includes non-empty `fileserver_hostname` and `FOLDER_NAMES` values.

## Privacy

The application performs local Windows network-drive operations. The current source code does not implement telemetry or remote data collection.
