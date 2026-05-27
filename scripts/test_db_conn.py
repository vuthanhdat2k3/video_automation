import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

LOCAL_DB = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:15432/ai2d_flow"
SUPABASE_DB = "postgresql+asyncpg://postgres:vuthanhdat19052003@db.dthmeuawwlsnzxkizxuf.supabase.co:5432/postgres"

async def test_conn(name, uri):
    print(f"Testing {name} connection...")
    engine = create_async_engine(uri, echo=False)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print(f"[✔] {name} Connected successfully! Result: {res.fetchone()}")
    except Exception as e:
        print(f"[-] {name} Connection failed: {e}")
    finally:
        await engine.dispose()

async def main():
    await test_conn("Local DB", LOCAL_DB)
    await test_conn("Supabase DB", SUPABASE_DB)

if __name__ == "__main__":
    asyncio.run(main())
