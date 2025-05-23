"""キャッシュシステムのテスト."""

import time
import threading
from unittest.mock import patch

import pytest

from src.utils.cache import CacheEntry, LRUCache, cache_decorator


class TestCacheEntry:
    """CacheEntryのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        entry = CacheEntry("test_value")
        
        assert entry.value == "test_value"
        assert entry.ttl is None
        assert entry.access_count == 1
        assert isinstance(entry.created_at, float)
        assert entry.last_accessed == entry.created_at
    
    def test_initialization_with_ttl(self):
        """TTL付き初期化のテスト."""
        entry = CacheEntry("test_value", ttl=60.0)
        
        assert entry.value == "test_value"
        assert entry.ttl == 60.0
        assert entry.access_count == 1
    
    def test_is_expired_no_ttl(self):
        """TTLなしの場合の有効期限チェック."""
        entry = CacheEntry("test_value")
        assert not entry.is_expired()
    
    def test_is_expired_with_ttl(self):
        """TTL付きの有効期限チェック."""
        # 有効期限内
        entry = CacheEntry("test_value", ttl=60.0)
        assert not entry.is_expired()
        
        # 有効期限切れ
        with patch('time.time', return_value=time.time() + 61):
            assert entry.is_expired()
    
    def test_touch(self):
        """アクセス更新のテスト."""
        entry = CacheEntry("test_value")
        original_access_count = entry.access_count
        original_last_accessed = entry.last_accessed
        
        time.sleep(0.01)
        entry.touch()
        
        assert entry.access_count == original_access_count + 1
        assert entry.last_accessed > original_last_accessed


class TestLRUCache:
    """LRUCacheのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        cache = LRUCache[str, str](max_size=100)
        
        assert cache.max_size == 100
        assert cache.default_ttl is None
        assert cache.size() == 0
        assert cache.is_empty()
        assert cache.get_stats()["hits"] == 0
        assert cache.get_stats()["misses"] == 0
    
    def test_initialization_invalid_size(self):
        """不正なサイズでの初期化テスト."""
        with pytest.raises(ValueError, match="max_size must be positive"):
            LRUCache[str, str](max_size=0)
        
        with pytest.raises(ValueError, match="max_size must be positive"):
            LRUCache[str, str](max_size=-1)
    
    def test_put_and_get(self):
        """基本的な put/get のテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        assert cache.size() == 1
        assert not cache.is_empty()
    
    def test_get_default(self):
        """存在しないキーの取得テスト."""
        cache = LRUCache[str, str](max_size=10)
        
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"
    
    def test_update_existing_key(self):
        """既存キーの更新テスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key1", "value2")
        
        assert cache.get("key1") == "value2"
        assert cache.size() == 1
    
    def test_lru_eviction(self):
        """LRU による立ち退きテスト."""
        cache = LRUCache[str, str](max_size=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        cache.put("key4", "value4")  # key1 が立ち退き
        
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        assert cache.size() == 3
    
    def test_lru_access_order(self):
        """LRU アクセス順序のテスト."""
        cache = LRUCache[str, str](max_size=3)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        
        # key1 にアクセスして最新にする
        cache.get("key1")
        
        # 新しいキーを追加（key2 が立ち退き）
        cache.put("key4", "value4")
        
        assert cache.get("key1") == "value1"  # 残っている
        assert cache.get("key2") is None      # 立ち退き
        assert cache.get("key3") == "value3"  # 残っている
        assert cache.get("key4") == "value4"  # 新規
    
    def test_delete(self):
        """削除のテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.size() == 0
        
        # 存在しないキーの削除
        assert cache.delete("nonexistent") is False
    
    def test_clear(self):
        """クリアのテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.get("key1")  # ヒット数を増やす
        
        cache.clear()
        
        assert cache.size() == 0
        assert cache.is_empty()
        assert cache.get_stats()["hits"] == 0
        assert cache.get_stats()["misses"] == 0
    
    def test_ttl_expiration(self):
        """TTL による有効期限のテスト."""
        cache = LRUCache[str, str](max_size=10, default_ttl=0.1)
        
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # 有効期限が切れるまで待機
        time.sleep(0.15)
        
        assert cache.get("key1") is None
        assert cache.size() == 0
    
    def test_custom_ttl(self):
        """カスタムTTLのテスト."""
        cache = LRUCache[str, str](max_size=10, default_ttl=60.0)
        
        cache.put("key1", "value1", ttl=0.1)  # カスタムTTL
        cache.put("key2", "value2")           # デフォルトTTL
        
        time.sleep(0.15)
        
        assert cache.get("key1") is None      # 期限切れ
        assert cache.get("key2") == "value2"  # まだ有効
    
    def test_keys_values_items(self):
        """keys/values/items のテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3", ttl=0.1)
        
        time.sleep(0.15)  # key3 を期限切れにする
        
        keys = cache.keys()
        values = cache.values()
        items = cache.items()
        
        assert "key1" in keys
        assert "key2" in keys
        assert "key3" not in keys  # 期限切れで削除済み
        
        assert "value1" in values
        assert "value2" in values
        assert "value3" not in values
        
        assert ("key1", "value1") in items
        assert ("key2", "value2") in items
        assert ("key3", "value3") not in items
    
    def test_cleanup_expired(self):
        """期限切れエントリのクリーンアップテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1", ttl=0.1)
        cache.put("key2", "value2", ttl=0.1)
        cache.put("key3", "value3")  # TTLなし
        
        time.sleep(0.15)
        
        expired_count = cache.cleanup_expired()
        
        assert expired_count == 2
        assert cache.size() == 1
        assert cache.get("key3") == "value3"
    
    def test_statistics(self):
        """統計情報のテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        cache.get("key1")      # ヒット
        cache.get("key2")      # ミス
        cache.get("key1")      # ヒット
        
        stats = cache.get_stats()
        
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate"] == 2/3
        assert stats["current_size"] == 1
        assert stats["max_size"] == 10
        assert stats["utilization"] == 0.1
    
    def test_reset_stats(self):
        """統計リセットのテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache.put("key1", "value1")
        cache.get("key1")
        cache.get("key2")
        
        cache.reset_stats()
        
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
    
    def test_dict_interface(self):
        """辞書インターフェースのテスト."""
        cache = LRUCache[str, str](max_size=10)
        
        cache["key1"] = "value1"
        assert cache["key1"] == "value1"
        assert "key1" in cache
        assert len(cache) == 1
        
        del cache["key1"]
        assert "key1" not in cache
        assert len(cache) == 0
        
        with pytest.raises(KeyError):
            _ = cache["nonexistent"]
        
        with pytest.raises(KeyError):
            del cache["nonexistent"]
    
    def test_thread_safety(self):
        """スレッドセーフティのテスト."""
        cache = LRUCache[str, int](max_size=100)
        
        def worker(worker_id: int):
            for i in range(100):
                key = f"key_{worker_id}_{i}"
                cache.put(key, i)
                value = cache.get(key)
                assert value == i
        
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # すべてのスレッドが正常に完了したことを確認
        assert cache.size() <= 100  # サイズ制限内


class TestCacheDecorator:
    """cache_decoratorのテスト."""
    
    def test_basic_caching(self):
        """基本的なキャッシュ機能のテスト."""
        call_count = 0
        
        @cache_decorator(max_size=10)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # 初回呼び出し
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # キャッシュからの取得
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 関数は再実行されない
        
        # 異なる引数での呼び出し
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_cache_with_kwargs(self):
        """キーワード引数を含むキャッシュのテスト."""
        call_count = 0
        
        @cache_decorator(max_size=10)
        def function_with_kwargs(x: int, y: int = 1) -> int:
            nonlocal call_count
            call_count += 1
            return x + y
        
        result1 = function_with_kwargs(5, y=2)
        result2 = function_with_kwargs(5, y=2)
        result3 = function_with_kwargs(5, y=3)
        
        assert result1 == 7
        assert result2 == 7
        assert result3 == 8
        assert call_count == 2  # 異なる引数なので2回実行
    
    def test_cache_ttl(self):
        """TTL付きキャッシュのテスト."""
        call_count = 0
        
        @cache_decorator(max_size=10, ttl=0.1)
        def function_with_ttl(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3
        
        result1 = function_with_ttl(5)
        assert result1 == 15
        assert call_count == 1
        
        # キャッシュからの取得
        result2 = function_with_ttl(5)
        assert result2 == 15
        assert call_count == 1
        
        # TTL期限切れ後
        time.sleep(0.15)
        result3 = function_with_ttl(5)
        assert result3 == 15
        assert call_count == 2  # 再実行される
    
    def test_cache_operations(self):
        """キャッシュ操作のテスト."""
        @cache_decorator(max_size=10)
        def test_function(x: int) -> int:
            return x * 4
        
        # キャッシュに値を設定
        test_function(5)
        
        # キャッシュ統計の確認
        stats = test_function.cache_info()
        assert stats["total_requests"] > 0
        
        # キャッシュクリア
        test_function.cache_clear()
        stats_after_clear = test_function.cache_info()
        assert stats_after_clear["current_size"] == 0 