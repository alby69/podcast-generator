from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class Newsletter:
    title: str
    url: str
    date: datetime
    content: str


@dataclass
class Episode:
    audio_path: Path
    script_path: Path
    script: str
    date_str: str
    title: str
    url: str
    duration_minutes: float | None = None
