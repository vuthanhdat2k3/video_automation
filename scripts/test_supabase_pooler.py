import asyncio
import socket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_REF = "dthmeuawwlsnzxkizxuf"
PASSWORD = "vuthanhdat19052003"

async def test_host(host, port=6543):
    print(f"\nTesting resolve of {host}...")
    try:
        ip = socket.gethostbyname(host)
        print(f"[✔] Resolved to IP: {ip}")
        
        # Test sqlalchemy connect
        uri = f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{host}:{port}/postgres"
        print(f"Connecting to pooler: {uri}...")
        engine = create_async_engine(uri, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[✔] Connected successfully! Result: {res.fetchone()}")
            return host, port
    except Exception as e:
        print(f"[-] Failed: {e}")
    return None

async def main():
    hosts = [
        f"aws-0-ap-southeast-2.pooler.supabase.com", # Sydney
        f"aws-0-ap-southeast-1.pooler.supabase.com", # Singapore
        f"aws-0-us-east-1.pooler.supabase.com",      # US East
    ]
    for host in hosts:
        res = await test_host(host, 6543)
        if res:
            print(f"\n🎉 FOUND WORKING POOLER HOST: {res[0]} on port {res[1]}")
            break

if __name__ == "__main__":
    asyncio.run(main())
