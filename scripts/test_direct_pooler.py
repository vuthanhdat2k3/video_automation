import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_REF = "dthmeuawwlsnzxkizxuf"
PASSWORD = "vuthanhdat19052003"

async def test_conn(host, port, user="postgres"):
    uri = f"postgresql+asyncpg://{user}:{PASSWORD}@{host}:{port}/postgres"
    print(f"\nTesting connection to {host}:{port} with user {user}...")
    engine = create_async_engine(uri, echo=False)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[✔] Connected successfully! Result: {res.fetchone()}")
            return uri
    except Exception as e:
        print(f"[-] Failed: {e}")
    finally:
        await engine.dispose()
    return None

async def main():
    # Test direct host on pooler port 6543
    await test_conn(f"db.{PROJECT_REF}.supabase.co", 6543, "postgres")
    
    # Test pooler host with user postgres
    await test_conn("aws-0-ap-southeast-2.pooler.supabase.com", 6543, "postgres")
    
    # Test pooler host with user postgres.project_ref
    await test_conn("aws-0-ap-southeast-2.pooler.supabase.com", 6543, f"postgres.{PROJECT_REF}")
    
    # Test ap-southeast-1 (Singapore)
    await test_conn("aws-0-ap-southeast-1.pooler.supabase.com", 6543, f"postgres.{PROJECT_REF}")

if __name__ == "__main__":
    asyncio.run(main())
