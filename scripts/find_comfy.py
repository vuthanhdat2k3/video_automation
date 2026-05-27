#!/usr/bin/env python3
import paramiko

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"

def run_cmd(ssh, cmd):
    print(f"\n[+] Running: {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='ignore')
    err = stderr.read().decode('utf-8', errors='ignore')
    if out:
        print(f"[STDOUT]:\n{out}")
    if err:
        print(f"[STDERR]:\n{err}")

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASS,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30
        )
        print("[+] Connected!")
        run_cmd(ssh, "ls -la /")
        run_cmd(ssh, "ls -la /root")
        run_cmd(ssh, "find / -name \"main.py\" -maxdepth 4 2>/dev/null")
        run_cmd(ssh, "find / -name \"ComfyUI\" -type d -maxdepth 4 2>/dev/null")
        run_cmd(ssh, "ps aux | grep python")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh.close()

if __name__ == "__main__":
    main()
