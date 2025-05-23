"""キャッシュシステム."""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import RLock
from typing import Any, Generic, Hashable, Optional, TypeVar

K = TypeVar('K', bound=Hashable)
V = TypeVar('V')


class CacheEntry(Generic[V]):
    """キャッシュエントリ."""
    
    def __init__(self, value: V, ttl: Optional[float] = None):
        """初期化."""
        self.value = value
        self.created_at = time.time()
        self.last_accessed = self.created_at
        self.access_count = 1
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """有効期限切れかどうか確認."""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl
    
    def touch(self) -> None:
        """アクセス時刻と回数を更新."""
        self.last_accessed = time.time()
        self.access_count += 1


class LRUCache(Generic[K, V]):
    """スレッドセーフなLRUキャッシュ."""
    
    def __init__(self, max_size: int = 1000, default_ttl: Optional[float] = None):
        """初期化."""
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[K, CacheEntry[V]] = OrderedDict()
        self._lock = RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """値を取得."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default
            
            entry = self._cache[key]
            
            # 有効期限チェック
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return default
            
            # LRUリストの先頭に移動
            self._cache.move_to_end(key)
            entry.touch()
            self._hits += 1
            
            return entry.value
    
    def put(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """値を設定."""
        with self._lock:
            # TTLの決定
            effective_ttl = ttl if ttl is not None else self.default_ttl
            
            # 既存のキーの場合は更新
            if key in self._cache:
                self._cache[key] = CacheEntry(value, effective_ttl)
                self._cache.move_to_end(key)
                return
            
            # 新しいキーの場合
            entry = CacheEntry(value, effective_ttl)
            self._cache[key] = entry
            self._cache.move_to_end(key)
            
            # サイズ制限チェック
            if len(self._cache) > self.max_size:
                # 最も古いエントリを削除
                self._cache.popitem(last=False)
    
    def delete(self, key: K) -> bool:
        """キーを削除."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """キャッシュをクリア."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def size(self) -> int:
        """現在のキャッシュサイズ."""
        with self._lock:
            return len(self._cache)
    
    def is_empty(self) -> bool:
        """キャッシュが空かどうか."""
        with self._lock:
            return len(self._cache) == 0
    
    def keys(self) -> list[K]:
        """キーのリストを取得."""
        with self._lock:
            # 有効期限切れのエントリを除外
            valid_keys = []
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    valid_keys.append(key)
            
            # 有効期限切れのキーを削除
            for key in expired_keys:
                del self._cache[key]
            
            return valid_keys
    
    def values(self) -> list[V]:
        """値のリストを取得."""
        with self._lock:
            # 有効期限切れのエントリを除外
            valid_values = []
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    valid_values.append(entry.value)
            
            # 有効期限切れのキーを削除
            for key in expired_keys:
                del self._cache[key]
            
            return valid_values
    
    def items(self) -> list[tuple[K, V]]:
        """キー・値のペアのリストを取得."""
        with self._lock:
            # 有効期限切れのエントリを除外
            valid_items = []
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
                else:
                    valid_items.append((key, entry.value))
            
            # 有効期限切れのキーを削除
            for key in expired_keys:
                del self._cache[key]
            
            return valid_items
    
    def cleanup_expired(self) -> int:
        """有効期限切れのエントリを削除し、削除した数を返す."""
        with self._lock:
            expired_keys = []
            
            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._cache[key]
            
            return len(expired_keys)
    
    def get_stats(self) -> dict[str, Any]:
        """キャッシュ統計を取得."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "current_size": len(self._cache),
                "max_size": self.max_size,
                "utilization": len(self._cache) / self.max_size
            }
    
    def reset_stats(self) -> None:
        """統計をリセット."""
        with self._lock:
            self._hits = 0
            self._misses = 0
    
    def __contains__(self, key: K) -> bool:
        """キーが存在するかチェック."""
        with self._lock:
            if key not in self._cache:
                return False
            
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False
            
            return True
    
    def __len__(self) -> int:
        """キャッシュサイズを取得."""
        return self.size()
    
    def __getitem__(self, key: K) -> V:
        """辞書形式でのアクセス."""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: K, value: V) -> None:
        """辞書形式での設定."""
        self.put(key, value)
    
    def __delitem__(self, key: K) -> None:
        """辞書形式での削除."""
        if not self.delete(key):
            raise KeyError(key)


def cache_decorator(
    max_size: int = 128,
    ttl: Optional[float] = None,
    key_func: Optional[callable] = None
):
    """関数結果をキャッシュするデコレータ."""
    def decorator(func):
        cache = LRUCache[str, Any](max_size=max_size, default_ttl=ttl)
        
        def make_key(*args, **kwargs) -> str:
            """キャッシュキーを生成."""
            if key_func:
                return key_func(*args, **kwargs)
            
            # デフォルトのキー生成
            key_parts = [func.__name__]
            
            # 引数を文字列化
            for arg in args:
                key_parts.append(str(arg))
            
            # キーワード引数を文字列化（ソート済み）
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            return "|".join(key_parts)
        
        def wrapper(*args, **kwargs):
            cache_key = make_key(*args, **kwargs)
            
            # キャッシュから取得を試行
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # キャッシュにない場合は計算
            result = func(*args, **kwargs)
            cache.put(cache_key, result)
            
            return result
        
        # キャッシュ操作関数を追加
        wrapper.cache = cache
        wrapper.cache_info = cache.get_stats
        wrapper.cache_clear = cache.clear
        
        return wrapper
    
    return decorator


async def async_cache_decorator(
    max_size: int = 128,
    ttl: Optional[float] = None,
    key_func: Optional[callable] = None
):
    """非同期関数結果をキャッシュするデコレータ."""
    def decorator(func):
        cache = LRUCache[str, Any](max_size=max_size, default_ttl=ttl)
        
        def make_key(*args, **kwargs) -> str:
            """キャッシュキーを生成."""
            if key_func:
                return key_func(*args, **kwargs)
            
            # デフォルトのキー生成
            key_parts = [func.__name__]
            
            # 引数を文字列化
            for arg in args:
                key_parts.append(str(arg))
            
            # キーワード引数を文字列化（ソート済み）
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")
            
            return "|".join(key_parts)
        
        async def wrapper(*args, **kwargs):
            cache_key = make_key(*args, **kwargs)
            
            # キャッシュから取得を試行
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # キャッシュにない場合は計算
            result = await func(*args, **kwargs)
            cache.put(cache_key, result)
            
            return result
        
        # キャッシュ操作関数を追加
        wrapper.cache = cache
        wrapper.cache_info = cache.get_stats
        wrapper.cache_clear = cache.clear
        
        return wrapper
    
    return decorator 