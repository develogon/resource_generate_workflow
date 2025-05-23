"""Redisクライアントのテスト"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.clients.redis import (
    RedisClient,
    RedisError,
    RedisConnectionError
)


@pytest.fixture
def redis_client():
    """Redisクライアントのフィクスチャ"""
    return RedisClient(url="redis://localhost:6379/0")


@pytest.fixture
def mock_redis():
    """モックRedisのフィクスチャ"""
    mock = AsyncMock()
    return mock


class TestRedisClient:
    """Redisクライアントのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, redis_client):
        """初期化のテスト"""
        assert redis_client.url == "redis://localhost:6379/0"
        assert redis_client.host == "localhost"
        assert redis_client.port == 6379
        assert redis_client.db == 0
        assert redis_client.password is None
        assert redis_client.encoding == "utf-8"
        assert redis_client.decode_responses is True
        
    @pytest.mark.asyncio
    async def test_initialization_with_auth(self):
        """認証付きURLでの初期化テスト"""
        client = RedisClient(url="redis://user:pass@example.com:6380/1")
        assert client.host == "example.com"
        assert client.port == 6380
        assert client.db == 1
        assert client.password == "pass"
        
    @pytest.mark.asyncio
    async def test_connect_success(self, redis_client, mock_redis):
        """接続成功のテスト"""
        with patch('src.clients.redis.redis.from_url', return_value=mock_redis) as mock_from_url:
            await redis_client.connect()
            
            assert redis_client.redis is mock_redis
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                encoding="utf-8",
                decode_responses=True
            )
            mock_redis.ping.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_connect_failure(self, redis_client):
        """接続失敗のテスト"""
        with patch('src.clients.redis.redis.from_url', side_effect=Exception("Connection failed")):
            with pytest.raises(RedisConnectionError):
                await redis_client.connect()
                
    @pytest.mark.asyncio
    async def test_disconnect(self, redis_client, mock_redis):
        """切断のテスト"""
        redis_client.redis = mock_redis
        
        await redis_client.disconnect()
        
        mock_redis.aclose.assert_called_once()
        assert redis_client.redis is None
        
    @pytest.mark.asyncio
    async def test_context_manager(self, redis_client, mock_redis):
        """コンテキストマネージャーのテスト"""
        with patch('src.clients.redis.redis.from_url', return_value=mock_redis):
            async with redis_client as client:
                assert client is redis_client
                assert redis_client.redis is mock_redis
                
            mock_redis.aclose.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_ensure_connected_success(self, redis_client, mock_redis):
        """接続確認成功のテスト"""
        redis_client.redis = mock_redis
        redis_client._ensure_connected()  # 例外が発生しないことを確認
        
    @pytest.mark.asyncio
    async def test_ensure_connected_failure(self, redis_client):
        """接続確認失敗のテスト"""
        with pytest.raises(RedisConnectionError):
            redis_client._ensure_connected()
            
    # ===== キー・バリュー操作のテスト =====
    
    @pytest.mark.asyncio
    async def test_set_success(self, redis_client, mock_redis):
        """値設定成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.set.return_value = True
        
        # 文字列値
        result = await redis_client.set("key1", "value1", ex=3600)
        assert result is True
        mock_redis.set.assert_called_with("key1", "value1", ex=3600, px=None, nx=False, xx=False)
        
        # オブジェクト値（シリアライズ）
        data = {"name": "test", "value": 123}
        await redis_client.set("key2", data, serialize=True)
        expected_json = json.dumps(data, ensure_ascii=False)
        mock_redis.set.assert_called_with("key2", expected_json, ex=None, px=None, nx=False, xx=False)
        
        # シリアライズなし
        await redis_client.set("key3", data, serialize=False)
        mock_redis.set.assert_called_with("key3", data, ex=None, px=None, nx=False, xx=False)
        
    @pytest.mark.asyncio
    async def test_get_success(self, redis_client, mock_redis):
        """値取得成功のテスト"""
        redis_client.redis = mock_redis
        
        # 文字列値
        mock_redis.get.return_value = "value1"
        result = await redis_client.get("key1")
        assert result == "value1"
        
        # JSON値（デシリアライズ）
        data = {"name": "test", "value": 123}
        mock_redis.get.return_value = json.dumps(data, ensure_ascii=False)
        result = await redis_client.get("key2", deserialize=True)
        assert result == data
        
        # 存在しないキー
        mock_redis.get.return_value = None
        result = await redis_client.get("nonexistent")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_delete_success(self, redis_client, mock_redis):
        """キー削除成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.delete.return_value = 2
        
        result = await redis_client.delete("key1", "key2")
        assert result == 2
        mock_redis.delete.assert_called_once_with("key1", "key2")
        
    @pytest.mark.asyncio
    async def test_exists_success(self, redis_client, mock_redis):
        """キー存在確認成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.exists.return_value = 1
        
        result = await redis_client.exists("key1", "key2")
        assert result == 1
        mock_redis.exists.assert_called_once_with("key1", "key2")
        
    @pytest.mark.asyncio
    async def test_expire_success(self, redis_client, mock_redis):
        """有効期限設定成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.expire.return_value = True
        
        result = await redis_client.expire("key1", 3600)
        assert result is True
        mock_redis.expire.assert_called_once_with("key1", 3600)
        
    @pytest.mark.asyncio
    async def test_ttl_success(self, redis_client, mock_redis):
        """TTL取得成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.ttl.return_value = 3600
        
        result = await redis_client.ttl("key1")
        assert result == 3600
        mock_redis.ttl.assert_called_once_with("key1")
        
    # ===== リスト操作のテスト =====
    
    @pytest.mark.asyncio
    async def test_lpush_success(self, redis_client, mock_redis):
        """リスト追加成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.lpush.return_value = 3
        
        # 文字列値
        result = await redis_client.lpush("list1", "value1", "value2")
        assert result == 3
        mock_redis.lpush.assert_called_with("list1", "value1", "value2")
        
        # オブジェクト値（シリアライズ）
        data = {"name": "test"}
        await redis_client.lpush("list2", data, serialize=True)
        expected_json = json.dumps(data, ensure_ascii=False)
        mock_redis.lpush.assert_called_with("list2", expected_json)
        
    @pytest.mark.asyncio
    async def test_rpop_success(self, redis_client, mock_redis):
        """リスト取得成功のテスト"""
        redis_client.redis = mock_redis
        
        # 文字列値
        mock_redis.rpop.return_value = "value1"
        result = await redis_client.rpop("list1")
        assert result == "value1"
        
        # JSON値（デシリアライズ）
        data = {"name": "test"}
        mock_redis.rpop.return_value = json.dumps(data, ensure_ascii=False)
        result = await redis_client.rpop("list2", deserialize=True)
        assert result == data
        
        # 空のリスト
        mock_redis.rpop.return_value = None
        result = await redis_client.rpop("empty_list")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_llen_success(self, redis_client, mock_redis):
        """リスト長取得成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.llen.return_value = 5
        
        result = await redis_client.llen("list1")
        assert result == 5
        mock_redis.llen.assert_called_once_with("list1")
        
    @pytest.mark.asyncio
    async def test_lrange_success(self, redis_client, mock_redis):
        """リスト範囲取得成功のテスト"""
        redis_client.redis = mock_redis
        
        # 文字列値
        mock_redis.lrange.return_value = ["value1", "value2"]
        result = await redis_client.lrange("list1", 0, -1)
        assert result == ["value1", "value2"]
        mock_redis.lrange.assert_called_with("list1", 0, -1)
        
        # JSON値（デシリアライズ）
        data1 = {"name": "test1"}
        data2 = {"name": "test2"}
        mock_redis.lrange.return_value = [
            json.dumps(data1, ensure_ascii=False),
            json.dumps(data2, ensure_ascii=False)
        ]
        result = await redis_client.lrange("list2", 0, 1, deserialize=True)
        assert result == [data1, data2]
        
    # ===== セット操作のテスト =====
    
    @pytest.mark.asyncio
    async def test_sadd_success(self, redis_client, mock_redis):
        """セット追加成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.sadd.return_value = 2
        
        result = await redis_client.sadd("set1", "value1", "value2")
        assert result == 2
        mock_redis.sadd.assert_called_with("set1", "value1", "value2")
        
    @pytest.mark.asyncio
    async def test_smembers_success(self, redis_client, mock_redis):
        """セット要素取得成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.smembers.return_value = {"value1", "value2"}
        
        result = await redis_client.smembers("set1")
        assert result == {"value1", "value2"}
        mock_redis.smembers.assert_called_once_with("set1")
        
    # ===== ハッシュ操作のテスト =====
    
    @pytest.mark.asyncio
    async def test_hset_success(self, redis_client, mock_redis):
        """ハッシュ設定成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.hset.return_value = 1
        
        # 文字列値
        result = await redis_client.hset("hash1", "field1", "value1")
        assert result == 1
        mock_redis.hset.assert_called_with("hash1", "field1", "value1")
        
        # オブジェクト値（シリアライズ）
        data = {"name": "test"}
        await redis_client.hset("hash2", "field2", data, serialize=True)
        expected_json = json.dumps(data, ensure_ascii=False)
        mock_redis.hset.assert_called_with("hash2", "field2", expected_json)
        
    @pytest.mark.asyncio
    async def test_hget_success(self, redis_client, mock_redis):
        """ハッシュ取得成功のテスト"""
        redis_client.redis = mock_redis
        
        # 文字列値
        mock_redis.hget.return_value = "value1"
        result = await redis_client.hget("hash1", "field1")
        assert result == "value1"
        
        # JSON値（デシリアライズ）
        data = {"name": "test"}
        mock_redis.hget.return_value = json.dumps(data, ensure_ascii=False)
        result = await redis_client.hget("hash2", "field2", deserialize=True)
        assert result == data
        
        # 存在しないフィールド
        mock_redis.hget.return_value = None
        result = await redis_client.hget("hash1", "nonexistent")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_hgetall_success(self, redis_client, mock_redis):
        """ハッシュ全取得成功のテスト"""
        redis_client.redis = mock_redis
        
        # 文字列値
        mock_redis.hgetall.return_value = {"field1": "value1", "field2": "value2"}
        result = await redis_client.hgetall("hash1")
        assert result == {"field1": "value1", "field2": "value2"}
        
        # JSON値（デシリアライズ）
        data1 = {"name": "test1"}
        data2 = {"name": "test2"}
        mock_redis.hgetall.return_value = {
            "field1": json.dumps(data1, ensure_ascii=False),
            "field2": json.dumps(data2, ensure_ascii=False)
        }
        result = await redis_client.hgetall("hash2", deserialize=True)
        assert result == {"field1": data1, "field2": data2}
        
    # ===== その他の操作のテスト =====
    
    @pytest.mark.asyncio
    async def test_keys_success(self, redis_client, mock_redis):
        """キー検索成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.keys.return_value = ["key1", "key2", "key3"]
        
        result = await redis_client.keys("key*")
        assert result == ["key1", "key2", "key3"]
        mock_redis.keys.assert_called_once_with("key*")
        
    @pytest.mark.asyncio
    async def test_flushdb_success(self, redis_client, mock_redis):
        """データベースクリア成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.flushdb.return_value = True
        
        result = await redis_client.flushdb()
        assert result is True
        mock_redis.flushdb.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_ping_success(self, redis_client, mock_redis):
        """Ping成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.ping.return_value = "PONG"
        
        result = await redis_client.ping()
        assert result is True
        
        # バイト形式のレスポンス
        mock_redis.ping.return_value = b"PONG"
        result = await redis_client.ping()
        assert result is True
        
    @pytest.mark.asyncio
    async def test_ping_failure(self, redis_client, mock_redis):
        """Ping失敗のテスト"""
        redis_client.redis = mock_redis
        mock_redis.ping.side_effect = Exception("Connection lost")
        
        result = await redis_client.ping()
        assert result is False
        
    @pytest.mark.asyncio
    async def test_info_success(self, redis_client, mock_redis):
        """Redis情報取得成功のテスト"""
        redis_client.redis = mock_redis
        mock_info = {"redis_version": "6.2.0", "used_memory": "1024000"}
        mock_redis.info.return_value = mock_info
        
        result = await redis_client.info("memory")
        assert result == mock_info
        mock_redis.info.assert_called_once_with("memory")
        
    @pytest.mark.asyncio
    async def test_health_check_success(self, redis_client, mock_redis):
        """ヘルスチェック成功のテスト"""
        redis_client.redis = mock_redis
        mock_redis.ping.return_value = "PONG"
        
        is_healthy = await redis_client.health_check()
        assert is_healthy is True
        
    @pytest.mark.asyncio
    async def test_health_check_failure(self, redis_client, mock_redis):
        """ヘルスチェック失敗のテスト"""
        redis_client.redis = mock_redis
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        is_healthy = await redis_client.health_check()
        assert is_healthy is False
        
    @pytest.mark.asyncio
    async def test_stats_tracking(self, redis_client, mock_redis):
        """統計情報追跡のテスト"""
        redis_client.redis = mock_redis
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "value"
        mock_redis.delete.return_value = 2
        mock_redis.lpush.return_value = 1
        mock_redis.rpop.return_value = "value"
        mock_redis.sadd.return_value = 1
        mock_redis.hset.return_value = 1
        mock_redis.hget.return_value = "value"
        mock_redis.flushdb.return_value = True
        
        # 各種操作を実行
        await redis_client.set("key1", "value1")
        await redis_client.set("key2", "value2")
        await redis_client.get("key1")
        await redis_client.delete("key1", "key2")
        await redis_client.lpush("list1", "value1", "value2")
        await redis_client.rpop("list1")
        await redis_client.sadd("set1", "value1")
        await redis_client.hset("hash1", "field1", "value1")
        await redis_client.hget("hash1", "field1")
        await redis_client.flushdb()
        
        assert redis_client.stats['sets'] == 2
        assert redis_client.stats['gets'] == 1
        assert redis_client.stats['deletes'] == 2
        assert redis_client.stats['list_pushes'] == 2
        assert redis_client.stats['list_pops'] == 1
        assert redis_client.stats['set_adds'] == 1
        assert redis_client.stats['hash_sets'] == 1
        assert redis_client.stats['hash_gets'] == 1
        assert redis_client.stats['flushes'] == 1
        
    @pytest.mark.asyncio
    async def test_error_handling(self, redis_client, mock_redis):
        """エラーハンドリングのテスト"""
        redis_client.redis = mock_redis
        
        # 一般的なRedisエラー
        mock_redis.set.side_effect = Exception("Redis error")
        with pytest.raises(RedisError):
            await redis_client.set("key", "value")
            
        mock_redis.get.side_effect = Exception("Redis error")
        with pytest.raises(RedisError):
            await redis_client.get("key")
            
        mock_redis.delete.side_effect = Exception("Redis error")
        with pytest.raises(RedisError):
            await redis_client.delete("key")
            
    @pytest.mark.asyncio
    async def test_serialization_edge_cases(self, redis_client, mock_redis):
        """シリアライゼーションのエッジケースのテスト"""
        redis_client.redis = mock_redis
        mock_redis.set.return_value = True
        mock_redis.get.return_value = "not json"
        
        # JSONでない文字列の取得
        result = await redis_client.get("key", deserialize=True)
        assert result == "not json"
        
        # 数値型の設定（シリアライズしない）
        await redis_client.set("key", 123, serialize=True)
        mock_redis.set.assert_called_with("key", 123, ex=None, px=None, nx=False, xx=False) 