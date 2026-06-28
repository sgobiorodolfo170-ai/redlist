class RedListError(Exception):
    """Base exception for all RedList application errors."""


class OCRError(RedListError):
    """Raised when OCR processing fails."""


class TranslationError(RedListError):
    """Raised when translation request fails."""


class LLMError(RedListError):
    """Raised when LLM request fails."""


class SettingsError(RedListError):
    """Raised when settings cannot be loaded or saved."""
