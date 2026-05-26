import re
from typing import Any

from ai_2d_shared.character import CharacterDNA


class CharacterDNAService:
    """Bridge between LLM story character_json (free-form) and structured CharacterDNA."""

    # Style-specific prompt suffixes for image generation
    STYLE_PROMPTS = {
        "2d_chinese_donghua": "2D Chinese donghua animation style, cel-shaded, detailed line art, vibrant colors",
        "2d_anime": "anime style, Japanese animation, cel-shaded, clean line art, expressive eyes",
        "2d_western": "western 2D animation style, bold outlines, exaggerated features",
        "3d_pixar": "3D Pixar-style render, smooth surfaces, subsurface scattering",
        "3d_realistic": "photorealistic 3D render, PBR materials, ray-traced lighting",
    }

    KNOWN_HAIR_COLORS = {"black", "brown", "blonde", "red", "blue", "green", "purple", "white", "silver", "gold", "pink", "orange"}
    KNOWN_EYE_COLORS = {"black", "brown", "blue", "green", "red", "gold", "silver", "purple", "amber", "hazel", "gray"}
    KNOWN_SKIN_TONES = {"pale", "fair", "light", "tan", "olive", "brown", "dark", "ebony"}

    def extract_dna(self, character_data: dict) -> CharacterDNA:
        """Extract structured CharacterDNA from LLM story character JSON."""
        appearance = character_data.get("appearance", "") or ""
        visual_cues = character_data.get("visual_cues", []) or []
        personality = character_data.get("personality", "") or ""
        all_text = f"{appearance} {' '.join(visual_cues)} {personality}".lower()

        return CharacterDNA(
            age=character_data.get("age") or self._infer_age(character_data),
            gender=character_data.get("gender") or self._infer_gender(character_data),
            hair_style=self._find_hair_style(all_text, visual_cues),
            hair_color=self._find_hair_color(all_text, visual_cues),
            eye_shape=self._find_eye_shape(all_text, visual_cues),
            eye_color=self._find_eye_color(all_text, visual_cues),
            face_shape=self._find_face_shape(all_text, visual_cues),
            skin_tone=self._find_skin_tone(all_text, visual_cues),
            height=self._find_height(all_text),
            build=self._find_build(all_text),
            clothing_style=self._find_clothing(appearance, visual_cues),
            distinctive_features=self._find_distinctive(cues=visual_cues, text=all_text),
            personality_traits=self._find_traits(personality, visual_cues),
        )

    def generate_image_prompt(self, dna: CharacterDNA, style: str) -> str:
        """Build a ComfyUI-ready T2I prompt from CharacterDNA."""
        parts = []

        # Basic description
        desc_parts = []
        if dna.age and dna.gender:
            desc_parts.append(f"{dna.gender}, {dna.age} years old")
        if dna.hair_color and dna.hair_style:
            desc_parts.append(f"{dna.hair_color} {dna.hair_style}")
        elif dna.hair_color:
            desc_parts.append(f"{dna.hair_color} hair")
        if dna.eye_color and dna.eye_shape:
            desc_parts.append(f"{dna.eye_color} {dna.eye_shape}")
        elif dna.eye_color:
            desc_parts.append(f"{dna.eye_color} eyes")
        if dna.skin_tone:
            desc_parts.append(f"{dna.skin_tone} skin")
        if dna.build:
            desc_parts.append(f"{dna.build} build")
        if dna.height:
            desc_parts.append(f"{dna.height} height")
        if dna.clothing_style:
            desc_parts.append(f"wearing {dna.clothing_style}")
        if dna.distinctive_features:
            desc_parts.append(f"{' and '.join(dna.distinctive_features)}")

        parts.append("portrait of " + ", ".join(desc_parts))

        # Style
        style_prompt = self.STYLE_PROMPTS.get(style, self.STYLE_PROMPTS["2d_chinese_donghua"])
        parts.append(style_prompt)

        # Quality
        parts.append("high quality, detailed, sharp focus, clean background")

        return ", ".join(parts)

    # --- Private helpers ---

    def merge_dna_into_json(self, existing_json: dict, dna: CharacterDNA) -> dict:
        """Merge structured DNA fields back into character_json blob."""
        merged = dict(existing_json)
        dna_fields = dna.model_dump(exclude_unset=True)
        # Don't overwrite non-DNA fields
        merged.update(dna_fields)
        # Ensure appearance field reflects DNA
        appearance_parts = []
        if dna.age and dna.gender:
            appearance_parts.append(f"{dna.age}-year-old {dna.gender}")
        if dna.hair_color and dna.hair_style:
            appearance_parts.append(f"{dna.hair_color} {dna.hair_style}")
        elif dna.hair_color:
            appearance_parts.append(f"{dna.hair_color} hair")
        if dna.eye_color and dna.eye_shape:
            appearance_parts.append(f"{dna.eye_color} {dna.eye_shape}")
        elif dna.eye_color:
            appearance_parts.append(f"{dna.eye_color} eyes")
        if dna.clothing_style:
            appearance_parts.append(f"wearing {dna.clothing_style}")
        if dna.distinctive_features:
            appearance_parts.append("; ".join(dna.distinctive_features))
        if dna.personality_traits:
            merged["personality"] = ", ".join(dna.personality_traits)
        if appearance_parts:
            merged["appearance"] = ", ".join(appearance_parts)
        return merged

    def _infer_age(self, data: dict) -> int | None:
        role = (data.get("role") or "").lower()
        if any(k in role for k in ("child", "kid", "young")):
            return 12
        if any(k in role for k in ("teen", "student", "adolescent")):
            return 16
        if any(k in role for k in ("elder", "old", "ancient")):
            return 65
        return 25  # default adult

    def _infer_gender(self, data: dict) -> str | None:
        appearance = (data.get("appearance") or "").lower()
        name = (data.get("name") or "").lower()
        role = (data.get("role") or "").lower()
        # Vietnamese name heuristics
        if any(k in name for k in ("vũ", "minh", "huy", "đức", "cường", "nam", "hùng")):
            return "male"
        if any(k in name for k in ("lan", "hương", "mai", "trang", "thảo", "ly", "anh")):
            return "female"
        if any(k in appearance for k in ("woman", "female", "cô gái", "nữ", "kiều nữ")):
            return "female"
        if any(k in appearance for k in ("man", "male", "chàng trai", "nam", "thanh niên")):
            return "male"
        return None

    def _find_hair_style(self, text: str, cues: list[str]) -> str | None:
        for cue in cues:
            hl = cue.lower()
            if "hair" in hl:
                for style in ("long", "short", "medium", "ponytail", "bob", "braid", "curly", "straight", "spiky", "bald", "bun", "twintail"):
                    if style in hl:
                        return f"{style} hair"
        patterns = [
            r"(long|short|medium|curly|straight|spiky|bald)\s+hair",
            r"ponytail|bob\s*cut|braid|bun|twintail",
        ]
        for p in patterns:
            m = re.search(p, text)
            if m:
                return m.group(0)
        return "medium length" if "hair" in text else None

    def _find_hair_color(self, text: str, cues: list[str]) -> str | None:
        for cue in cues:
            for c in self.KNOWN_HAIR_COLORS:
                if c in cue.lower():
                    return c
        for c in self.KNOWN_HAIR_COLORS:
            if c in text and ("hair" in text or "haired" in text):
                return c
        words = text.split()
        for i, w in enumerate(words):
            if w == "hair" and i > 0:
                candidate = words[i - 1].strip(",-")
                if candidate in self.KNOWN_HAIR_COLORS:
                    return candidate
        return "black"  # default

    def _find_eye_shape(self, text: str, cues: list[str]) -> str | None:
        for cue in cues:
            hl = cue.lower()
            if "eye" in hl:
                for shape in ("round", "almond", "narrow", "big", "large", "slanted", "sharp", "gentle"):
                    if shape in hl:
                        return f"{shape} eyes"
        for shape in ("almond", "round", "narrow", "sharp", "big", "large"):
            if shape in text and "eye" in text:
                return f"{shape} eyes"
        return None

    def _find_eye_color(self, text: str, cues: list[str]) -> str | None:
        for cue in cues:
            for c in self.KNOWN_EYE_COLORS:
                if c in cue.lower() and "eye" in cue.lower():
                    return c
        for c in self.KNOWN_EYE_COLORS:
            if c in text and "eye" in text:
                return c
        return "black"

    def _find_face_shape(self, text: str, cues: list[str]) -> str | None:
        for shape in ("oval", "round", "square", "heart", "diamond", "long"):
            pattern = shape + r"\s*face"
            if re.search(pattern, text):
                return f"{shape} face"
        for cue in cues:
            for shape in ("oval", "round", "square", "heart", "diamond"):
                if shape in cue.lower() and "face" in cue.lower():
                    return f"{shape} face"
        return None

    def _find_skin_tone(self, text: str, cues: list[str]) -> str | None:
        for cue in cues:
            for t in self.KNOWN_SKIN_TONES:
                if t in cue.lower():
                    return t
        for t in self.KNOWN_SKIN_TONES:
            if t in text and ("skin" in text or "skinned" in text or "complexion" in text):
                return t
        return None

    def _find_height(self, text: str) -> str | None:
        for h in ("tall", "short", "average height", "petite"):
            if h in text:
                return h
        return None

    def _find_build(self, text: str) -> str | None:
        for b in ("slim", "slender", "muscular", "athletic", "stocky", "plump", "thin", "lean", "average"):
            if b in text:
                return b
        return None

    def _find_clothing(self, appearance: str, cues: list[str]) -> str | None:
        cloth_cues = cues + [appearance]
        patterns = [
            r"wearing\s+([^,.]+)",
            r"dressed\s+in\s+([^,.]+)",
            r"clad\s+in\s+([^,.]+)",
            r"in\s+a\s+([^,.]+(?:robe|gown|suit|armor|dress|uniform|coat|jacket|shirt|pants|outfit))",
        ]
        for text in cloth_cues:
            for p in patterns:
                m = re.search(p, text)
                if m:
                    return m.group(1).strip()
        return None

    def _find_distinctive(self, cues: list[str], text: str) -> list[str]:
        known_features = {"scar", "tattoo", "glasses", "mask", "birthmark", "freckles", "beard", "mustache",
                          "eyepatch", "bandage", "piercing", "earring", "necklace", "crown", "headband", "ribbon"}
        found = set()
        for cue in cues:
            cl = cue.lower()
            for f in known_features:
                if f in cl:
                    found.add(cue)
        return list(found)

    def _find_traits(self, personality: str, cues: list[str]) -> list[str]:
        all_text = f"{personality} {' '.join(cues)}"
        known_traits = {
            "brave", "calm", "cold", "composed", "confident", "cruel", "curious",
            "determined", "elegant", "fierce", "gentle", "happy", "honorable", "loyal",
            "mysterious", "noble", "observant", "patient", "playful", "proud",
            "quiet", "sarcastic", "serious", "shy", "stoic", "strong-willed", "wise",
        }
        found = []
        for t in known_traits:
            if t in all_text:
                found.append(t)
        return found
