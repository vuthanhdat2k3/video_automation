#!/usr/bin/env python3
# ==============================================================================
# Script: remote_ssh_setup.py
# Description: Connects to the remote ckey GPU server via SSH and executes
#              the setup_remote_gpu.sh script.
# Author: Antigravity AI Assistant
# ==============================================================================

import os
import sys
import paramiko

# Remote details
SSH_HOST = "n1.ckey.vn"
SSH_PORT = 3328
SSH_USER = "root"
SSH_PASS = "12345678"

LOCAL_SCRIPT_PATH = "/home/dat/pipeline/video_automation/scripts/setup_remote_gpu.sh"
REMOTE_SCRIPT_PATH = "/tmp/setup_remote_gpu.sh"

def main():
    print("=" * 80)
    print("AI REMOTE GPU AUTOMATED SETUP PROCESS STARTED")
    print("=" * 80)
    
    if not os.path.exists(LOCAL_SCRIPT_PATH):
        print(f"[-] Error: Local script not found at {LOCAL_SCRIPT_PATH}")
        sys.exit(1)
        
    print(f"[+] Connecting to SSH {SSH_HOST}:{SSH_PORT} as {SSH_USER}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=60,
            banner_timeout=60.0,
            auth_timeout=60.0
        )
        print("[+] SSH Connection established successfully!")
        
        # 1. Uploading setup script via SFTP
        print("[+] Initializing SFTP Client...")
        sftp = ssh.open_sftp()
        print(f"[+] Uploading setup script: {LOCAL_SCRIPT_PATH} -> {REMOTE_SCRIPT_PATH}...")
        sftp.put(LOCAL_SCRIPT_PATH, REMOTE_SCRIPT_PATH)
        sftp.close()
        print("[+] Upload completed successfully!")
        
        # 2. Executing setup script on remote server
        print("[+] Executing remote setup script. This might take 5-10 minutes to download all AI models...")
        print("[+] Real-time Remote Logs:\n" + "-"*80)
        
        # Make executable and run
        cmd = f"chmod +x {REMOTE_SCRIPT_PATH} && {REMOTE_SCRIPT_PATH}"
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.get_pty() # Request pseudo-terminal to get colored output and flush buffers
        channel.exec_command(cmd)
        
        # Stream output in real-time
        while True:
            if channel.recv_ready():
                data = channel.recv(1024).decode('utf-8', errors='ignore')
                sys.stdout.write(data)
                sys.stdout.flush()
            if channel.recv_stderr_ready():
                data_err = channel.recv_stderr(1024).decode('utf-8', errors='ignore')
                sys.stderr.write(data_err)
                sys.stderr.flush()
            if channel.exit_status_ready():
                break
                
        # Flush remaining output
        while channel.recv_ready():
            data = channel.recv(1024).decode('utf-8', errors='ignore')
            sys.stdout.write(data)
            sys.stdout.flush()
            
        exit_code = channel.get_exit_status()
        print("-" * 80)
        
        if exit_code == 0:
            print("[+] REMOTE SETUP COMPLETED SUCCESSFULLY!")
        else:
            print(f"[-] Error: Remote script failed with exit code: {exit_code}")
            sys.exit(exit_code)
            
    except Exception as e:
        print(f"[-] SSH Error occurred: {e}")
        sys.exit(1)
    finally:
        ssh.close()
        print("[+] Connections closed.")
        print("=" * 80)

if __name__ == "__main__":
    main()
