"""
ファイル操作を抽象化するモジュール。
ディレクトリ作成、ファイル読み書き、画像エンコード、キャッシュ機能などの機能を提供する。
"""
import os
import re
import base64
import shutil
from typing import Dict, List, Any, Optional, Union


class FileManager:
    """
    ファイルやディレクトリの操作を抽象化するクラス。
    Facade パターンを使用して、複雑なファイル操作を簡略化する。
    """

    def __init__(self):
        """
        FileManagerを初期化する。
        キャッシュ用の辞書を初期化。
        """
        self._cache = {}  # キャッシュ用の辞書

    def create_directory_structure(self, base_path: str, structure: Dict[str, Any]) -> List[str]:
        """
        ディレクトリ構造を再帰的に作成する

        Args:
            base_path (str): 基準となるディレクトリパス
            structure (dict): 作成するディレクトリ構造 (ネストした辞書)

        Returns:
            list: 作成したディレクトリのパスのリスト
        """
        created_paths = []
        
        # ベースディレクトリがなければ作成
        if not os.path.exists(base_path):
            os.makedirs(base_path)
            created_paths.append(base_path)
        
        # 再帰的にディレクトリ構造を作成
        for name, sub_structure in structure.items():
            path = os.path.join(base_path, name)
            
            # ディレクトリ作成
            if not os.path.exists(path):
                os.makedirs(path)
                created_paths.append(path)
            
            # サブディレクトリがあれば再帰的に処理
            if isinstance(sub_structure, dict):
                sub_paths = self.create_directory_structure(path, sub_structure)
                created_paths.extend(sub_paths)
        
        return created_paths

    def write_content(self, path: str, content: str) -> None:
        """
        ファイルにコンテンツを書き込む。
        必要に応じてディレクトリも作成する。

        Args:
            path (str): 書き込み先のファイルパス
            content (str): 書き込むコンテンツ
        """
        # ディレクトリがなければ作成
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # ファイルに書き込み
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_content(self, path: str) -> str:
        """
        ファイルからコンテンツを読み込む

        Args:
            path (str): 読み込むファイルのパス

        Returns:
            str: ファイルの内容

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def encode_images(self, content: str) -> str:
        """
        Markdown内の画像参照をBase64エンコードに置き換える

        Args:
            content (str): 処理するコンテンツ

        Returns:
            str: 画像参照がBase64エンコードに置き換えられたコンテンツ
        """
        # 画像参照パターン: ![alt text](path/to/image.png)
        image_pattern = r'!\[(.*?)\]\((.*?)\)'
        
        def encode_image_match(match):
            alt_text = match.group(1)
            image_path = match.group(2)
            
            # 画像ファイルの存在確認
            if not os.path.exists(image_path):
                # 相対パスの場合は現在のディレクトリからの相対パスを試す
                if not os.path.isabs(image_path):
                    # 現在のディレクトリからの相対パスを試す
                    for root_dir in [".", ".."]:
                        full_path = os.path.join(root_dir, image_path)
                        if os.path.exists(full_path):
                            image_path = full_path
                            break
                    else:
                        # 画像が見つからない場合は元の参照を保持
                        return match.group(0)
            
            try:
                # 画像ファイルの読み込みとエンコード
                with open(image_path, 'rb') as f:
                    image_data = f.read()
                
                # MIMEタイプの推定
                mime_type = self._get_mime_type(image_path)
                
                # Base64エンコード
                encoded_data = base64.b64encode(image_data).decode('utf-8')
                data_url = f"data:{mime_type};base64,{encoded_data}"
                
                # 新しい画像参照を作成
                return f"![{alt_text}]({data_url})"
            except Exception:
                # エラーが発生した場合は元の参照を保持
                return match.group(0)
        
        # 画像参照を置換
        return re.sub(image_pattern, encode_image_match, content)

    def _get_mime_type(self, file_path: str) -> str:
        """
        ファイル拡張子からMIMEタイプを推定する

        Args:
            file_path (str): ファイルパス

        Returns:
            str: MIMEタイプ
        """
        extension = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.webp': 'image/webp'
        }
        return mime_types.get(extension, 'application/octet-stream')

    def cache_content(self, key: str, content: Any) -> None:
        """
        キーを使ってコンテンツをキャッシュする

        Args:
            key (str): キャッシュのキー
            content (Any): キャッシュするコンテンツ
        """
        self._cache[key] = content

    def get_cached_content(self, key: str) -> Any:
        """
        キャッシュからコンテンツを取得する

        Args:
            key (str): キャッシュのキー

        Returns:
            Any: キャッシュされたコンテンツ

        Raises:
            KeyError: キャッシュにキーが存在しない場合
        """
        if key not in self._cache:
            raise KeyError(f"キャッシュに '{key}' が存在しません")
        return self._cache[key]

    def clean_directory(self, directory_path: str) -> None:
        """
        ディレクトリの内容を削除する (ディレクトリ自体は残す)

        Args:
            directory_path (str): クリーンアップするディレクトリのパス
        """
        if not os.path.exists(directory_path):
            return
        
        # ディレクトリ内のすべてのファイルとディレクトリを削除
        for item in os.listdir(directory_path):
            item_path = os.path.join(directory_path, item)
            if os.path.isfile(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path) 