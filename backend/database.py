"""
Persistence helpers for face encodings and metadata.
"""

from __future__ import annotations

import pickle
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Tuple

import face_recognition
import numpy as np


class FaceDatabase:
    """Simple filesystem-backed face database."""

    def __init__(
        self,
        data_dir: Path,
        faces_dir: Path,
        tolerance: float = 0.45,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.faces_dir = Path(faces_dir)
        self.tolerance = tolerance
        self._db_file = self.data_dir / "faces.pkl"
        self._lock = RLock()

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.faces_dir.mkdir(parents=True, exist_ok=True)

        self._encodings: List[np.ndarray] = []
        self._metadata: List[Dict[str, str]] = []
        self._load()

        # Debug database status
        print(f"[DEBUG] Loaded face database:")
        print(f"[DEBUG] - Number of faces: {len(self._encodings)}")
        print(f"[DEBUG] - Tolerance: {self.tolerance}")

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _load(self) -> None:
        if not self._db_file.exists():
            print(f"[DEBUG] Database file does not exist: {self._db_file}")
            return

        try:
            with self._db_file.open("rb") as handle:
                payload = pickle.load(handle)

            encodings = payload.get("encodings", [])
            metadata = payload.get("metadata", [])

            self._encodings = [np.array(enc, dtype=np.float32) for enc in encodings]
            self._metadata = metadata

            print(f"[DEBUG] Loaded from disk: {len(self._encodings)} encodings, {len(self._metadata)} metadata entries")
        except Exception as e:
            print(f"[ERROR] Failed to load database: {e}")
            import traceback
            traceback.print_exc()

    def _save(self) -> None:
        serializable_encodings = [enc.tolist() for enc in self._encodings]
        payload = {"encodings": serializable_encodings, "metadata": self._metadata}

        with self._db_file.open("wb") as handle:
            pickle.dump(payload, handle)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def add_face(self, name: str, encoding: np.ndarray, image_path: Path, person_id: str = None) -> Dict[str, str]:
        """Persist a new face encoding."""
        image_name = Path(image_path).name if image_path else None

        with self._lock:
            self._encodings.append(np.array(encoding, dtype=np.float32))
            entry = {
                "name": name,
                "person_id": person_id or "",  # Store person ID
                "image_path": image_name,
                "created_at": datetime.utcnow().isoformat(),
            }
            self._metadata.append(entry)
            self._save()
            return entry

    def clear(self) -> None:
        """Remove all saved faces."""
        with self._lock:
            self._encodings = []
            self._metadata = []
            if self._db_file.exists():
                self._db_file.unlink()

    def list_faces(self) -> List[Dict[str, str]]:
        """Return metadata for registered faces."""
        with self._lock:
            faces = []
            for entry in self._metadata:
                faces.append(
                    {
                        **entry,
                        "image_url": f"/faces/{entry['image_path']}"
                        if entry.get("image_path")
                        else None,
                    }
                )
            return faces

    def match(self, encoding: np.ndarray) -> Optional[Dict[str, object]]:
        """Return the best match for the provided encoding."""
        with self._lock:
            if not self._encodings:
                return None

            known_encodings = np.vstack(self._encodings)
            distances = face_recognition.face_distance(known_encodings, encoding)
            best_idx = int(np.argmin(distances))
            distance = float(distances[best_idx])
            
            # Add debug logging for matching
            print(f"[DEBUG] Face matching:")
            print(f"[DEBUG] - Best distance: {distance:.3f}")
            print(f"[DEBUG] - Tolerance threshold: {self.tolerance}")

            metadata = self._metadata[best_idx]
            if distance <= self.tolerance:
                match = {
                    "name": metadata["name"],
                    "person_id": metadata.get("person_id", ""),  # Include person_id
                    "distance": distance,
                    "meta": metadata,
                    "confidence": 1.0 - (distance / self.tolerance)
                }
                print(f"[DEBUG] - Match found: {metadata['name']} (ID: {metadata.get('person_id', 'N/A')}) (confidence: {match['confidence']:.3f})")
                return match

            print("[DEBUG] - No match found (unknown face)")
            return {"name": "Unknown", "person_id": "", "distance": distance, "meta": None}

    @property
    def count(self) -> int:
        return len(self._encodings)
