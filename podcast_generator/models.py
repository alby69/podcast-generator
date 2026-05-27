from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Newsletter(BaseModel):
    title: str
    url: str
    date: datetime
    content: str


class ArticleSummary(BaseModel):
    href: str
    text: str
    description: str = ""
    date: str = ""
    duration: str = ""


class Episode(BaseModel):
    audio_path: Path
    script_path: Path
    script: str
    date_str: str
    title: str
    url: str
    duration_minutes: Optional[float] = None


class EpisodeRecord(BaseModel):
    id: int
    title: str
    url: str
    date: str
    audio_path: str
    script_path: str
    created_at: str


class GenerationJob(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    download_url: Optional[str] = None
    title: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
