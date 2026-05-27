import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

PROJECT_REF = "dthmeuawwlsnzxkizxuf"
PASSWORD = "vuthanhdat19052003"
HOST = "aws-1-ap-southeast-2.pooler.supabase.com"

async def test_uri(name, uri):
    print(f"\nTesting {name}...")
    engine = create_async_engine(uri, echo=False)
    try:
        async with engine.connect() as conn:
            # Run multiple queries to trigger prepared statement cache usage
            res1 = await conn.execute(text("SELECT 1"))
            res2 = await conn.execute(text("SELECT 2"))
            print(f"[✔] {name} Connected & Queried successfully! Result: {res2.fetchone()}")
            return True
    except Exception as e:
        print(f"[-] {name} failed: {e}")
    finally:
        await engine.dispose()
    return False

async def main():
    # 1. Test port 5432 on pooler (Session Mode)
    uri_session = f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{HOST}:5432/postgres"
    await test_uri("Session Mode (Port 5432)", uri_session)
    
    # 2. Test port 6543 on pooler with cache_size=0 (Transaction Mode)
    uri_tx = f"postgresql+asyncpg://postgres.{PROJECT_REF}:{PASSWORD}@{HOST}:6543/postgres?prepared_statement_cache_size=0"
    await test_uri("Transaction Mode (Port 6543) with cache_size=0", uri_tx)

if __name__ == "__main__":
    asyncio.run(main())
