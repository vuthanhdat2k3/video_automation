#!/usr/bin/env python3
# ==============================================================================
# Script: fix_remote_packages.py
# Description: Connects via SSH to the remote ckey server and fixes the python
#              dependency conflicts (downgrading numpy, transformers, accelerate)
#              to make it compatible with PyTorch 2.1.0+cu121.
# Author: Antigravity AI Assistant
# ==============================================================================

import paramiko
import sys
import time

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def main():
    print("=" * 80)
    print("AI REMOTE GPU PACKAGE REPAIR PROCESS")
    print("=" * 80)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=15)
        print("[+] Connected to server.")
        
        # 1. Stop s6 comfyui service to prevent crash restart loop during package installation
        print("[+] Stopping comfyui service via s6-svc...")
        ssh.exec_command("s6-svc -d /etc/services.d/comfyui || s6-svc -d /var/run/s6/services/comfyui")
        time.sleep(2)
        ssh.exec_command("pkill -9 -f 'python main.py'")
        time.sleep(1)
        
        # 2. Run pip install to fix package conflicts
        # Downgrading numpy, transformers, and accelerate to versions compatible with PyTorch 2.1.0
        print("[+] Downgrading numpy, transformers, accelerate, tokenizers in venv (no-deps)...")
        cmd = "/app/venv/bin/pip install --no-deps --force-reinstall \"numpy==1.26.4\" \"transformers==4.40.2\" \"accelerate==0.34.2\" \"diffusers==0.35.0\" \"tokenizers==0.19.1\" \"huggingface-hub==0.23.0\" \"safetensors==0.4.3\""
        
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Read stdout in real-time
        for line in stdout:
            sys.stdout.write("    " + line)
            sys.stdout.flush()
            
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"[-] Pip install failed with exit code: {exit_code}")
            err_data = stderr.read().decode('utf-8')
            print(f"[-] Error details:\n{err_data}")
            sys.exit(1)
            
        print("[+] Packages reinstalled successfully!")
        
        # 3. Restart comfyui service
        print("[+] Restoring comfyui service in s6...")
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui || s6-svc -u /var/run/s6/services/comfyui")
        print("[+] Done! Please wait 30 seconds for ComfyUI to reload.")
        
    except Exception as e:
        print(f"[-] SSH Error occurred: {e}")
        sys.exit(1)
    finally:
        ssh.close()
        print("=" * 80)

if __name__ == "__main__":
    main()
