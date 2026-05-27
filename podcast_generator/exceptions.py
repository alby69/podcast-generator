class PodcastGeneratorError(Exception):
    """Base exception for all podcast generator errors."""


class ConfigError(PodcastGeneratorError):
    """Missing or invalid configuration."""


class FetchError(PodcastGeneratorError):
    """Error fetching newsletter content."""


class TranslationError(PodcastGeneratorError):
    """Error generating podcast script via LLM."""


class TTSError(PodcastGeneratorError):
    """Error generating audio via TTS."""


class AudioError(PodcastGeneratorError):
    """Error processing audio files."""


class TrackerError(PodcastGeneratorError):
    """Error reading/writing tracker state."""


class AuthError(PodcastGeneratorError):
    """Authentication/authorization error."""


class NotFoundError(PodcastGeneratorError):
    """Resource not found."""
