import pytest
import os
from unittest.mock import patch, MagicMock, mock_open

from services.storage import StorageService
from tests.fixtures.sample_api_responses import SAMPLE_S3_UPLOAD_RESPONSE


class TestStorageService:
    """S3ストレージサービスのテスト"""

    @pytest.fixture
    def mock_config(self):
        """テスト用の設定"""
        return {
            "storage": {
                "aws_access_key_id": "test_access_key",
                "aws_secret_access_key": "test_secret_key",
                "region": "ap-northeast-1",
                "bucket_name": "test-bucket",
                "base_url": "https://test-bucket.s3.ap-northeast-1.amazonaws.com"
            }
        }

    @pytest.fixture
    def storage_service(self, mock_config):
        """ストレージサービスのインスタンス"""
        with patch('boto3.client') as mock_boto3:
            service = StorageService(mock_config)
            # S3クライアントを直接設定
            service._s3_client = MagicMock()
            return service

    def test_init(self, mock_config):
        """初期化のテスト"""
        with patch('boto3.client') as mock_boto3:
            service = StorageService(mock_config)
            
            # boto3.clientが正しい引数で呼ばれたことを確認
            mock_boto3.assert_called_once_with(
                's3',
                aws_access_key_id='test_access_key',
                aws_secret_access_key='test_secret_key',
                region_name='ap-northeast-1'
            )
            
            # 設定値が正しく保存されていることを確認
            assert service._bucket_name == 'test-bucket'
            assert service._base_url == 'https://test-bucket.s3.ap-northeast-1.amazonaws.com'

    def test_upload_file(self, storage_service, temp_dir):
        """ファイルアップロードのテスト"""
        # テストファイルの作成
        test_file_path = os.path.join(str(temp_dir), "test_image.png")
        with open(test_file_path, 'wb') as f:
            f.write(b'test image data')
        
        # S3アップロードのモック
        storage_service._s3_client.upload_file.return_value = None
        storage_service._s3_client.head_object.return_value = {}
        
        # アップロード実行
        remote_path = "images/test_image.png"
        result = storage_service.upload_file(test_file_path, remote_path)
        
        # S3クライアントの呼び出しを確認
        storage_service._s3_client.upload_file.assert_called_once_with(
            test_file_path,
            'test-bucket',
            'images/test_image.png'
        )
        
        # 結果のURLを確認
        expected_url = "https://test-bucket.s3.ap-northeast-1.amazonaws.com/images/test_image.png"
        assert result == expected_url

    def test_get_url(self, storage_service):
        """URL取得のテスト"""
        remote_path = "images/test_image.png"
        url = storage_service.get_url(remote_path)
        
        expected_url = "https://test-bucket.s3.ap-northeast-1.amazonaws.com/images/test_image.png"
        assert url == expected_url
        
        # カスタムパラメータ付きURL
        url_with_params = storage_service.get_url(remote_path, expire=3600)
        
        # presigned_urlが生成されたことを確認
        storage_service._s3_client.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={
                'Bucket': 'test-bucket',
                'Key': 'images/test_image.png'
            },
            ExpiresIn=3600
        )

    def test_delete_file(self, storage_service):
        """ファイル削除のテスト"""
        remote_path = "images/test_image.png"
        storage_service.delete_file(remote_path)
        
        # S3クライアントの呼び出しを確認
        storage_service._s3_client.delete_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='images/test_image.png'
        )

    def test_check_upload_status(self, storage_service):
        """アップロード状態確認のテスト"""
        # オブジェクトが存在する場合
        storage_service._s3_client.head_object.return_value = {
            'ContentLength': 12345,
            'LastModified': 'test_date'
        }
        
        result = storage_service.check_upload_status("images/exists.png")
        assert result is True
        
        # オブジェクトが存在しない場合
        storage_service._s3_client.head_object.side_effect = Exception("Not found")
        
        result = storage_service.check_upload_status("images/not_exists.png")
        assert result is False

    def test_upload_multiple_files(self, storage_service, temp_dir):
        """複数ファイルアップロードのテスト"""
        # テストファイル作成
        file_paths = []
        for i in range(3):
            path = os.path.join(str(temp_dir), f"test_image_{i}.png")
            with open(path, 'wb') as f:
                f.write(f"test image data {i}".encode())
            file_paths.append(path)
        
        # S3アップロードのモック
        storage_service._s3_client.upload_file.return_value = None
        
        # アップロード実行
        remote_dir = "images/"
        results = storage_service.upload_multiple_files(file_paths, remote_dir)
        
        # S3クライアントの呼び出し回数を確認
        assert storage_service._s3_client.upload_file.call_count == 3
        
        # 結果のURL数を確認
        assert len(results) == 3
        
        # URLの形式を確認
        for i, url in enumerate(results):
            expected_url = f"https://test-bucket.s3.ap-northeast-1.amazonaws.com/images/test_image_{i}.png"
            assert url == expected_url 