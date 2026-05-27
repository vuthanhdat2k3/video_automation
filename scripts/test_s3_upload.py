import asyncio
from uuid import uuid4
from app.services.storage import StorageManager
from app.config import settings

async def main():
    print("Testing Supabase Storage S3 upload...")
    print(f"USE_S3_STORAGE: {settings.use_s3_storage}")
    print(f"S3_ENDPOINT_URL: {settings.s3_endpoint_url}")
    print(f"S3_BUCKET_NAME: {settings.s3_bucket_name}")
    
    storage = StorageManager(settings.storage_root)
    
    project_id = uuid4()
    filename = "test_cloud_upload.png"
    data = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" # mock 1x1 black png bytes
    
    print("\n[+] Triggering save_asset (will save locally and upload to Supabase Storage S3)...")
    try:
        rel_path = storage.save_asset(project_id, "characters", filename, data)
        print(f"\n[✔] save_asset completed. Path in db: {rel_path}")
        
        # Test get_public_url
        public_url = storage.get_public_url(project_id, rel_path)
        print(f"[✔] Compiled Public CDN URL: {public_url}")
        
    except Exception as e:
        print(f"\n[-] Cloud upload failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
