import os
import pytest
import base64
from unittest.mock import patch, mock_open, MagicMock

from core.file_manager import FileManager


class TestFileManager:
    """ファイル管理のテストクラス"""

    def test_create_directory_structure(self, temp_dir):
        """ディレクトリ構造作成のテスト"""
        file_manager = FileManager()
        structure = {
            "dir1": {
                "subdir1": {},
                "subdir2": {},
            },
            "dir2": {}
        }
        
        base_path = str(temp_dir)
        created_paths = file_manager.create_directory_structure(base_path, structure)
        
        assert os.path.exists(os.path.join(base_path, "dir1"))
        assert os.path.exists(os.path.join(base_path, "dir1", "subdir1"))
        assert os.path.exists(os.path.join(base_path, "dir1", "subdir2"))
        assert os.path.exists(os.path.join(base_path, "dir2"))
        
        # 作成されたパスのリストを検証
        assert len(created_paths) == 4  # 全体で4つのディレクトリ

    def test_write_content(self, temp_dir):
        """コンテンツ書き込みのテスト"""
        file_manager = FileManager()
        test_file = os.path.join(str(temp_dir), "test_file.txt")
        test_content = "テストコンテンツ"
        
        file_manager.write_content(test_file, test_content)
        
        assert os.path.exists(test_file)
        with open(test_file, 'r', encoding='utf-8') as f:
            assert f.read() == test_content

    def test_read_content(self, temp_dir):
        """コンテンツ読み込みのテスト"""
        file_manager = FileManager()
        test_file = os.path.join(str(temp_dir), "test_file.txt")
        test_content = "テストコンテンツ"
        
        # ファイル作成
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # 読み込みテスト
        content = file_manager.read_content(test_file)
        assert content == test_content

    @patch('builtins.open', new_callable=mock_open, read_data=b'test image data')
    def test_encode_images(self, mock_file):
        """画像エンコードのテスト"""
        file_manager = FileManager()
        
        # Base64エンコードのモック
        with patch('base64.b64encode') as mock_b64encode:
            mock_b64encode.return_value = b'encoded_image_data'
            
            content = """# テスト
            
            ![テスト画像](path/to/image.png)
            """
            
            result = file_manager.encode_images(content)
            
            # Base64エンコードが呼ばれたことを確認
            mock_b64encode.assert_called_once()
            
            # 画像参照が置換されたことを確認
            assert 'data:image/png;base64,encoded_image_data' in result

    def test_cache_content(self):
        """コンテンツキャッシュのテスト"""
        file_manager = FileManager()
        
        # キャッシュの保存
        key = "test_key"
        content = "テストコンテンツ"
        file_manager.cache_content(key, content)
        
        # キャッシュの取得
        cached = file_manager.get_cached_content(key)
        assert cached == content
        
        # 存在しないキーの取得
        with pytest.raises(KeyError):
            file_manager.get_cached_content("nonexistent_key")

    def test_clean_directory(self, temp_dir):
        """ディレクトリクリーンアップのテスト"""
        file_manager = FileManager()
        
        # テストディレクトリ構造の作成
        test_dir = os.path.join(str(temp_dir), "test_dir")
        os.makedirs(test_dir)
        test_file = os.path.join(test_dir, "test_file.txt")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # クリーンアップ実行
        file_manager.clean_directory(test_dir)
        
        # ディレクトリは存在するが、内容が空であることを確認
        assert os.path.exists(test_dir)
        assert len(os.listdir(test_dir)) == 0 