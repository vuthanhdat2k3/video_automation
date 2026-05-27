import asyncio
import socket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_REF = "dthmeuawwlsnzxkizxuf"
PASSWORD = "vuthanhdat19052003"

regions = ["ap-southeast-1", "ap-southeast-2", "ap-northeast-1", "ap-northeast-2", "us-east-1", "us-east-2", "us-west-1", "us-west-2", "eu-central-1", "eu-west-1"]
prefixes = ["aws-0", "gcp-0", "aws-1", "gcp-1"]

async def test_combination(prefix, region):
    host = f"{prefix}-{region}.pooler.supabase.com"
    try:
        # Check DNS first
        ip = socket.gethostbyname(host)
        
        # Test connection
        uri = f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{host}:6543/postgres"
        engine = create_async_engine(uri, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[✔] SUCCESS! Connected to {host}: {res.fetchone()}")
            return uri
    except Exception as e:
        err_msg = str(e)
        if "tenant/user" not in err_msg and "Tenant or user not found" not in err_msg and "getaddrinfo failed" not in err_msg:
            print(f"[-] {host} matched, but connection failed: {err_msg}")
            return f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{host}:6543/postgres"
    return None

async def main():
    print("Scanning combinations of prefix and region...")
    tasks = []
    for prefix in prefixes:
        for region in regions:
            tasks.append(test_combination(prefix, region))
            
    results = await asyncio.gather(*tasks)
    working = [r for r in results if r]
    if working:
        print(f"\n🎉 FOUND WORKING CONNECTION STRING:\n{working[0]}")
    else:
        print("\n[-] No working combination found.")

if __name__ == "__main__":
    asyncio.run(main())
