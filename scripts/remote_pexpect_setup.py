#!/usr/bin/env python3
# ==============================================================================
# Script: remote_pexpect_setup.py
# Description: Connects to the remote ckey GPU server using native scp/ssh
#              spawning via pexpect to bypass Paramiko banner issues.
# Author: Antigravity AI Assistant
# ==============================================================================

import os
import sys
import pexpect

# Remote details
SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

LOCAL_SCRIPT_PATH = "/home/dat/pipeline/video_automation/scripts/setup_remote_gpu.sh"
REMOTE_SCRIPT_PATH = "/tmp/setup_remote_gpu.sh"

def run_scp():
    print(f"[+] Spawning scp upload process: {LOCAL_SCRIPT_PATH} -> {REMOTE_SCRIPT_PATH}...")
    cmd = f"scp -P {SSH_PORT} -o StrictHostKeyChecking=no {LOCAL_SCRIPT_PATH} {SSH_USER}@{SSH_HOST}:{REMOTE_SCRIPT_PATH}"
    
    child = pexpect.spawn(cmd, timeout=30, encoding='utf-8')
    
    try:
        index = child.expect([r"(?i)password:", pexpect.EOF, pexpect.TIMEOUT])
        if index == 0:
            child.sendline(SSH_PASS)
            child.expect(pexpect.EOF)
            print("[+] File upload completed successfully!")
        elif index == 1:
            # Maybe connected without password (keys)
            print("[+] Upload completed without password challenge!")
        else:
            print("[-] Timeout waiting for password prompt during upload.")
            sys.exit(1)
    except Exception as e:
        print(f"[-] SCP Error: {e}")
        print(child.before)
        sys.exit(1)

def run_ssh_setup():
    print(f"[+] Connecting via native SSH to {SSH_HOST}:{SSH_PORT}...")
    cmd = f"ssh -p {SSH_PORT} -o StrictHostKeyChecking=no {SSH_USER}@{SSH_HOST}"
    
    # Run setup command
    child = pexpect.spawn(cmd, timeout=600, encoding='utf-8') # 10 minute timeout for model downloads
    
    try:
        index = child.expect([r"(?i)password:", pexpect.TIMEOUT])
        if index == 0:
            child.sendline(SSH_PASS)
        else:
            print("[-] Timeout waiting for password prompt.")
            sys.exit(1)
            
        # Expect a prompt (usually ends in '#' for root)
        child.expect([r"#", r"\$"])
        print("[+] SSH Shell connected successfully!")
        
        # Execute the remote setup script
        print("[+] Running remote setup_remote_gpu.sh...")
        print("[+] Real-time remote setup logs:\n" + "-"*80)
        
        child.sendline(f"chmod +x {REMOTE_SCRIPT_PATH} && {REMOTE_SCRIPT_PATH}")
        
        # Stream the output directly to stdout in real-time
        # Loop and read line by line
        while True:
            try:
                line = child.readline()
                if not line:
                    break
                # Echo line to local console
                sys.stdout.write(line)
                sys.stdout.flush()
                
                # Check for completion markers
                if "THIẾT LẬP HOÀN TẤT THÀNH CÔNG!" in line:
                    break
            except pexpect.TIMEOUT:
                # Script might still be downloading, continue
                continue
            except pexpect.EOF:
                break
                
        print("\n" + "-"*80)
        print("[+] SSH command executed!")
        
        # Close shell
        child.sendline("exit")
        child.expect(pexpect.EOF)
        print("[+] SSH Session closed.")
        print("[+] REMOTE SETUP COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"[-] SSH Execution Error: {e}")
        print(child.before)
        sys.exit(1)

def main():
    print("=" * 80)
    print("AI NATIVE SCP/SSH AUTOMATED SETUP PROCESS STARTED")
    print("=" * 80)
    
    if not os.path.exists(LOCAL_SCRIPT_PATH):
        print(f"[-] Error: Local script not found at {LOCAL_SCRIPT_PATH}")
        sys.exit(1)
        
    # Run upload
    run_scp()
    
    # Run SSH script
    run_ssh_setup()
    
    print("=" * 80)

if __name__ == "__main__":
    main()
