from pathlib import Path
from uuid import UUID


class StorageManager:
    def __init__(self, storage_root: str | Path):
        self.root = Path(storage_root)

    def ensure_project_dirs(self, project_id: UUID) -> None:
        dirs = ["characters", "backgrounds", "props", "keyframes", "audio", "video_clips", "exports"]
        for d in dirs:
            (self.root / str(project_id) / d).mkdir(parents=True, exist_ok=True)

    def save_asset(self, project_id: UUID, asset_type: str, filename: str, data: bytes) -> Path:
        rel_path = Path(asset_type) / filename
        abs_path = self.root / str(project_id) / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(data)
        return rel_path

    def get_asset_path(self, project_id: UUID, relative_path: str) -> Path:
        return self.root / str(project_id) / relative_path

    def delete_asset(self, project_id: UUID, relative_path: str) -> None:
        path = self.root / str(project_id) / relative_path
        if path.exists():
            path.unlink()
