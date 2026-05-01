import logging
import pickle
from pathlib import Path

from pybloom_live import ScalableBloomFilter

logger = logging.getLogger(__name__)


class BloomDedup:
    def __init__(self, path: str | Path, capacity: int = 10000, error_rate: float = 0.01):
        self.path = Path(path)
        self.filter = self._load(capacity, error_rate)

    def _load(self, capacity: int, error_rate: float) -> ScalableBloomFilter:
        if self.path.exists():
            try:
                with open(self.path, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning("Bloom filter file corrupted, creating new one: %s", e)
        return ScalableBloomFilter(initial_capacity=capacity, error_rate=error_rate)

    def is_seen(self, aweme_id: str) -> bool:
        return aweme_id in self.filter

    def mark_seen(self, aweme_id: str) -> None:
        self.filter.add(aweme_id)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "wb") as f:
            pickle.dump(self.filter, f)
        logger.info("Bloom filter saved to %s", self.path)

    @staticmethod
    def reset(path: str | Path) -> None:
        p = Path(path)
        if p.exists():
            p.unlink()
            logger.info("Bloom filter removed: %s", p)
