"""Redis クライアント実装"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any, Set
from urllib.parse import urlparse

import redis.asyncio as redis
from redis.asyncio import Redis

from ..utils.logger import get_logger

logger = get_logger(__name__)


class RedisError(Exception):
    """Redis操作エラー"""
    pass


class RedisConnectionError(RedisError):
    """Redis接続エラー"""
    pass


class RedisClient:
    """Redis クライアント"""
    
    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        encoding: str = "utf-8",
        decode_responses: bool = True,
        **kwargs
    ):
        self.url = url
        self.encoding = encoding
        self.decode_responses = decode_responses
        self.redis: Optional[Redis] = None
        
        # URL解析
        parsed = urlparse(url)
        self.host = parsed.hostname or "localhost"
        self.port = parsed.port or 6379
        self.db = int(parsed.path.lstrip('/')) if parsed.path else 0
        self.password = parsed.password
        
        # 統計情報
        self.stats = {}
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        
    async def connect(self) -> None:
        """Redisに接続"""
        try:
            self.redis = redis.from_url(
                self.url,
                encoding=self.encoding,
                decode_responses=self.decode_responses
            )
            
            # 接続テスト
            await self.redis.ping()
            
            logger.info(f"Redisに接続しました: {self.host}:{self.port}/{self.db}")
            
        except Exception as e:
            raise RedisConnectionError(f"Redis接続に失敗しました: {e}")
            
    async def disconnect(self) -> None:
        """Redis接続を切断"""
        if self.redis:
            await self.redis.aclose()
            self.redis = None
            logger.info("Redis接続を切断しました")
            
    def _ensure_connected(self) -> None:
        """接続確認"""
        if not self.redis:
            raise RedisConnectionError("Redisに接続されていません")
            
    # ===== 基本的なキー・バリュー操作 =====
    
    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
        serialize: bool = True
    ) -> bool:
        """値を設定
        
        Args:
            key: キー
            value: 値
            ex: 有効期限（秒）
            px: 有効期限（ミリ秒）
            nx: キーが存在しない場合のみ設定
            xx: キーが存在する場合のみ設定
            serialize: 値をシリアライズするか
            
        Returns:
            設定成功かどうか
        """
        self._ensure_connected()
        
        try:
            if serialize and not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value, ensure_ascii=False)
                
            result = await self.redis.set(
                key, value, ex=ex, px=px, nx=nx, xx=xx
            )
            
            if result:
                logger.debug(f"値を設定しました: {key}")
                self.stats['sets'] = self.stats.get('sets', 0) + 1
                
            return bool(result)
            
        except Exception as e:
            raise RedisError(f"値の設定に失敗しました: {e}")
            
    async def get(
        self,
        key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """値を取得
        
        Args:
            key: キー
            deserialize: 値をデシリアライズするか
            
        Returns:
            取得した値（存在しない場合はNone）
        """
        self._ensure_connected()
        
        try:
            value = await self.redis.get(key)
            
            if value is None:
                return None
                
            if deserialize and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    # JSONでない場合はそのまま返す
                    pass
                    
            logger.debug(f"値を取得しました: {key}")
            self.stats['gets'] = self.stats.get('gets', 0) + 1
            
            return value
            
        except Exception as e:
            raise RedisError(f"値の取得に失敗しました: {e}")
            
    async def delete(self, *keys: str) -> int:
        """キーを削除
        
        Args:
            keys: 削除するキー
            
        Returns:
            削除されたキーの数
        """
        self._ensure_connected()
        
        try:
            count = await self.redis.delete(*keys)
            
            logger.debug(f"キーを削除しました: {keys} ({count}件)")
            self.stats['deletes'] = self.stats.get('deletes', 0) + count
            
            return count
            
        except Exception as e:
            raise RedisError(f"キーの削除に失敗しました: {e}")
            
    async def exists(self, *keys: str) -> int:
        """キーの存在確認
        
        Args:
            keys: 確認するキー
            
        Returns:
            存在するキーの数
        """
        self._ensure_connected()
        
        try:
            count = await self.redis.exists(*keys)
            logger.debug(f"キーの存在確認: {keys} ({count}件存在)")
            return count
            
        except Exception as e:
            raise RedisError(f"キーの存在確認に失敗しました: {e}")
            
    async def expire(self, key: str, seconds: int) -> bool:
        """キーに有効期限を設定
        
        Args:
            key: キー
            seconds: 有効期限（秒）
            
        Returns:
            設定成功かどうか
        """
        self._ensure_connected()
        
        try:
            result = await self.redis.expire(key, seconds)
            
            if result:
                logger.debug(f"有効期限を設定しました: {key} ({seconds}秒)")
                
            return bool(result)
            
        except Exception as e:
            raise RedisError(f"有効期限の設定に失敗しました: {e}")
            
    async def ttl(self, key: str) -> int:
        """キーの残り有効期限を取得
        
        Args:
            key: キー
            
        Returns:
            残り有効期限（秒）、-1: 無期限、-2: 存在しない
        """
        self._ensure_connected()
        
        try:
            ttl_value = await self.redis.ttl(key)
            logger.debug(f"TTLを取得しました: {key} ({ttl_value}秒)")
            return ttl_value
            
        except Exception as e:
            raise RedisError(f"TTLの取得に失敗しました: {e}")
            
    # ===== リスト操作 =====
    
    async def lpush(self, key: str, *values: Any, serialize: bool = True) -> int:
        """リストの先頭に要素を追加
        
        Args:
            key: キー
            values: 追加する値
            serialize: 値をシリアライズするか
            
        Returns:
            リストの長さ
        """
        self._ensure_connected()
        
        try:
            if serialize:
                values = [
                    json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, bytes, int, float)) else v
                    for v in values
                ]
                
            length = await self.redis.lpush(key, *values)
            
            logger.debug(f"リストに要素を追加しました: {key} ({len(values)}件)")
            self.stats['list_pushes'] = self.stats.get('list_pushes', 0) + len(values)
            
            return length
            
        except Exception as e:
            raise RedisError(f"リストへの追加に失敗しました: {e}")
            
    async def rpop(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """リストの末尾から要素を取得・削除
        
        Args:
            key: キー
            deserialize: 値をデシリアライズするか
            
        Returns:
            取得した値（リストが空の場合はNone）
        """
        self._ensure_connected()
        
        try:
            value = await self.redis.rpop(key)
            
            if value is None:
                return None
                
            if deserialize and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
                    
            logger.debug(f"リストから要素を取得しました: {key}")
            self.stats['list_pops'] = self.stats.get('list_pops', 0) + 1
            
            return value
            
        except Exception as e:
            raise RedisError(f"リストからの取得に失敗しました: {e}")
            
    async def llen(self, key: str) -> int:
        """リストの長さを取得
        
        Args:
            key: キー
            
        Returns:
            リストの長さ
        """
        self._ensure_connected()
        
        try:
            length = await self.redis.llen(key)
            logger.debug(f"リストの長さを取得しました: {key} ({length})")
            return length
            
        except Exception as e:
            raise RedisError(f"リストの長さ取得に失敗しました: {e}")
            
    async def lrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        deserialize: bool = True
    ) -> List[Any]:
        """リストの範囲を取得
        
        Args:
            key: キー
            start: 開始インデックス
            end: 終了インデックス
            deserialize: 値をデシリアライズするか
            
        Returns:
            取得した値のリスト
        """
        self._ensure_connected()
        
        try:
            values = await self.redis.lrange(key, start, end)
            
            if deserialize:
                result = []
                for value in values:
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    result.append(value)
                values = result
                
            logger.debug(f"リストの範囲を取得しました: {key} ({len(values)}件)")
            
            return values
            
        except Exception as e:
            raise RedisError(f"リストの範囲取得に失敗しました: {e}")
            
    # ===== セット操作 =====
    
    async def sadd(self, key: str, *values: Any, serialize: bool = True) -> int:
        """セットに要素を追加
        
        Args:
            key: キー
            values: 追加する値
            serialize: 値をシリアライズするか
            
        Returns:
            追加された要素の数
        """
        self._ensure_connected()
        
        try:
            if serialize:
                values = [
                    json.dumps(v, ensure_ascii=False) if not isinstance(v, (str, bytes, int, float)) else v
                    for v in values
                ]
                
            count = await self.redis.sadd(key, *values)
            
            logger.debug(f"セットに要素を追加しました: {key} ({count}件)")
            self.stats['set_adds'] = self.stats.get('set_adds', 0) + count
            
            return count
            
        except Exception as e:
            raise RedisError(f"セットへの追加に失敗しました: {e}")
            
    async def smembers(self, key: str, deserialize: bool = True) -> Set[Any]:
        """セットの全要素を取得
        
        Args:
            key: キー
            deserialize: 値をデシリアライズするか
            
        Returns:
            セットの要素
        """
        self._ensure_connected()
        
        try:
            values = await self.redis.smembers(key)
            
            if deserialize:
                result = set()
                for value in values:
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    result.add(value)
                values = result
                
            logger.debug(f"セットの要素を取得しました: {key} ({len(values)}件)")
            
            return values
            
        except Exception as e:
            raise RedisError(f"セットの要素取得に失敗しました: {e}")
            
    # ===== ハッシュ操作 =====
    
    async def hset(
        self,
        key: str,
        field: str,
        value: Any,
        serialize: bool = True
    ) -> int:
        """ハッシュのフィールドに値を設定
        
        Args:
            key: キー
            field: フィールド名
            value: 値
            serialize: 値をシリアライズするか
            
        Returns:
            新しく追加されたフィールドの数
        """
        self._ensure_connected()
        
        try:
            if serialize and not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value, ensure_ascii=False)
                
            count = await self.redis.hset(key, field, value)
            
            logger.debug(f"ハッシュのフィールドを設定しました: {key}.{field}")
            self.stats['hash_sets'] = self.stats.get('hash_sets', 0) + 1
            
            return count
            
        except Exception as e:
            raise RedisError(f"ハッシュの設定に失敗しました: {e}")
            
    async def hget(
        self,
        key: str,
        field: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """ハッシュのフィールドの値を取得
        
        Args:
            key: キー
            field: フィールド名
            deserialize: 値をデシリアライズするか
            
        Returns:
            取得した値（存在しない場合はNone）
        """
        self._ensure_connected()
        
        try:
            value = await self.redis.hget(key, field)
            
            if value is None:
                return None
                
            if deserialize and isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass
                    
            logger.debug(f"ハッシュのフィールドを取得しました: {key}.{field}")
            self.stats['hash_gets'] = self.stats.get('hash_gets', 0) + 1
            
            return value
            
        except Exception as e:
            raise RedisError(f"ハッシュの取得に失敗しました: {e}")
            
    async def hgetall(self, key: str, deserialize: bool = True) -> Dict[str, Any]:
        """ハッシュの全フィールドを取得
        
        Args:
            key: キー
            deserialize: 値をデシリアライズするか
            
        Returns:
            ハッシュの全フィールドと値
        """
        self._ensure_connected()
        
        try:
            data = await self.redis.hgetall(key)
            
            if deserialize:
                result = {}
                for field, value in data.items():
                    if isinstance(value, str):
                        try:
                            value = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    result[field] = value
                data = result
                
            logger.debug(f"ハッシュの全フィールドを取得しました: {key} ({len(data)}件)")
            
            return data
            
        except Exception as e:
            raise RedisError(f"ハッシュの全取得に失敗しました: {e}")
            
    # ===== その他の操作 =====
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """パターンにマッチするキーを取得
        
        Args:
            pattern: パターン（ワイルドカード使用可）
            
        Returns:
            マッチしたキーのリスト
        """
        self._ensure_connected()
        
        try:
            keys = await self.redis.keys(pattern)
            logger.debug(f"キーを検索しました: {pattern} ({len(keys)}件)")
            return keys
            
        except Exception as e:
            raise RedisError(f"キーの検索に失敗しました: {e}")
            
    async def flushdb(self) -> bool:
        """現在のデータベースをクリア"""
        self._ensure_connected()
        
        try:
            result = await self.redis.flushdb()
            logger.info("データベースをクリアしました")
            self.stats['flushes'] = self.stats.get('flushes', 0) + 1
            return bool(result)
            
        except Exception as e:
            raise RedisError(f"データベースのクリアに失敗しました: {e}")
            
    async def ping(self) -> bool:
        """接続確認"""
        self._ensure_connected()
        
        try:
            result = await self.redis.ping()
            return result == b"PONG" or result == "PONG" or result is True
            
        except Exception as e:
            logger.error(f"Ping に失敗しました: {e}")
            return False
            
    async def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Redis情報を取得
        
        Args:
            section: 取得するセクション
            
        Returns:
            Redis情報
        """
        self._ensure_connected()
        
        try:
            info = await self.redis.info(section)
            logger.debug(f"Redis情報を取得しました: {section or 'all'}")
            return info
            
        except Exception as e:
            raise RedisError(f"Redis情報の取得に失敗しました: {e}")
            
    async def health_check(self) -> bool:
        """Redis接続のヘルスチェック"""
        try:
            return await self.ping()
        except Exception as e:
            logger.error(f"Redisヘルスチェックに失敗しました: {e}")
            return False 