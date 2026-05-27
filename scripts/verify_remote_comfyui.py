#!/usr/bin/env python3
import asyncio
import aiohttp
import sys

COMFYUI_URL = "http://n2.ckey.vn:2256"

async def main():
    print("[+] Waiting for ComfyUI to complete loading custom nodes...")
    async with aiohttp.ClientSession() as session:
        for attempt in range(1, 20):
            await asyncio.sleep(5)
            try:
                async with session.get(f"{COMFYUI_URL}/system_stats", timeout=3) as resp:
                    if resp.status == 200:
                        print(f"[+] ComfyUI is ONLINE (Attempt {attempt})!")
                        break
            except Exception:
                print(f"[*] ComfyUI still loading... (Attempt {attempt}/20)")
                continue
        else:
            print("[-] Timeout waiting for ComfyUI to respond.")
            sys.exit(1)
            
        # Verify custom nodes
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

if __name__ == "__main__":
    asyncio.run(main())
