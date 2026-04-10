"""
Checkpoint manager for resume-from-failure support.

At billion-record scale, crashes are not if but when. This tracks
processed record IDs so the pipeline can resume where it left off.
"""

from __future__ import annotations

import os
from pathlib import Path


class CheckpointManager:
    """Tracks processed IDs for each pipeline phase."""

    def __init__(self, checkpoint_dir: str = "checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._loaded: dict[str, set[str]] = {}

    def _phase_path(self, phase: str) -> Path:
        return self.checkpoint_dir / f"phase_{phase}_completed_ids.txt"

    def load_completed(self, phase: str) -> set[str]:
        """Load the set of completed IDs for a phase."""
        if phase in self._loaded:
            return self._loaded[phase]

        path = self._phase_path(phase)
        completed: set[str] = set()
        if path.exists():
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        completed.add(line)
        self._loaded[phase] = completed
        return completed

    def mark_completed(self, phase: str, record_id: str) -> None:
        """Append a completed record ID to the checkpoint file."""
        path = self._phase_path(phase)
        with open(path, "a") as f:
            f.write(record_id + "\n")
        if phase in self._loaded:
            self._loaded[phase].add(record_id)

    def mark_batch_completed(self, phase: str, record_ids: list[str]) -> None:
        """Append multiple completed record IDs."""
        path = self._phase_path(phase)
        with open(path, "a") as f:
            for rid in record_ids:
                f.write(rid + "\n")
        if phase in self._loaded:
            self._loaded[phase].update(record_ids)

    def count_completed(self, phase: str) -> int:
        """Return count of completed records for a phase."""
        return len(self.load_completed(phase))

    def is_completed(self, phase: str, record_id: str) -> bool:
        """Check if a specific record has been processed."""
        completed = self.load_completed(phase)
        return record_id in completed

    def reset_phase(self, phase: str) -> None:
        """Clear checkpoint for a phase (for re-processing)."""
        path = self._phase_path(phase)
        if path.exists():
            os.remove(path)
        self._loaded.pop(phase, None)
