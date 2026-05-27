import asyncio
import socket
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_REF = "dthmeuawwlsnzxkizxuf"
PASSWORD = "vuthanhdat19052003"

regions = [
    "ap-southeast-1", # Singapore
    "ap-southeast-2", # Sydney
    "ap-northeast-1", # Tokyo
    "ap-northeast-2", # Seoul
    "ap-south-1",     # Mumbai
    "us-east-1",      # N. Virginia
    "us-east-2",      # Ohio
    "us-west-1",      # N. California
    "us-west-2",      # Oregon
    "eu-west-1",      # Ireland
    "eu-west-2",      # London
    "eu-west-3",      # Paris
    "eu-central-1",   # Frankfurt
    "ca-central-1",   # Canada Central
    "sa-east-1"       # São Paulo
]

async def test_region(region):
    host = f"aws-0-{region}.pooler.supabase.com"
    try:
        # Check DNS resolution
        ip = socket.gethostbyname(host)
        
        # Test connection
        uri = f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{host}:6543/postgres"
        engine = create_async_engine(uri, echo=False)
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[✔] SUCCESS! Connected to {region} ({host}): {res.fetchone()}")
            return uri
    except Exception as e:
        err_msg = str(e)
        if "tenant/user" not in err_msg and "Tenant or user not found" not in err_msg:
            # If the error is not "tenant not found", it means it found the tenant but password/db error, or something else!
            print(f"[-] {region} ({host}) error: {err_msg}")
        else:
            # Tenant not found, ignore
            pass
    return None

async def main():
    print("Scanning Supabase regions to find the correct pooler host...")
    tasks = [test_region(r) for r in regions]
    results = await asyncio.gather(*tasks)
    
    working = [r for r in results if r]
    if working:
        print(f"\n🎉 FOUND WORKING CONNECTION STRING:\n{working[0]}")
    else:
        print("\n[-] No working region found using default aws-0 prefix. Checking if there is any other error...")

if __name__ == "__main__":
    asyncio.run(main())
