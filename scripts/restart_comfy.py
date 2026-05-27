#!/usr/bin/env python3
# ==============================================================================
# Script: restart_comfy.py
# Description: Connects via SSH to the remote ckey server and restarts the
#              ComfyUI service by killing the python process. S6-overlay will
#              automatically restart it, scanning the new custom nodes.
# Author: Antigravity AI Assistant
# ==============================================================================

import asyncio
import aiohttp
import paramiko
import sys
import time

SSH_HOST = "n2.ckey.vn"
SSH_PORT = 2254
SSH_USER = "root"
SSH_PASS = "12345678"
COMFYUI_URL = "http://n2.ckey.vn:2256"

def restart_process_via_ssh():
    print("[+] Connecting via SSH to trigger ComfyUI process restart...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(SSH_HOST, SSH_PORT, SSH_USER, SSH_PASS, timeout=10)
        print("[+] Connected! Killing running ComfyUI python process...")
        
        # Kill python process running main.py. S6-overlay will restart it automatically.
        stdin, stdout, stderr = ssh.exec_command("pkill -9 -f 'python main.py'")
        print("[+] Process killed. S6-overlay should restart it shortly.")
        
    except Exception as e:
        print(f"[-] SSH Error: {e}")
        sys.exit(1)
    finally:
        ssh.close()

async def verify_comfyui_reloaded():
    print("[*] Waiting for ComfyUI to reload (checking every 3s)...")
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, 15):
            await asyncio.sleep(3)
            try:
                async with session.get(f"{COMFYUI_URL}/system_stats", timeout=3) as resp:
                    if resp.status == 200:
                        print(f"[+] ComfyUI is BACK ONLINE after {attempt * 3} seconds!")
                        break
            except Exception:
                # Still reloading...
                continue
        else:
            print("[-] Timeout waiting for ComfyUI to come back online.")
            sys.exit(1)
            
        # Verify custom nodes are loaded
        print("[+] Verifying custom nodes have been scanned and loaded...")
        try:
            async with session.get(f"{COMFYUI_URL}/object_info", timeout=5) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    gguf_nodes = [name for name in info.keys() if "GGUF" in name]
                    wan_nodes = [name for name in info.keys() if "WanVideo" in name or "Wan" in name]
                    vhs_nodes = [name for name in info.keys() if "VideoHelperSuite" in name or "VHS_" in name]
                    
                    print("="*80)
                    print("COMFYUI CUSTOM NODES STATUS:")
                    print(f"    - GGUF Nodes: {'LOADED (' + str(len(gguf_nodes)) + ' nodes)' if gguf_nodes else 'NOT FOUND'}")
                    print(f"    - WanVideo Nodes: {'LOADED (' + str(len(wan_nodes)) + ' nodes)' if wan_nodes else 'NOT FOUND'}")
                    print(f"    - VideoHelperSuite Nodes: {'LOADED (' + str(len(vhs_nodes)) + ' nodes)' if vhs_nodes else 'NOT FOUND'}")
                    print("="*80)
                    
                    if gguf_nodes and wan_nodes and vhs_nodes:
                        print("[+] SUCCESS: All custom nodes loaded and ready for Wan2.1 video generation!")
                    else:
                        print("[-] Warning: Some custom nodes might be missing.")
                else:
                    print(f"[-] Failed to fetch object info: status {resp.status}")
        except Exception as e:
            print(f"[-] Error verifying custom nodes: {e}")

def main():
    restart_process_via_ssh()
    # Give s6-overlay a brief moment to register the kill
    time.sleep(2)
    asyncio.run(verify_comfyui_reloaded())

if __name__ == "__main__":
    main()
