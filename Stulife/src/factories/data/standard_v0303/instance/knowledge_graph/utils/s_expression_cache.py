from typing import Sequence
import json
from pydantic import BaseModel
import datetime
from typing import Optional
from src.utils import SafeLogger


class CacheInfo(BaseModel):
    created_time: str
    visited_count: int
    last_visited_time: str


class SExpressionCacheEntry(BaseModel):
    value: Sequence[str]
    info: CacheInfo


class SExpressionCache:
    def __init__(self, cache_path: str):
        self.cache_path = cache_path
        self.cache_dict = {
            key: SExpressionCacheEntry.model_validate(entry_dict)
            for key, entry_dict in json.load(open(self.cache_path)).items()
        }
        self.update_count = 0

    def get_cache_item(self, key: str) -> Optional[Sequence[str]]:
        if key not in self.cache_dict:
            return None
        cache_entry = self.cache_dict[key]
        cache_entry.info.visited_count += 1
        cache_entry.info.last_visited_time = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return self.cache_dict[key].value

    def set_cache_item(self, key: str, value: Sequence[str]) -> None:
        value = sorted(value)
        if key in self.cache_dict:
            if self.cache_dict[key].value != value:
                SafeLogger.warning(
                    f"Cache entry for {key} already exists with different value. Overwriting."
                )
            else:
                return
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cache_dict[key] = SExpressionCacheEntry(
            value=value,
            info=CacheInfo(
                created_time=current_time,
                visited_count=1,
                last_visited_time=current_time,
            ),
        )
        self.update_count += 1
        if self.update_count == 100:
            self.update_count = 0
            self.write_back()

    def write_back(self) -> None:
        json.dump(
            {key: entry.model_dump() for key, entry in self.cache_dict.items()},
            open(self.cache_path, "w"),
            indent=2,
        )
