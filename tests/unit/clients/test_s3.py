"""S3クライアントのテスト"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError, NoCredentialsError

from src.clients.s3 import (
    S3Client,
    S3Error,
    BucketNotFoundError,
    ObjectNotFoundError
)


@pytest.fixture
def s3_client():
    """S3クライアントのフィクスチャ"""
    return S3Client(
        aws_access_key_id="test_key",
        aws_secret_access_key="test_secret",
        region_name="us-east-1",
        bucket_name="test-bucket"
    )


@pytest.fixture
def mock_s3_client():
    """モックS3クライアントのフィクスチャ"""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


class TestS3Client:
    """S3クライアントのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, s3_client):
        """初期化のテスト"""
        assert s3_client.aws_access_key_id == "test_key"
        assert s3_client.aws_secret_access_key == "test_secret"
        assert s3_client.region_name == "us-east-1"
        assert s3_client.bucket_name == "test-bucket"
        
    @pytest.mark.asyncio
    async def test_context_manager(self, s3_client):
        """コンテキストマネージャーのテスト"""
        with patch('aioboto3.Session') as mock_session:
            mock_client = AsyncMock()
            mock_session.return_value.client.return_value = mock_client
            
            async with s3_client as client:
                assert client is s3_client
                assert s3_client.s3_client is mock_client
                mock_client.__aenter__.assert_called_once()
                
            mock_client.__aexit__.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_upload_file_success(self, s3_client, mock_s3_client):
        """ファイルアップロード成功のテスト"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("test content")
            temp_path = Path(f.name)
            
        try:
            s3_client.s3_client = mock_s3_client
            
            url = await s3_client.upload_file(
                file_path=temp_path,
                key="test/file.txt",
                content_type="text/plain",
                metadata={"author": "test"},
                public_read=True
            )
            
            assert url == "https://test-bucket.s3.us-east-1.amazonaws.com/test/file.txt"
            mock_s3_client.upload_file.assert_called_once()
            
            # 引数の確認
            args, kwargs = mock_s3_client.upload_file.call_args
            assert args[0] == str(temp_path)
            assert args[1] == "test-bucket"
            assert args[2] == "test/file.txt"
            assert kwargs['ExtraArgs']['ContentType'] == "text/plain"
            assert kwargs['ExtraArgs']['Metadata'] == {"author": "test"}
            assert kwargs['ExtraArgs']['ACL'] == "public-read"
            
        finally:
            temp_path.unlink()
            
    @pytest.mark.asyncio
    async def test_upload_file_not_found(self, s3_client):
        """存在しないファイルのアップロードテスト"""
        s3_client.s3_client = AsyncMock()
        
        with pytest.raises(FileNotFoundError):
            await s3_client.upload_file(
                file_path="nonexistent.txt",
                key="test/file.txt"
            )
            
    @pytest.mark.asyncio
    async def test_upload_file_no_bucket(self):
        """バケット名未指定のテスト"""
        client = S3Client(
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret"
        )
        client.s3_client = AsyncMock()
        
        with pytest.raises(S3Error, match="バケット名が指定されていません"):
            await client.upload_file(
                file_path="test.txt",
                key="test/file.txt"
            )
            
    @pytest.mark.asyncio
    async def test_upload_file_bucket_not_found(self, s3_client, mock_s3_client):
        """バケットが見つからない場合のテスト"""
        mock_s3_client.upload_file.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket'}},
            'upload_file'
        )
        s3_client.s3_client = mock_s3_client
        
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(BucketNotFoundError):
                await s3_client.upload_file(
                    file_path=f.name,
                    key="test/file.txt"
                )
                
    @pytest.mark.asyncio
    async def test_upload_file_no_credentials(self, s3_client, mock_s3_client):
        """認証情報なしのテスト"""
        mock_s3_client.upload_file.side_effect = NoCredentialsError()
        s3_client.s3_client = mock_s3_client
        
        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(S3Error, match="AWS認証情報が設定されていません"):
                await s3_client.upload_file(
                    file_path=f.name,
                    key="test/file.txt"
                )
                
    @pytest.mark.asyncio
    async def test_upload_bytes_success(self, s3_client, mock_s3_client):
        """バイトデータアップロード成功のテスト"""
        s3_client.s3_client = mock_s3_client
        test_data = b"test binary data"
        
        url = await s3_client.upload_bytes(
            data=test_data,
            key="test/data.bin",
            content_type="application/octet-stream",
            metadata={"size": str(len(test_data))},
            public_read=True
        )
        
        assert url == "https://test-bucket.s3.us-east-1.amazonaws.com/test/data.bin"
        mock_s3_client.put_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/data.bin",
            Body=test_data,
            ContentType="application/octet-stream",
            Metadata={"size": str(len(test_data))},
            ACL="public-read"
        )
        
    @pytest.mark.asyncio
    async def test_download_file_success(self, s3_client, mock_s3_client):
        """ファイルダウンロード成功のテスト"""
        s3_client.s3_client = mock_s3_client
        
        with tempfile.TemporaryDirectory() as temp_dir:
            download_path = Path(temp_dir) / "downloaded.txt"
            
            result_path = await s3_client.download_file(
                key="test/file.txt",
                file_path=download_path
            )
            
            assert result_path == download_path
            mock_s3_client.download_file.assert_called_once_with(
                "test-bucket",
                "test/file.txt",
                str(download_path)
            )
            
    @pytest.mark.asyncio
    async def test_download_file_object_not_found(self, s3_client, mock_s3_client):
        """存在しないオブジェクトのダウンロードテスト"""
        mock_s3_client.download_file.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'download_file'
        )
        s3_client.s3_client = mock_s3_client
        
        with pytest.raises(ObjectNotFoundError):
            await s3_client.download_file(
                key="nonexistent.txt",
                file_path="download.txt"
            )
            
    @pytest.mark.asyncio
    async def test_download_bytes_success(self, s3_client, mock_s3_client):
        """バイトデータダウンロード成功のテスト"""
        test_data = b"test binary data"
        mock_response = {
            'Body': AsyncMock()
        }
        mock_response['Body'].read.return_value = test_data
        mock_s3_client.get_object.return_value = mock_response
        s3_client.s3_client = mock_s3_client
        
        data = await s3_client.download_bytes(key="test/data.bin")
        
        assert data == test_data
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/data.bin"
        )
        
    @pytest.mark.asyncio
    async def test_delete_object_success(self, s3_client, mock_s3_client):
        """オブジェクト削除成功のテスト"""
        s3_client.s3_client = mock_s3_client
        
        result = await s3_client.delete_object(key="test/file.txt")
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt"
        )
        
    @pytest.mark.asyncio
    async def test_list_objects_success(self, s3_client, mock_s3_client):
        """オブジェクト一覧取得成功のテスト"""
        mock_objects = [
            {'Key': 'test/file1.txt', 'Size': 100},
            {'Key': 'test/file2.txt', 'Size': 200}
        ]
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': mock_objects
        }
        s3_client.s3_client = mock_s3_client
        
        objects = await s3_client.list_objects(
            prefix="test/",
            max_keys=100
        )
        
        assert objects == mock_objects
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket="test-bucket",
            Prefix="test/",
            MaxKeys=100
        )
        
    @pytest.mark.asyncio
    async def test_list_objects_empty(self, s3_client, mock_s3_client):
        """空のオブジェクト一覧のテスト"""
        mock_s3_client.list_objects_v2.return_value = {}
        s3_client.s3_client = mock_s3_client
        
        objects = await s3_client.list_objects()
        
        assert objects == []
        
    @pytest.mark.asyncio
    async def test_object_exists_true(self, s3_client, mock_s3_client):
        """オブジェクト存在確認（存在する場合）のテスト"""
        s3_client.s3_client = mock_s3_client
        
        exists = await s3_client.object_exists(key="test/file.txt")
        
        assert exists is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt"
        )
        
    @pytest.mark.asyncio
    async def test_object_exists_false(self, s3_client, mock_s3_client):
        """オブジェクト存在確認（存在しない場合）のテスト"""
        mock_s3_client.head_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey'}},
            'head_object'
        )
        s3_client.s3_client = mock_s3_client
        
        exists = await s3_client.object_exists(key="nonexistent.txt")
        
        assert exists is False
        
    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self, s3_client, mock_s3_client):
        """署名付きURL生成成功のテスト"""
        expected_url = "https://test-bucket.s3.amazonaws.com/test/file.txt?signature=..."
        mock_s3_client.generate_presigned_url.return_value = expected_url
        s3_client.s3_client = mock_s3_client
        
        url = await s3_client.generate_presigned_url(
            key="test/file.txt",
            expiration=7200,
            method="get_object"
        )
        
        assert url == expected_url
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={'Bucket': "test-bucket", 'Key': "test/file.txt"},
            ExpiresIn=7200
        )
        
    @pytest.mark.asyncio
    async def test_health_check_success(self, s3_client, mock_s3_client):
        """ヘルスチェック成功のテスト"""
        s3_client.s3_client = mock_s3_client
        
        is_healthy = await s3_client.health_check()
        
        assert is_healthy is True
        mock_s3_client.head_bucket.assert_called_once_with(
            Bucket="test-bucket"
        )
        
    @pytest.mark.asyncio
    async def test_health_check_no_bucket(self):
        """デフォルトバケットなしのヘルスチェックテスト"""
        client = S3Client(
            aws_access_key_id="test_key",
            aws_secret_access_key="test_secret"
        )
        mock_s3_client = AsyncMock()
        client.s3_client = mock_s3_client
        
        is_healthy = await client.health_check()
        
        assert is_healthy is True
        mock_s3_client.list_buckets.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_health_check_failure(self, s3_client, mock_s3_client):
        """ヘルスチェック失敗のテスト"""
        mock_s3_client.head_bucket.side_effect = Exception("Connection failed")
        s3_client.s3_client = mock_s3_client
        
        is_healthy = await s3_client.health_check()
        
        assert is_healthy is False
        
    @pytest.mark.asyncio
    async def test_stats_tracking(self, s3_client, mock_s3_client):
        """統計情報追跡のテスト"""
        s3_client.s3_client = mock_s3_client
        
        # アップロード
        with tempfile.NamedTemporaryFile() as f:
            await s3_client.upload_file(f.name, "test1.txt")
            
        # バイトアップロード
        await s3_client.upload_bytes(b"data", "test2.txt")
        
        # ダウンロード
        mock_response = {'Body': AsyncMock()}
        mock_response['Body'].read.return_value = b"data"
        mock_s3_client.get_object.return_value = mock_response
        await s3_client.download_bytes("test1.txt")
        
        # 削除
        await s3_client.delete_object("test1.txt")
        
        assert s3_client.stats['uploads'] == 2
        assert s3_client.stats['downloads'] == 1
        assert s3_client.stats['deletions'] == 1 