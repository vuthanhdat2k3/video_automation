#!/usr/bin/env python3
# ==============================================================================
# Script: update_remote_comfyui.py
# Description: Connects to the remote ckey server, initializes git in /app,
#              updates ComfyUI core to the latest master branch, resolves
#              the libxcb OpenCV error by installing opencv-python-headless,
#              and re-enforces PyTorch 2.1.0 package compatibility.
# Author: Antigravity AI Assistant
# ==============================================================================

import paramiko
import sys
import time

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def run_commands(ssh, commands):
    for cmd in commands:
        print(f"[+] Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        
        # Stream stdout
        for line in stdout:
            sys.stdout.write("    " + line)
            sys.stdout.flush()
            
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            print(f"[-] Command failed with exit code: {exit_code}")
            err_data = stderr.read().decode('utf-8')
            print(f"[-] Error details:\n{err_data}")
            return False
    return True

def main():
    print("=" * 80)
    print("AI REMOTE GPU COMFYUI CORE UPDATE & REPAIR")
    print("=" * 80)
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=15)
        print("[+] Connected to server.")
        
        # 1. Stop service
        print("[+] Stopping comfyui service via s6-svc to avoid write conflicts...")
        ssh.exec_command("s6-svc -d /etc/services.d/comfyui || s6-svc -d /var/run/s6/services/comfyui")
        time.sleep(2)
        ssh.exec_command("pkill -9 -f 'python main.py'")
        time.sleep(1)
        
        # 2. Update ComfyUI Core
        print("[+] Initializing Git and updating ComfyUI Core to latest...")
        setup_git_cmds = [
            "git config --global --add safe.directory /app",
            "cd /app && git init",
            "cd /app && git remote add origin https://github.com/comfyanonymous/ComfyUI.git || cd /app && git remote set-url origin https://github.com/comfyanonymous/ComfyUI.git",
            "cd /app && git fetch origin",
            "cd /app && git reset --hard origin/master"
        ]
        if not run_commands(ssh, setup_git_cmds):
            print("[-] Failed to update ComfyUI Core.")
            sys.exit(1)
            
        # 3. Upgrade PyTorch to 2.4.0+cu121 to support comfy_kitchen custom ops
        print("[+] Upgrading PyTorch, torchvision, torchaudio to 2.4.0+cu121...")
        pytorch_cmds = [
            "/app/venv/bin/pip install torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 --index-url https://download.pytorch.org/whl/cu121"
        ]
        if not run_commands(ssh, pytorch_cmds):
            print("[-] Failed to upgrade PyTorch.")
            sys.exit(1)

        # 4. Fix OpenCV dependency (opencv-python-headless)
        print("[+] Replacing opencv-python with opencv-python-headless to fix libxcb error...")
        opencv_cmds = [
            "/app/venv/bin/pip uninstall -y opencv-python opencv-python-headless",
            "/app/venv/bin/pip install --no-deps opencv-python-headless"
        ]
        run_commands(ssh, opencv_cmds)
        
        # 5. Install requirements.txt
        print("[+] Running pip install for any new ComfyUI Core dependencies...")
        run_commands(ssh, ["/app/venv/bin/pip install -r /app/requirements.txt"])
        
        # 6. Restart service
        print("[+] Restoring comfyui service in s6...")
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui || ssh.exec_command('s6-svc -u /var/run/s6/services/comfyui')")
        # Ensure it is running by sending -u to both potential locations
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui")
        ssh.exec_command("s6-svc -u /var/run/s6/services/comfyui")
        print("[+] Done! Please wait 30 seconds for ComfyUI to reload.")
        
    except Exception as e:
        print(f"[-] SSH Error occurred: {e}")
        sys.exit(1)
    finally:
        ssh.close()
        print("=" * 80)

if __name__ == "__main__":
    main()
