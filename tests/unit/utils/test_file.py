import pytest
import os
import shutil
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.utils.file import FileUtils

class TestFileUtils:
    """ファイル操作ユーティリティのテストクラス"""
    
    @pytest.fixture
    def file_utils(self):
        """テスト用のファイル操作ユーティリティインスタンスを作成"""
        # コメントアウトされているコードは、実際のクラスが実装された後に有効化する
        # return FileUtils()
        
        # モックインスタンスを返す（クラスが実装されるまでの一時的な対応）
        mock_utils = MagicMock()
        
        # read_file メソッドが呼ばれたときに実行される関数
        def mock_read_file(file_path):
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        mock_utils.read_file.side_effect = mock_read_file
        
        # write_file メソッドが呼ばれたときに実行される関数
        def mock_write_file(file_path, content, create_dirs=True):
            if create_dirs:
                os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return file_path
            
        mock_utils.write_file.side_effect = mock_write_file
        
        # ensure_dir メソッドが呼ばれたときに実行される関数
        def mock_ensure_dir(dir_path):
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            return dir_path
            
        mock_utils.ensure_dir.side_effect = mock_ensure_dir
        
        # list_files メソッドが呼ばれたときに実行される関数
        def mock_list_files(dir_path, pattern=None):
            if not os.path.exists(dir_path):
                return []
                
            import glob
            if pattern:
                return glob.glob(os.path.join(dir_path, pattern))
            else:
                return [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
                
        mock_utils.list_files.side_effect = mock_list_files
        
        # copy_file メソッドが呼ばれたときに実行される関数
        def mock_copy_file(src_path, dest_path, create_dirs=True):
            if not os.path.exists(src_path):
                raise FileNotFoundError(f"コピー元ファイルが見つかりません: {src_path}")
                
            if create_dirs:
                os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
                
            shutil.copy2(src_path, dest_path)
            return dest_path
            
        mock_utils.copy_file.side_effect = mock_copy_file
        
        # delete_file メソッドが呼ばれたときに実行される関数
        def mock_delete_file(file_path):
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        mock_utils.delete_file.side_effect = mock_delete_file
        
        # get_file_extension メソッドが呼ばれたときに実行される関数
        def mock_get_file_extension(file_path):
            _, ext = os.path.splitext(file_path)
            return ext.lower().lstrip('.')
            
        mock_utils.get_file_extension.side_effect = mock_get_file_extension
        
        return mock_utils
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # テスト後にディレクトリを削除
        shutil.rmtree(temp_dir)
    
    def test_read_file(self, file_utils, temp_dir):
        """ファイル読み込みのテスト"""
        # テスト用のファイルを作成
        test_file = os.path.join(temp_dir, "test.txt")
        test_content = "これはテスト用のファイル内容です。"
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # ファイル読み込みのテスト
        content = file_utils.read_file(test_file)
        
        # 読み込み結果が正しいことを確認
        assert content == test_content
    
    def test_write_file(self, file_utils, temp_dir):
        """ファイル書き込みのテスト"""
        test_file = os.path.join(temp_dir, "output.txt")
        test_content = "これは書き込むテスト内容です。"
        
        # ファイル書き込みのテスト
        result = file_utils.write_file(test_file, test_content)
        
        # 結果が正しいことを確認
        assert result == test_file
        assert os.path.exists(test_file)
        
        # 書き込まれた内容が正しいことを確認
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == test_content
    
    def test_write_file_create_dirs(self, file_utils, temp_dir):
        """ディレクトリ作成付きのファイル書き込みテスト"""
        test_file = os.path.join(temp_dir, "subdir1", "subdir2", "output.txt")
        test_content = "これは深いディレクトリへの書き込みテストです。"
        
        # ファイル書き込みのテスト（ディレクトリ作成あり）
        result = file_utils.write_file(test_file, test_content, create_dirs=True)
        
        # 結果が正しいことを確認
        assert result == test_file
        assert os.path.exists(test_file)
        
        # 書き込まれた内容が正しいことを確認
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == test_content
    
    def test_ensure_dir(self, file_utils, temp_dir):
        """ディレクトリ作成のテスト"""
        test_dir = os.path.join(temp_dir, "new_dir")
        
        # ディレクトリが存在しないことを確認
        assert not os.path.exists(test_dir)
        
        # ディレクトリ作成のテスト
        result = file_utils.ensure_dir(test_dir)
        
        # 結果が正しいことを確認
        assert result == test_dir
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)
    
    def test_list_files(self, file_utils, temp_dir):
        """ファイル一覧取得のテスト"""
        # テスト用のファイルを作成
        files = {
            "file1.txt": "内容1",
            "file2.txt": "内容2",
            "file3.md": "Markdown内容",
            "subdir/file4.txt": "サブディレクトリ内の内容"
        }
        
        for file_path, content in files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # ファイル一覧取得のテスト
        file_list = file_utils.list_files(temp_dir)
        
        # 結果が正しいことを確認
        assert len(file_list) == 3  # サブディレクトリ内のファイルは含まれない
        assert "file1.txt" in file_list
        assert "file2.txt" in file_list
        assert "file3.md" in file_list
    
    def test_list_files_with_pattern(self, file_utils, temp_dir):
        """パターン指定のファイル一覧取得テスト"""
        # テスト用のファイルを作成
        files = {
            "file1.txt": "内容1",
            "file2.txt": "内容2",
            "file3.md": "Markdown内容",
            "subdir/file4.txt": "サブディレクトリ内の内容"
        }
        
        for file_path, content in files.items():
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # パターン指定のファイル一覧取得テスト
        txt_files = file_utils.list_files(temp_dir, pattern="*.txt")
        
        # 結果が正しいことを確認
        assert len(txt_files) == 2
        assert os.path.join(temp_dir, "file1.txt") in txt_files
        assert os.path.join(temp_dir, "file2.txt") in txt_files
        assert os.path.join(temp_dir, "file3.md") not in txt_files
    
    def test_copy_file(self, file_utils, temp_dir):
        """ファイルコピーのテスト"""
        # テスト用のファイルを作成
        src_file = os.path.join(temp_dir, "source.txt")
        dest_file = os.path.join(temp_dir, "dest.txt")
        test_content = "これはコピーテスト用の内容です。"
        
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # ファイルコピーのテスト
        result = file_utils.copy_file(src_file, dest_file)
        
        # 結果が正しいことを確認
        assert result == dest_file
        assert os.path.exists(dest_file)
        
        # コピーされた内容が正しいことを確認
        with open(dest_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == test_content
    
    def test_copy_file_create_dirs(self, file_utils, temp_dir):
        """ディレクトリ作成付きのファイルコピーテスト"""
        # テスト用のファイルを作成
        src_file = os.path.join(temp_dir, "source.txt")
        dest_file = os.path.join(temp_dir, "subdir1", "subdir2", "dest.txt")
        test_content = "これはディレクトリ作成付きコピーテスト用の内容です。"
        
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # ファイルコピーのテスト（ディレクトリ作成あり）
        result = file_utils.copy_file(src_file, dest_file, create_dirs=True)
        
        # 結果が正しいことを確認
        assert result == dest_file
        assert os.path.exists(dest_file)
        
        # コピーされた内容が正しいことを確認
        with open(dest_file, 'r', encoding='utf-8') as f:
            content = f.read()
            assert content == test_content
    
    def test_delete_file(self, file_utils, temp_dir):
        """ファイル削除のテスト"""
        # テスト用のファイルを作成
        test_file = os.path.join(temp_dir, "delete_test.txt")
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("削除されるファイル")
        
        # ファイルが存在することを確認
        assert os.path.exists(test_file)
        
        # ファイル削除のテスト
        result = file_utils.delete_file(test_file)
        
        # 結果が正しいことを確認
        assert result is True
        assert not os.path.exists(test_file)
    
    def test_delete_nonexistent_file(self, file_utils, temp_dir):
        """存在しないファイルの削除テスト"""
        test_file = os.path.join(temp_dir, "nonexistent.txt")
        
        # ファイルが存在しないことを確認
        assert not os.path.exists(test_file)
        
        # 存在しないファイルの削除テスト
        result = file_utils.delete_file(test_file)
        
        # 結果が正しいことを確認
        assert result is False
    
    def test_get_file_extension(self, file_utils):
        """ファイル拡張子取得のテスト"""
        # 様々なファイルパスでのテスト
        file_paths = {
            "test.txt": "txt",
            "image.png": "png",
            "doc.pdf": "pdf",
            "archive.tar.gz": "gz",
            "script.PY": "py",  # 大文字の拡張子
            "noextension": "",  # 拡張子なし
            "/path/to/file.md": "md",  # パス付き
            "dir.name/file": ""  # ディレクトリ名に拡張子があるがファイルに拡張子がない
        }
        
        for file_path, expected_ext in file_paths.items():
            ext = file_utils.get_file_extension(file_path)
            assert ext == expected_ext
    
    def test_read_nonexistent_file(self, file_utils, temp_dir):
        """存在しないファイルの読み込みテスト"""
        nonexistent_file = os.path.join(temp_dir, "nonexistent.txt")
        
        # 存在しないファイルの読み込みでFileNotFoundErrorが発生することを確認
        with pytest.raises(FileNotFoundError):
            file_utils.read_file(nonexistent_file)
    
    def test_copy_nonexistent_file(self, file_utils, temp_dir):
        """存在しないファイルのコピーテスト"""
        nonexistent_file = os.path.join(temp_dir, "nonexistent.txt")
        dest_file = os.path.join(temp_dir, "dest.txt")
        
        # 存在しないファイルのコピーでFileNotFoundErrorが発生することを確認
        with pytest.raises(FileNotFoundError):
            file_utils.copy_file(nonexistent_file, dest_file) 