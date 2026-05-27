import asyncio
import os
import sys
import json
from io import BytesIO
from PIL import Image

# Add root path
sys.path.insert(0, "/home/dat/pipeline/video_automation/apps/api")

from app.services.image_gen import ImageGenService
from ai_2d_shared.character import CharacterDNA

async def main():
    print("Initializing ImageGenService...")
    image_gen = ImageGenService()
    
    dna = CharacterDNA(
        age=20,
        gender="male",
        hair_color="white",
        hair_style="long hair tied in ponytail",
        eye_color="red",
        clothing_style="ancient chinese martial arts robes",
        accessories=["floating glowing blue sword", "jade pendant"],
        distinctive_features=["scar on cheek"]
    )
    
    print("Generating Character Sheet raw (before split)...")
    
    # Generate prompt & raw sheet
    from app.services.character_dna import CharacterDNAService
    from app.services.comfyui.client import ComfyUIClient, WORKFLOW_DIR
    from app.config import settings
    import random
    
    dna_service = CharacterDNAService()
    comfyui = ComfyUIClient(base_url=settings.comfyui_base_url, timeout=settings.comfyui_timeout)
    
    prompt = dna_service.generate_image_prompt(dna, "2d_chinese_donghua", view="sheet")
    print(f"\n=== PROMPT ===\n{prompt}\n")
    
    import json
    with open(WORKFLOW_DIR / "character_sheet.json") as f:
        workflow = json.load(f)
    
    neg = "lowres, bad anatomy, bad hands, text, error, missing finger, extra digits, fewer digits, cropped, worst quality, low quality, low score, bad score, average score, signature, watermark, username, blurry, mutation, deformed, distorted, disfigured, poorly drawn, bad proportions, extra limbs, missing limbs, floating limbs, disconnected limbs, malformed hands, malformed feet, poorly drawn hands, poorly drawn feet, bad perspective, bad composition, out of frame, nude, naked, NSFW, pornographic"
    
    overrides = {
        "6": {"inputs": {"text": prompt}},
        "7": {"inputs": {"text": neg}},
    }
    
    sheet_bytes = await comfyui.generate_with_workflow_dict(
        workflow=workflow,
        overrides=overrides,
        seed=random.randint(1, 999999999),
    )
    
    os.makedirs("test_outputs", exist_ok=True)
    
    # Save raw sheet
    raw_path = "test_outputs/raw_sheet.png"
    with open(raw_path, "wb") as f:
        f.write(sheet_bytes)
    
    img = Image.open(BytesIO(sheet_bytes))
    print(f"Raw sheet saved: {raw_path} | Size: {img.size}")
    
    # Now split and classify
    print("\nSplitting sheet...")
    crop_data = image_gen._split_character_sheet_smart(sheet_bytes)
    
    print(f"Characters found: {len(crop_data['characters'])}")
    print(f"Assets found: {len(crop_data['assets'])}")
    
    for i, b in enumerate(crop_data["characters"]):
        path = f"test_outputs/char_{i}.png"
        with open(path, "wb") as f:
            f.write(b)
        img = Image.open(BytesIO(b))
        print(f"  Saved character: {path} | Size: {img.size}")
    
    for i, b in enumerate(crop_data["assets"]):
        path = f"test_outputs/asset_{i}.png"
        with open(path, "wb") as f:
            f.write(b)
        img = Image.open(BytesIO(b))
        print(f"  Saved asset: {path} | Size: {img.size}")
    
    print("\nDone!")

if __name__ == "__main__":
    asyncio.run(main())
