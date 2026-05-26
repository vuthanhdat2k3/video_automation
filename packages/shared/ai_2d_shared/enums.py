from enum import Enum


class Style(str, Enum):
    TWO_D_CHINESE_DONGHUA = "2d_chinese_donghua"
    TWO_D_ANIME = "2d_anime"
    TWO_D_WESTERN = "2d_western"
    TWO_D_PIXAR = "2d_pixar"


class Status(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class AssetType(str, Enum):
    CHARACTER = "character"
    BACKGROUND = "background"
    PROP = "prop"
    KEYFRAME = "keyframe"
    AUDIO = "audio"
    VIDEO_CLIP = "video_clip"
    EXPORT = "export"


class JobType(str, Enum):
    GENERATE_CHARACTER = "generate_character"
    GENERATE_BACKGROUND = "generate_background"
    GENERATE_KEYFRAME = "generate_keyframe"
    GENERATE_AUDIO = "generate_audio"
    GENERATE_VIDEO = "generate_video"
    EXPORT = "export"


class ShotType(str, Enum):
    CINEMATIC_INTRO = "cinematic_intro"
    DIALOGUE = "dialogue"
    ACTION = "action"
    TRANSITION = "transition"
    ESTABLISHING = "establishing"
