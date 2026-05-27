#!/usr/bin/env python3
import paramiko

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)
        
        # Check files in models folders
        cmd = "ls -lh /app/models/unet/ /app/models/clip/ /app/models/vae/ /app/models/clip_vision/ 2>/dev/null"
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode('utf-8'))
        
        # Check running aria2c processes
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep aria2c")
        print("--- aria2c process check ---")
        print(stdout.read().decode('utf-8'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
