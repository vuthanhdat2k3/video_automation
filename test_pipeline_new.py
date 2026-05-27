import asyncio
import os
import sys
from pathlib import Path

# Add root path to import app services
sys.path.insert(0, "/home/dat/pipeline/video_automation/apps/api")

from app.services.image_gen import ImageGenService
from ai_2d_shared.character import CharacterDNA

async def main():
    print("🚀 Initializing ImageGenService for 4-Phase Full Pipeline Test...")
    image_gen = ImageGenService()
    
    # Define a character DNA
    dna = CharacterDNA(
        age=22,
        gender="female",
        hair_color="silver",
        hair_style="long hair flowing with twintails",
        eye_color="blue",
        clothing_style="futuristic cyberpunk bodysuit with neon blue accents",
        accessories=["cyber visor", "glowing neon necklace"],
        distinctive_features=["glowing cyber sword", "neon tattoo on neck"]
    )
    
    output_dir = Path("test_outputs_new")
    output_dir.mkdir(exist_ok=True)
    
    style = "2d_chinese_donghua"
    seed = 8888  # Seed for consistency
    
    results = {}

    # ==========================================
    # PHASE 1: Character turnaround views (SKIPPED FOR SPEED)
    # ==========================================
    print("\n=== [PHASE 1] Loading Master Front View from disk ===")
    front_path = output_dir / "01_master_front.png"
    if front_path.exists():
        front_bytes = front_path.read_bytes()
        print(f"✅ Loaded Master Front from {front_path}")
    else:
        print(f"❌ {front_path} not found! Run full pipeline first.")
        return

    # ==========================================
    # PHASE 2: Outfit Items
    # ==========================================
    print("\n=== [PHASE 2] Generating Outfit Items ===")
    outfit_items = {}
    
    # 2.1 Bodysuit
    print("2.1 Generating Bodysuit...")
    bodysuit_bytes = await image_gen.generate_item("upper_body", "futuristic cyberpunk bodysuit with neon accents", style, reference_image_bytes=front_bytes, seed=seed)
    output_dir.joinpath("outfit_bodysuit.png").write_bytes(bodysuit_bytes)
    outfit_items["bodysuit"] = bodysuit_bytes
    
    # 2.2 Cyber Visor
    print("2.2 Generating Cyber Visor...")
    visor_bytes = await image_gen.generate_item("accessory_0", "cyber visor, high-tech glowing eyewear", style, reference_image_bytes=front_bytes, seed=seed)
    output_dir.joinpath("outfit_visor.png").write_bytes(visor_bytes)
    outfit_items["visor"] = visor_bytes

    # 2.3 Stitch Outfit Sheet
    try:
        outfit_sheet = image_gen.stitch_character_sheet(outfit_items)
        outfit_sheet_path = output_dir / "phase2_outfit_sheet.png"
        outfit_sheet_path.write_bytes(outfit_sheet)
        print(f"✅ Stitched Outfit Sheet saved to {outfit_sheet_path}")
    except Exception as e:
        print(f"❌ Failed to stitch outfit sheet: {e}")

    # ==========================================
    # PHASE 3: Asset Items
    # ==========================================
    print("\n=== [PHASE 3] Generating Asset Items (Weapons/Props) ===")
    asset_items = {}
    
    # 3.1 Cyber Sword
    print("3.1 Generating Cyber Sword...")
    sword_bytes = await image_gen.generate_item("glowing_cyber_sword", "glowing futuristic cyber sword, energy blade", style, reference_image_bytes=front_bytes, seed=seed)
    output_dir.joinpath("asset_cyber_sword.png").write_bytes(sword_bytes)
    asset_items["cyber_sword"] = sword_bytes

    # 3.2 Stitch Asset Sheet
    try:
        asset_sheet = image_gen.stitch_character_sheet(asset_items)
        asset_sheet_path = output_dir / "phase3_asset_sheet.png"
        asset_sheet_path.write_bytes(asset_sheet)
        print(f"✅ Stitched Asset Sheet saved to {asset_sheet_path}")
    except Exception as e:
        print(f"❌ Failed to stitch asset sheet: {e}")

    # ==========================================
    # PHASE 4: Expression Views
    # ==========================================
    print("\n=== [PHASE 4] Generating Face Expression Views ===")
    expression_items = {}
    
    # 4.1 Smile Expression
    print("4.1 Generating Smile Expression...")
    smile_bytes = await image_gen.generate_expression(dna, style, "smile", front_bytes, denoise=0.38)
    try:
        smile_restored = await image_gen.apply_face_restore(smile_bytes)
        output_dir.joinpath("expr_smile_restored.png").write_bytes(smile_restored)
        expression_items["smile"] = smile_restored
        print("   Saved smile expression")
    except Exception as e:
        print(f"   Smile face restore failed: {e}")
        expression_items["smile"] = smile_bytes

    # 4.2 Angry Expression
    print("4.2 Generating Angry Expression...")
    angry_bytes = await image_gen.generate_expression(dna, style, "angry", front_bytes, denoise=0.38)
    try:
        angry_restored = await image_gen.apply_face_restore(angry_bytes)
        output_dir.joinpath("expr_angry_restored.png").write_bytes(angry_restored)
        expression_items["angry"] = angry_restored
        print("   Saved angry expression")
    except Exception as e:
        print(f"   Angry face restore failed: {e}")
        expression_items["angry"] = angry_bytes

    # 4.3 Stitch Expression Sheet
    try:
        expression_sheet = image_gen.stitch_character_sheet(expression_items)
        expr_sheet_path = output_dir / "phase4_expression_sheet.png"
        expr_sheet_path.write_bytes(expression_sheet)
        print(f"✅ Stitched Expression Sheet saved to {expr_sheet_path}")
    except Exception as e:
        print(f"❌ Failed to stitch expression sheet: {e}")

    print("\n🎉 Full 4-Phase pipeline test run completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
