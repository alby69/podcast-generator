from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from podcast_generator.exceptions import TrackerError

PROCESSED_FILE = ".processed.json"


class Tracker:
    def __init__(self, output_dir: Path):
        self.tracker_path = output_dir / PROCESSED_FILE
        self.data = self._load()

    def _load(self) -> dict:
        try:
            if self.tracker_path.exists():
                return json.loads(self.tracker_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            raise TrackerError(f"Failed to load tracker file: {e}") from e
        return {"processed": []}

    def _save(self):
        try:
            self.tracker_path.parent.mkdir(parents=True, exist_ok=True)
            self.tracker_path.write_text(
                json.dumps(self.data, indent=2, ensure_ascii=False)
            )
        except OSError as e:
            raise TrackerError(f"Failed to save tracker file: {e}") from e

    def is_processed(self, url: str) -> bool:
        return any(item["url"] == url for item in self.data["processed"])

    def mark_processed(
        self,
        url: str,
        title: str,
        date: str,
        daily_file: str,
        script_file: str,
    ):
        self.data["processed"].append(
            {
                "url": url,
                "title": title,
                "date": date,
                "daily_file": daily_file,
                "script_file": script_file,
            }
        )
        self._save()

    def get_by_week(self) -> dict[str, list[dict]]:
        groups: dict[str, list[dict]] = {}
        for item in self.data["processed"]:
            try:
                year, week_num = self._get_iso_week(item["date"])
            except (ValueError, KeyError):
                continue
            key = f"{year}-W{week_num:02d}"
            groups.setdefault(key, []).append(item)
        return groups

    @staticmethod
    def _get_iso_week(date_str: str) -> tuple[int, int]:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        iso = dt.isocalendar()
        return (iso[0], iso[1])
