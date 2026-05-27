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
        
        # 1. Check running python processes
        print("--- Running Python Processes ---")
        stdin, stdout, stderr = ssh.exec_command("ps aux | grep python")
        print(stdout.read().decode('utf-8'))
        
        # 2. Check if there are s6 service logs
        print("--- s6 Service Directory Check ---")
        stdin, stdout, stderr = ssh.exec_command("ls -la /etc/services.d/ /var/log/ 2>/dev/null")
        print(stdout.read().decode('utf-8'))
        
        # 3. Check docker entrypoint or logs if any
        print("--- Log folder files check ---")
        stdin, stdout, stderr = ssh.exec_command("find /var/log -type f -mmin -10 2>/dev/null")
        print(stdout.read().decode('utf-8'))
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
