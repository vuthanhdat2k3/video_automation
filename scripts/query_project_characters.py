import asyncio
import json
from app.database import async_session_factory
from sqlalchemy import select
from sqlalchemy import text
from app.models.project import ProjectModel
from app.models.character import CharacterModel
from app.models.asset import AssetModel

async def main():
    project_id = "95f0d3b4-0004-44ac-91e4-9261ea576415"
    print(f"Querying project: {project_id}\n")
    
    async with async_session_factory() as db:
        # Get project
        proj_res = await db.execute(select(ProjectModel).where(ProjectModel.id == project_id))
        project = proj_res.scalar_one_or_none()
        if not project:
            print("Project not found in DB!")
            return
            
        print(f"Project Name: {project.name}")
        print(f"Project Style: {project.style}")
        print(f"Project Aspect Ratio: {project.aspect_ratio}")
        print(f"Created At: {project.created_at}")
        print("=" * 60)
        
        # Get characters
        char_res = await db.execute(select(CharacterModel).where(CharacterModel.project_id == project_id))
        characters = char_res.scalars().all()
        print(f"Found {len(characters)} character(s):")
        
        for idx, char in enumerate(characters):
            print(f"\n[{idx+1}] Character Name: {char.name}")
            print(f"    ID: {char.id}")
            print(f"    Role: {char.role}")
            print(f"    Reference Asset ID: {char.reference_asset_id}")
            print(f"    Description: {char.description}")
            print(f"    Prompt: {char.prompt}")
            print("    Character JSON (DNA):")
            print(json.dumps(char.character_json, indent=4, ensure_ascii=False))
            print("-" * 50)
            
        print("=" * 60)
        # Get assets
        asset_res = await db.execute(select(AssetModel).where(AssetModel.project_id == project_id))
        assets = asset_res.scalars().all()
        print(f"Found {len(assets)} asset(s):")
        for asset in assets:
            print(f"Asset ID: {asset.id}")
            print(f"  Type: {asset.type}")
            print(f"  Filename: {asset.filename}")
            print(f"  Path: {asset.path}")
            print(f"  Metadata: {json.dumps(asset.metadata_json, indent=4, ensure_ascii=False)}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
