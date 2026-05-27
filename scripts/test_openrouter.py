import asyncio
from app.services.story import create_translation_llm_provider
from ai_2d_shared.character import CharacterDNA

async def main():
    print("Testing OpenRouter translation & DNA extraction...")
    provider = create_translation_llm_provider()
    
    # Test description
    description = "Một nam tử 24 tuổi tóc đỏ rực buộc đuôi ngựa cao, mặc hắc bào thêu rồng đỏ, mắt lạnh lùng."
    system_prompt = "You are a precise character metadata extraction assistant. Output ONLY valid JSON."
    
    from app.services.prompts.compiler import PromptCompiler
    compiler = PromptCompiler()
    prompt = compiler.compile("CHARACTER_DNA_EXTRACT_PROMPT", description=description)
    
    print("\n[+] Sending request to OpenRouter...")
    try:
        res = await provider.generate(system_prompt, prompt, CharacterDNA)
        print("\n[✔] OpenRouter Response parsed successfully:")
        import json
        print(json.dumps(res, indent=4, ensure_ascii=False))
    except Exception as e:
        print(f"\n[-] OpenRouter request failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
