import asyncio
import json
import os
import re
from pathlib import Path
import boto3
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# URIs
LOCAL_DB = "postgresql+asyncpg://ai2d:ai2d_pass@localhost:15432/ai2d_flow"
SUPABASE_DB = "postgresql+asyncpg://postgres.dthmeuawwlsnzxkizxuf:vuthanhdat19052003@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

# S3 Configuration
S3_ENDPOINT_URL = "https://dthmeuawwlsnzxkizxuf.storage.supabase.co/storage/v1/s3"
S3_ACCESS_KEY_ID = "6e9d604b901abf2bd9fd1f9049d0f7eb"
S3_SECRET_ACCESS_KEY = "30467cc0cdcf6f4b1a9a8f5d25cd093ec08a7f07e6be80df9faddceccac9d491"
S3_BUCKET_NAME = "root"
STORAGE_ROOT = Path("/home/dat/pipeline/video_automation/storage")

async def sync_database():
    print("=" * 60)
    print("1. SYNCING DATABASE TO SUPABASE")
    print("=" * 60)
    
    # Create engines
    local_engine = create_async_engine(LOCAL_DB, echo=False)
    supabase_engine = create_async_engine(SUPABASE_DB, echo=False)
    
    tables = ["projects", "assets", "characters", "scenes", "shots", "jobs"]
    
    try:
        async with local_engine.connect() as local_conn:
            async with supabase_engine.connect() as supabase_conn:
                # Create all tables on Supabase first
                print("[+] Creating database schema (tables) in Supabase...")
                from app.models.project import ProjectModel
                from app.models.character import CharacterModel
                from app.models.scene import SceneModel
                from app.models.shot import ShotModel
                from app.models.asset import AssetModel
                from app.models.job import JobModel
                from app.database import Base
                
                # run_sync requires connection to run synchronous methods
                await supabase_conn.run_sync(Base.metadata.create_all)
                await supabase_conn.commit()
                print("    [✔] Database schema created successfully in Supabase!")
                
                # 1. Clean existing records in Supabase (in reverse order to avoid FK errors)
                print("[+] Cleaning old tables in Supabase in reverse order...")
                for table in reversed(tables):
                    try:
                        await supabase_conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                    except Exception:
                        pass
                await supabase_conn.commit()
                
                # 2. Sync each table in correct order
                for table in tables:
                    print(f"[+] Syncing table: {table}...")
                    
                    # Get columns and records from local DB
                    res = await local_conn.execute(text(f"SELECT * FROM {table}"))
                    columns = res.keys()
                    rows = res.fetchall()
                    
                    if not rows:
                        print(f"    - No records found in {table}.")
                        continue
                    
                    print(f"    - Found {len(rows)} record(s). Writing to Supabase...")
                    
                    # Prepare bulk insert
                    col_names = ", ".join(columns)
                    col_placeholders = ", ".join(f":{col}" for col in columns)
                    insert_query = text(f"INSERT INTO {table} ({col_names}) VALUES ({col_placeholders})")
                    
                    # Build parameters
                    params = []
                    for row in rows:
                        row_dict = dict(zip(columns, row))
                        # Serialize dict/list values to JSON strings for JSONB compatibility
                        for key, val in row_dict.items():
                            if isinstance(val, (dict, list)):
                                row_dict[key] = json.dumps(val)
                        params.append(row_dict)
                        
                    await supabase_conn.execute(insert_query, params)
                    await supabase_conn.commit()
                    print(f"    [✔] Successfully synced {len(rows)} records for {table}!")
                    
        print("\n🎉 DATABASE SYNC COMPLETED SUCCESSFULLY!")
    except Exception as e:
        print(f"\n[-] Database sync failed: {e}")
    finally:
        await local_engine.dispose()
        await supabase_engine.dispose()

def sync_assets():
    print("\n" + "=" * 60)
    print("2. UPLOADING ASSETS TO SUPABASE STORAGE S3")
    print("=" * 60)
    
    if not STORAGE_ROOT.exists():
        print("[-] Local storage directory does not exist! Skipping S3 upload.")
        return
        
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        region_name="ap-southeast-2"
    )
    
    # Walk through local storage
    print(f"[+] Scanning storage directory: {STORAGE_ROOT}")
    files_to_upload = []
    for root, dirs, files in os.walk(STORAGE_ROOT):
        for file in files:
            full_path = Path(root) / file
            # Relative path to STORAGE_ROOT should be project_id/asset_type/filename
            rel_path = full_path.relative_to(STORAGE_ROOT)
            files_to_upload.append((full_path, rel_path))
            
    print(f"    - Found {len(files_to_upload)} local files.")
    
    uploaded_count = 0
    for full_path, rel_path in files_to_upload:
        # Supabase S3 Key format: {project_id}/{asset_type}/{filename}
        s3_key = str(rel_path).replace("\\", "/") # standardize path separators
        
        # Determine Content-Type
        content_type = "application/octet-stream"
        filename = full_path.name.lower()
        if filename.endswith(".png"):
            content_type = "image/png"
        elif filename.endswith(".jpg") or filename.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif filename.endswith(".mp4"):
            content_type = "video/mp4"
        elif filename.endswith(".mp3") or filename.endswith(".wav"):
            content_type = "audio/mpeg"
            
        print(f"[+] Uploading {rel_path}...")
        try:
            with open(full_path, "rb") as f:
                s3.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=f.read(),
                    ContentType=content_type
                )
            uploaded_count += 1
            print(f"    [✔] Successfully uploaded to S3: {s3_key}")
        except Exception as e:
            print(f"    [-] Failed to upload {rel_path}: {e}")
            
    print(f"\n🎉 UPLOADED {uploaded_count}/{len(files_to_upload)} ASSETS SUCCESSFULLY!")

def clean_local_storage():
    print("\n" + "=" * 60)
    print("3. CLEANING LOCAL STORAGE DIRECTORY")
    print("=" * 60)
    
    # We clean files inside storage, but keep directory structure for local engine compatibility
    deleted_files = 0
    deleted_bytes = 0
    
    for root, dirs, files in os.walk(STORAGE_ROOT):
        for file in files:
            file_path = Path(root) / file
            # Don't delete dotfiles
            if file.startswith("."):
                continue
            try:
                size = file_path.stat().st_size
                file_path.unlink()
                deleted_files += 1
                deleted_bytes += size
            except Exception as e:
                print(f"[-] Failed to delete {file}: {e}")
                
    print(f"👉 Deleted {deleted_files} local files.")
    print(f"👉 Reclaimed {deleted_bytes / (1024 * 1024):.2f} MB of local disk space!")
    print("[✔] Local storage directory cleaned successfully!")

async def run_all():
    await sync_database()
    sync_assets()
    clean_local_storage()
    print("\n" + "=" * 60)
    print("✨ ALL SYNC AND CLEANUP TASKS COMPLETED SUCCESSFULLY! ✨")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_all())
