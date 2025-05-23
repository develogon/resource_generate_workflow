"""AWS S3クライアント実装"""

import asyncio
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
from urllib.parse import urlparse

import aioboto3
from botocore.exceptions import ClientError, NoCredentialsError

from .base import BaseClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class S3Error(Exception):
    """S3操作エラー"""
    pass


class BucketNotFoundError(S3Error):
    """バケットが見つからないエラー"""
    pass


class ObjectNotFoundError(S3Error):
    """オブジェクトが見つからないエラー"""
    pass


class S3Client(BaseClient):
    """AWS S3クライアント"""
    
    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        bucket_name: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.region_name = region_name
        self.bucket_name = bucket_name
        self.session = None
        self.s3_client = None
        
    async def __aenter__(self):
        await super().__aenter__()
        self.session = aioboto3.Session(
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name
        )
        self.s3_client = self.session.client('s3')
        await self.s3_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.s3_client:
            await self.s3_client.__aexit__(exc_type, exc_val, exc_tb)
        await super().__aexit__(exc_type, exc_val, exc_tb)
        
    async def upload_file(
        self,
        file_path: Union[str, Path],
        key: str,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        public_read: bool = False
    ) -> str:
        """ファイルをS3にアップロード
        
        Args:
            file_path: アップロードするファイルのパス
            key: S3オブジェクトキー
            bucket: バケット名（未指定時はデフォルトバケット使用）
            content_type: コンテンツタイプ（未指定時は自動判定）
            metadata: メタデータ
            public_read: パブリック読み取り許可
            
        Returns:
            アップロードされたオブジェクトのURL
        """
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
            
        # コンテンツタイプの自動判定
        if not content_type:
            content_type, _ = mimetypes.guess_type(str(file_path))
            content_type = content_type or 'application/octet-stream'
            
        # アップロード引数の準備
        extra_args = {
            'ContentType': content_type,
            'Metadata': metadata or {}
        }
        
        if public_read:
            extra_args['ACL'] = 'public-read'
            
        try:
            await self.s3_client.upload_file(
                str(file_path),
                bucket,
                key,
                ExtraArgs=extra_args
            )
            
            # URLの生成
            url = f"https://{bucket}.s3.{self.region_name}.amazonaws.com/{key}"
            
            logger.info(f"ファイルをアップロードしました: {file_path} -> {url}")
            self.stats['uploads'] = self.stats.get('uploads', 0) + 1
            
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"アップロードに失敗しました: {e}")
        except NoCredentialsError:
            raise S3Error("AWS認証情報が設定されていません")
            
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        bucket: Optional[str] = None,
        content_type: str = 'application/octet-stream',
        metadata: Optional[Dict[str, str]] = None,
        public_read: bool = False
    ) -> str:
        """バイトデータをS3にアップロード"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        extra_args = {
            'ContentType': content_type,
            'Metadata': metadata or {}
        }
        
        if public_read:
            extra_args['ACL'] = 'public-read'
            
        try:
            await self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                **extra_args
            )
            
            url = f"https://{bucket}.s3.{self.region_name}.amazonaws.com/{key}"
            
            logger.info(f"バイトデータをアップロードしました: {key} ({len(data)} bytes)")
            self.stats['uploads'] = self.stats.get('uploads', 0) + 1
            
            return url
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"アップロードに失敗しました: {e}")
            
    async def download_file(
        self,
        key: str,
        file_path: Union[str, Path],
        bucket: Optional[str] = None
    ) -> Path:
        """S3からファイルをダウンロード"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            await self.s3_client.download_file(bucket, key, str(file_path))
            
            logger.info(f"ファイルをダウンロードしました: {key} -> {file_path}")
            self.stats['downloads'] = self.stats.get('downloads', 0) + 1
            
            return file_path
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise ObjectNotFoundError(f"オブジェクトが見つかりません: {key}")
            elif error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"ダウンロードに失敗しました: {e}")
            
    async def download_bytes(
        self,
        key: str,
        bucket: Optional[str] = None
    ) -> bytes:
        """S3からバイトデータをダウンロード"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        try:
            response = await self.s3_client.get_object(Bucket=bucket, Key=key)
            data = await response['Body'].read()
            
            logger.info(f"バイトデータをダウンロードしました: {key} ({len(data)} bytes)")
            self.stats['downloads'] = self.stats.get('downloads', 0) + 1
            
            return data
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise ObjectNotFoundError(f"オブジェクトが見つかりません: {key}")
            elif error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"ダウンロードに失敗しました: {e}")
            
    async def delete_object(
        self,
        key: str,
        bucket: Optional[str] = None
    ) -> bool:
        """S3オブジェクトを削除"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        try:
            await self.s3_client.delete_object(Bucket=bucket, Key=key)
            
            logger.info(f"オブジェクトを削除しました: {key}")
            self.stats['deletions'] = self.stats.get('deletions', 0) + 1
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"削除に失敗しました: {e}")
            
    async def list_objects(
        self,
        prefix: str = "",
        bucket: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[Dict]:
        """S3オブジェクトの一覧取得"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        try:
            response = await self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = response.get('Contents', [])
            
            logger.info(f"オブジェクト一覧を取得しました: {len(objects)}件")
            
            return objects
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"一覧取得に失敗しました: {e}")
            
    async def object_exists(
        self,
        key: str,
        bucket: Optional[str] = None
    ) -> bool:
        """S3オブジェクトの存在確認"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        try:
            await self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                return False
            elif error_code == 'NoSuchBucket':
                raise BucketNotFoundError(f"バケットが見つかりません: {bucket}")
            raise S3Error(f"存在確認に失敗しました: {e}")
            
    async def generate_presigned_url(
        self,
        key: str,
        bucket: Optional[str] = None,
        expiration: int = 3600,
        method: str = 'get_object'
    ) -> str:
        """署名付きURLの生成"""
        bucket = bucket or self.bucket_name
        if not bucket:
            raise S3Error("バケット名が指定されていません")
            
        try:
            url = await self.s3_client.generate_presigned_url(
                method,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            
            logger.info(f"署名付きURLを生成しました: {key} (有効期限: {expiration}秒)")
            
            return url
            
        except ClientError as e:
            raise S3Error(f"署名付きURL生成に失敗しました: {e}")
            
    async def health_check(self) -> bool:
        """S3接続のヘルスチェック"""
        try:
            if self.bucket_name:
                await self.s3_client.head_bucket(Bucket=self.bucket_name)
            else:
                # デフォルトバケットがない場合はバケット一覧を取得
                await self.s3_client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"S3ヘルスチェックに失敗しました: {e}")
            return False 