import os
import logging
import re
from typing import List, Dict, Any, Optional

class ChapterProcessor:
    """チャプター処理システム"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
    
    def create_chapter_folder(self, base_dir: str, chapter_title: str) -> str:
        """チャプターフォルダを作成
        
        Args:
            base_dir (str): ベースディレクトリ
            chapter_title (str): チャプタータイトル
            
        Returns:
            str: 作成されたチャプターディレクトリのパス
        """
        chapter_name = self.sanitize_filename(chapter_title)
        chapter_dir = os.path.join(base_dir, chapter_name)
        
        os.makedirs(chapter_dir, exist_ok=True)
        self.logger.debug(f"チャプターディレクトリを作成: {chapter_dir}")
        
        return chapter_dir
    
    def write_chapter_content(self, chapter_dir: str, content: str) -> str:
        """チャプターコンテンツをファイルに書き込む
        
        Args:
            chapter_dir (str): チャプターディレクトリのパス
            content (str): 書き込むチャプターコンテンツ
            
        Returns:
            str: 作成されたファイルのパス
        """
        chapter_file = os.path.join(chapter_dir, "text.md")
        
        with open(chapter_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.logger.debug(f"チャプターコンテンツを書き込み: {chapter_file}")
        return chapter_file
    
    def combine_chapter_contents(self, chapter_dir: str, content_type: str) -> str:
        """チャプターディレクトリ内の各セクションコンテンツを結合
        
        Args:
            chapter_dir (str): チャプターディレクトリのパス
            content_type (str): 結合するコンテンツタイプ（"article.md", "script.md"など）
            
        Returns:
            str: 結合されたコンテンツ
        """
        combined_content = ""
        combined_file_path = os.path.join(chapter_dir, content_type)
        
        # セクションディレクトリを取得（アルファベット順でソート）
        section_dirs = [d for d in os.listdir(chapter_dir) 
                         if os.path.isdir(os.path.join(chapter_dir, d)) and d != "images"]
        section_dirs.sort()
        
        contents = []
        for section_dir in section_dirs:
            section_file = os.path.join(chapter_dir, section_dir, content_type)
            if os.path.exists(section_file):
                with open(section_file, "r", encoding="utf-8") as f:
                    section_content = f.read()
                    contents.append(section_content)
        
        if contents:
            combined_content = "\n\n".join(contents)
            
            # 結合したコンテンツをファイルに書き込み
            with open(combined_file_path, "w", encoding="utf-8") as f:
                f.write(combined_content)
            
            self.logger.debug(f"セクションの{content_type}を結合: {combined_file_path}")
        
        return combined_content
    
    def extract_chapter_title(self, chapter_content: str) -> str:
        """チャプターコンテンツからタイトルを抽出
        
        Args:
            chapter_content (str): チャプターのMarkdownコンテンツ
            
        Returns:
            str: 抽出されたチャプタータイトル
        """
        lines = chapter_content.split("\n")
        
        for line in lines:
            if line.startswith("## "):
                return line[3:].strip()
        
        return ""
    
    def sanitize_filename(self, title: str) -> str:
        """タイトルをファイル名に適した形式に変換
        
        Args:
            title (str): 元のタイトル
            
        Returns:
            str: サニタイズされたファイル名
        """
        # 特定のパターンを置換
        sanitized = title.replace(": ", "_").replace("：", "_")
        sanitized = sanitized.replace(" - ", "_")
        
        # 括弧内のテキストを抽出して処理
        # "第4章 (補足)" → "第4章_補足"
        bracket_pattern = re.compile(r'\s*\(([^)]+)\)')
        match = bracket_pattern.search(sanitized)
        if match:
            bracket_content = match.group(1)
            sanitized = bracket_pattern.sub(f"_{bracket_content}", sanitized)
        
        # その他の特殊文字を置換
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        
        # スペースをアンダースコアに変換
        sanitized = sanitized.replace(" ", "_")
        
        # 連続した特殊文字をアンダースコア一つに
        sanitized = re.sub(r'[^\w\-\.]', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 末尾のアンダースコアを削除
        sanitized = sanitized.rstrip('_')
        
        return sanitized 