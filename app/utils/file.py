import os
import shutil
import glob


class FileUtils:
    """ファイル操作ユーティリティクラス

    ファイルの読み書きや操作を行うユーティリティクラスです。
    """

    @staticmethod
    def read_file(file_path):
        """ファイルを読み込む

        Args:
            file_path (str): 読み込むファイルのパス

        Returns:
            str: ファイルの内容

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @staticmethod
    def write_file(file_path, content, create_dirs=True):
        """ファイルに内容を書き込む

        Args:
            file_path (str): 書き込み先のファイルパス
            content (str): 書き込む内容
            create_dirs (bool, optional): ディレクトリがない場合に作成するか. デフォルトはTrue

        Returns:
            str: 書き込んだファイルのパス
        """
        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return file_path

    @staticmethod
    def ensure_dir(dir_path):
        """ディレクトリが存在することを確認し、なければ作成する

        Args:
            dir_path (str): 作成するディレクトリのパス

        Returns:
            str: 作成/確認したディレクトリのパス
        """
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        return dir_path

    @staticmethod
    def list_files(dir_path, pattern=None):
        """ディレクトリ内のファイル一覧を取得する

        Args:
            dir_path (str): 対象ディレクトリのパス
            pattern (str, optional): ファイル名パターン（glob形式）. デフォルトはNone

        Returns:
            list: ファイルパスのリスト
        """
        if not os.path.exists(dir_path):
            return []

        if pattern:
            return glob.glob(os.path.join(dir_path, pattern))
        else:
            return [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

    @staticmethod
    def copy_file(src_path, dest_path, create_dirs=True):
        """ファイルをコピーする

        Args:
            src_path (str): コピー元ファイルのパス
            dest_path (str): コピー先のパス
            create_dirs (bool, optional): ディレクトリがない場合に作成するか. デフォルトはTrue

        Returns:
            str: コピー先ファイルのパス

        Raises:
            FileNotFoundError: コピー元ファイルが存在しない場合
        """
        if not os.path.exists(src_path):
            raise FileNotFoundError(f"コピー元ファイルが見つかりません: {src_path}")

        if create_dirs:
            os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)

        shutil.copy2(src_path, dest_path)
        return dest_path

    @staticmethod
    def delete_file(file_path):
        """ファイルを削除する

        Args:
            file_path (str): 削除するファイルのパス

        Returns:
            bool: 削除に成功した場合はTrue、ファイルが存在しない場合はFalse
        """
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    @staticmethod
    def get_file_extension(file_path):
        """ファイルの拡張子を取得する

        Args:
            file_path (str): ファイルパス

        Returns:
            str: 拡張子（ドットなし、小文字）
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower().lstrip('.') 