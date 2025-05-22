import os
import logging
import re
import yaml
from typing import List, Dict, Any, Optional

class SectionProcessor:
    """セクション処理システム"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
    
    def create_section_folder(self, chapter_dir: str, section_title: str) -> str:
        """セクションフォルダを作成
        
        Args:
            chapter_dir (str): 親チャプターのディレクトリパス
            section_title (str): セクションタイトル
            
        Returns:
            str: 作成されたセクションディレクトリのパス
        """
        section_name = self.sanitize_filename(section_title)
        section_dir = os.path.join(chapter_dir, section_name)
        
        os.makedirs(section_dir, exist_ok=True)
        self.logger.debug(f"セクションディレクトリを作成: {section_dir}")
        
        return section_dir
    
    def write_section_content(self, section_dir: str, content: str) -> str:
        """セクションコンテンツをファイルに書き込む
        
        Args:
            section_dir (str): セクションディレクトリのパス
            content (str): 書き込むセクションコンテンツ
            
        Returns:
            str: 作成されたファイルのパス
        """
        section_file = os.path.join(section_dir, "text.md")
        
        with open(section_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        self.logger.debug(f"セクションコンテンツを書き込み: {section_file}")
        return section_file
    
    def write_section_structure(self, section_dir: str, structure: Dict) -> str:
        """セクション構造情報をYAMLファイルに書き込む
        
        Args:
            section_dir (str): セクションディレクトリのパス
            structure (Dict): 書き込む構造情報
            
        Returns:
            str: 作成されたファイルのパス
        """
        structure_file = os.path.join(section_dir, "section_structure.yaml")
        
        with open(structure_file, "w", encoding="utf-8") as f:
            yaml.dump(structure, f, default_flow_style=False, allow_unicode=True)
        
        self.logger.debug(f"セクション構造を書き込み: {structure_file}")
        return structure_file
    
    def extract_section_title(self, section_content: str) -> str:
        """セクションコンテンツからタイトルを抽出
        
        Args:
            section_content (str): セクションのMarkdownコンテンツ
            
        Returns:
            str: 抽出されたセクションタイトル
        """
        lines = section_content.split("\n")
        
        for line in lines:
            if line.startswith("### "):
                return line[4:].strip()
        
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
        # "2.2 (応用)" → "2_2_応用"
        bracket_pattern = re.compile(r'\s*\(([^)]+)\)')
        match = bracket_pattern.search(sanitized)
        if match:
            bracket_content = match.group(1)
            sanitized = bracket_pattern.sub(f"_{bracket_content}", sanitized)
        
        # その他の特殊文字を置換
        sanitized = sanitized.replace("/", "_").replace("\\", "_")
        sanitized = sanitized.replace(".", "_")
        
        # スペースをアンダースコアに変換
        sanitized = sanitized.replace(" ", "_")
        
        # 連続した特殊文字をアンダースコア一つに
        sanitized = re.sub(r'[^\w\-\.]', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # 末尾のアンダースコアを削除
        sanitized = sanitized.rstrip('_')
        
        return sanitized
    
    def combine_section_contents(self, section_dir: str, content_type: str) -> str:
        """セクションディレクトリ内の各パラグラフコンテンツを結合
        
        Args:
            section_dir (str): セクションディレクトリのパス
            content_type (str): 結合するコンテンツタイプ（"article.md", "script.md"など）
            
        Returns:
            str: 結合されたコンテンツ
        """
        combined_content = ""
        combined_file_path = os.path.join(section_dir, content_type)
        
        # パラグラフディレクトリを取得（アルファベット順でソート）
        paragraph_dirs = [d for d in os.listdir(section_dir) 
                           if os.path.isdir(os.path.join(section_dir, d)) and d != "images"]
        paragraph_dirs.sort()
        
        contents = []
        for paragraph_dir in paragraph_dirs:
            paragraph_file = os.path.join(section_dir, paragraph_dir, content_type)
            if os.path.exists(paragraph_file):
                with open(paragraph_file, "r", encoding="utf-8") as f:
                    paragraph_content = f.read()
                    contents.append(paragraph_content)
        
        if contents:
            combined_content = "\n\n".join(contents)
            
            # 結合したコンテンツをファイルに書き込み
            with open(combined_file_path, "w", encoding="utf-8") as f:
                f.write(combined_content)
            
            self.logger.debug(f"パラグラフの{content_type}を結合: {combined_file_path}")
        
        return combined_content 