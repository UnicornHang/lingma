"""Schema 包"""
from app.schemas.chapter import (
    ChapterBase,
    ChapterCreate,
    ChapterListResponse,
    ChapterRead,
    ChapterUpdate,
    GenerateChapterRequest,
    GenerationStreamEvent,
)
from app.schemas.common import ErrorResponse, HealthResponse
from app.schemas.setting import (
    ApiConfigCreate,
    ApiConfigRead,
    ApiConfigUpdate,
    ApiKeyReveal,
    SettingsBundle,
    SettingsUpdate,
)
from app.schemas.work import (
    WorkBase,
    WorkCreate,
    WorkListResponse,
    WorkRead,
    WorkUpdate,
    WorkWizardSeed,
)

__all__ = [
    # common
    "ErrorResponse",
    "HealthResponse",
    # work
    "WorkBase",
    "WorkCreate",
    "WorkUpdate",
    "WorkRead",
    "WorkListResponse",
    "WorkWizardSeed",
    # chapter
    "ChapterBase",
    "ChapterCreate",
    "ChapterUpdate",
    "ChapterRead",
    "ChapterListResponse",
    "GenerateChapterRequest",
    "GenerationStreamEvent",
    # setting
    "SettingsBundle",
    "SettingsUpdate",
    "ApiConfigCreate",
    "ApiConfigUpdate",
    "ApiConfigRead",
    "ApiKeyReveal",
]