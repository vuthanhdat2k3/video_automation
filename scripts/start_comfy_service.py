#!/usr/bin/env python3
import paramiko
import sys

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def main():
    print("[+] Connecting to start ComfyUI service...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)
        
        print("[+] Starting comfyui service via s6-svc...")
        # Start both potential s6 locations
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui")
        ssh.exec_command("s6-svc -u /var/run/s6/services/comfyui")
        
        print("[+] Service started successfully. Waiting to verify process...")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
