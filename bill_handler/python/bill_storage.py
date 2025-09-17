# workers/bill_storage.py
import threading
import json
import os
from typing import Dict

DEFAULT_DENOMS = [20, 50, 100, 200, 500, 1000]
DEFAULT_COUNTS = {d: 20 for d in DEFAULT_DENOMS}
DEFAULT_FILE = os.path.join(os.path.dirname(__file__), "bill_storage.json")


class BillStorage:
    """Thread-safe bill storage with JSON persistence."""

    def __init__(self, filepath: str = DEFAULT_FILE, initial_counts: Dict[int, int] = None):
        self.filepath = filepath
        self.lock = threading.Lock()
        if initial_counts is None:
            initial_counts = DEFAULT_COUNTS.copy()
        # normalize keys to ints
        self._storage = {int(k): int(v) for k, v in initial_counts.items()}
        # try to load persisted state if present
        try:
            self._load()
        except Exception:
            # if loading fails, persist defaults
            self._persist()

    def _load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r") as f:
                data = json.load(f)
            # convert keys to ints
            self._storage = {int(k): int(v) for k, v in data.items()}
            # ensure all default denoms exist
            for d in DEFAULT_DENOMS:
                self._storage.setdefault(d, 0)

    def _persist(self):
        tmp = self.filepath + ".tmp"
        with open(tmp, "w") as f:
            json.dump({str(k): v for k, v in self._storage.items()}, f, indent=2)
        os.replace(tmp, self.filepath)

    def get_storage(self) -> Dict[int, int]:
        with self.lock:
            return self._storage.copy()

    def add(self, denom: int, count: int = 1) -> None:
        if denom not in DEFAULT_DENOMS:
            raise ValueError("Unsupported denomination")
        with self.lock:
            self._storage.setdefault(denom, 0)
            self._storage[denom] += int(count)
            self._persist()

    def deduct(self, denom: int, count: int = 1) -> bool:
        """Atomically deduct; return True if success, False if insufficient."""
        if denom not in DEFAULT_DENOMS:
            raise ValueError("Unsupported denomination")
        with self.lock:
            current = self._storage.get(denom, 0)
            if current < count:
                return False
            self._storage[denom] = current - int(count)
            self._persist()
            return True

    def reserve_bulk(self, breakdown: Dict[int, int]) -> bool:
        """
        Attempt to deduct all denominations in breakdown atomically.
        Returns True on success (deducted), False on insufficient (no change).
        """
        with self.lock:
            # check availability
            for d, c in breakdown.items():
                if self._storage.get(d, 0) < c:
                    return False
            # deduct
            for d, c in breakdown.items():
                self._storage[d] = self._storage.get(d, 0) - c
            self._persist()
            return True

    def rollback_add(self, denom: int, count: int = 1) -> None:
        """Used to restore storage after a failed physical operation."""
        # reuse add (persistes)
        self.add(denom, count)
