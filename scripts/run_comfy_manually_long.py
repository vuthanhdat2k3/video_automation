#!/usr/bin/env python3
import paramiko
import time
import sys

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)
        
        # 1. Stop service
        print("[+] Stopping comfyui service via s6-svc...")
        ssh.exec_command("s6-svc -d /etc/services.d/comfyui || s6-svc -d /var/run/s6/services/comfyui")
        time.sleep(2)
        ssh.exec_command("pkill -9 -f 'python main.py'")
        time.sleep(1)
        
        # 2. Run manually and stream output
        print("[+] Launching ComfyUI manually (60s timeout)...")
        transport = ssh.get_transport()
        channel = transport.open_session()
        # Request a pty so stdout is line-buffered and we see output instantly
        channel.get_pty()
        channel.exec_command("cd /app && /app/venv/bin/python main.py --listen --port 8188")
        
        start_time = time.time()
        while time.time() - start_time < 60:
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8', errors='ignore')
                sys.stdout.write(data)
                sys.stdout.flush()
            if channel.exit_status_ready():
                print(f"\n[!] Process exited with code: {channel.get_exit_status()}")
                break
            time.sleep(0.5)
            
        print("\n[+] Finished manual run. Restoring s6 service...")
        channel.close()
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui || s6-svc -u /var/run/s6/services/comfyui")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
