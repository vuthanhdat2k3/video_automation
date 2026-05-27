#!/usr/bin/env python3
import paramiko
import time

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)
        
        # 1. Kill s6 service first so it doesn't auto-restart
        print("[+] Stopping comfyui service via s6-svc to prevent auto-restart loop...")
        ssh.exec_command("s6-svc -d /etc/services.d/comfyui || s6-svc -d /var/run/s6/services/comfyui")
        time.sleep(2)
        ssh.exec_command("pkill -9 -f 'python main.py'")
        time.sleep(1)
        
        # 2. Run ComfyUI manually and capture output
        print("[+] Running ComfyUI manually to capture terminal output / traceback...")
        transport = ssh.get_transport()
        channel = transport.open_session()
        channel.exec_command("cd /app && /app/venv/bin/python main.py --listen --port 8188")
        
        # Read output for 15 seconds
        start_time = time.time()
        output_buffer = ""
        
        while time.time() - start_time < 15:
            if channel.recv_ready():
                data = channel.recv(4096).decode('utf-8', errors='ignore')
                output_buffer += data
                print(data, end="")
            time.sleep(0.5)
            
        print("\n[+] Done reading. Closing session.")
        channel.close()
        
        # 3. Restore s6 service
        print("[+] Restoring comfyui service in s6...")
        ssh.exec_command("s6-svc -u /etc/services.d/comfyui || s6-svc -u /var/run/s6/services/comfyui")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
