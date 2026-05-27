import re
from pathlib import Path
from uuid import UUID
import boto3
from app.config import settings


class StorageManager:
    def __init__(self, storage_root: str | Path):
        self.root = Path(storage_root)
        self._s3_client = None

    def _get_s3_client(self):
        if self._s3_client is None and settings.use_s3_storage:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key_id,
                aws_secret_access_key=settings.s3_secret_access_key,
                region_name=settings.s3_region_name or "ap-southeast-2",
            )
        return self._s3_client

    def ensure_project_dirs(self, project_id: UUID) -> None:
        dirs = ["characters", "backgrounds", "props", "keyframes", "audio", "video_clips", "exports"]
        for d in dirs:
            (self.root / str(project_id) / d).mkdir(parents=True, exist_ok=True)

    def save_asset(self, project_id: UUID, asset_type: str, filename: str, data: bytes) -> Path:
        rel_path = Path(asset_type) / filename
        abs_path = self.root / str(project_id) / rel_path

        is_video = asset_type in ("video_clips", "exports") or filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))
        
        uploaded_to_s3 = False
        if settings.use_s3_storage and not is_video:
            try:
                s3 = self._get_s3_client()
                s3_key = f"{project_id}/{asset_type}/{filename}"
                
                content_type = "application/octet-stream"
                if filename.lower().endswith(".png"):
                    content_type = "image/png"
                elif filename.lower().endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif filename.lower().endswith((".mp3", ".wav")):
                    content_type = "audio/mpeg"

                s3.put_object(
                    Bucket=settings.s3_bucket_name,
                    Key=s3_key,
                    Body=data,
                    ContentType=content_type,
                )
                print(f"[✔] Successfully uploaded to S3: {s3_key}")
                uploaded_to_s3 = True
            except Exception as e:
                print(f"[-] S3 upload failed for {filename}: {e}")

        # Chỉ lưu local nếu KHÔNG upload được lên S3 (hoặc là video cần xử lý local)
        if not uploaded_to_s3:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_bytes(data)
            print(f"[✔] Saved locally: {abs_path}")

        return rel_path

    def get_asset_path(self, project_id: UUID, relative_path: str) -> Path:
        path = self.root / str(project_id) / relative_path
        
        # Lazy-load từ S3 nếu file chưa có ở local (FFmpeg/ComfyUI cần file cứng để đọc)
        if not path.exists() and settings.use_s3_storage:
            try:
                s3 = self._get_s3_client()
                s3_key = f"{project_id}/{relative_path}"
                path.parent.mkdir(parents=True, exist_ok=True)
                s3.download_file(settings.s3_bucket_name, s3_key, str(path))
                print(f"[✔] Downloaded missing asset from S3 for local processing: {s3_key}")
            except Exception as e:
                print(f"[-] Failed to download {relative_path} from S3: {e}")
                
        return path

    def get_public_url(self, project_id: UUID, relative_path: str) -> str | None:
        """Get the public Supabase CDN URL for high-speed file streaming."""
        if not settings.use_s3_storage:
            return None
            
        # Videos are stored locally, so return None to force local file streaming
        rel_path_str = str(relative_path).lower()
        is_video = any(v in rel_path_str for v in ("video_clips/", "exports/")) or rel_path_str.endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))
        if is_video:
            return None
            
        # Extract project reference ID from endpoint URL
        match = re.search(r"https://([^.]+)\.storage\.supabase\.co", settings.s3_endpoint_url)
        if not match:
            match = re.search(r"https://([^.]+)\.supabase\.co", settings.s3_endpoint_url)
            
        if match:
            project_ref = match.group(1)
            bucket = settings.s3_bucket_name
            return f"https://{project_ref}.supabase.co/storage/v1/object/public/{bucket}/{project_id}/{relative_path}"
            
        return None

    def delete_asset(self, project_id: UUID, relative_path: str) -> None:
        # 1. Delete locally
        path = self.root / str(project_id) / relative_path
        if path.exists():
            path.unlink()

        # 2. Delete from S3/Supabase if enabled and not a video
        rel_path_str = str(relative_path).lower()
        is_video = any(v in rel_path_str for v in ("video_clips/", "exports/")) or rel_path_str.endswith((".mp4", ".avi", ".mov", ".mkv", ".webm"))
        if settings.use_s3_storage and not is_video:
            try:
                s3 = self._get_s3_client()
                s3_key = f"{project_id}/{relative_path}"
                s3.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
                print(f"[✔] Successfully deleted from S3: {s3_key}")
            except Exception as e:
                print(f"[-] S3 deletion failed for {relative_path}: {e}")
