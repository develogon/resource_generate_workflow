import logging
from typing import List, Dict, Any, Optional

class ContentProcessor:
    """コンテンツ処理システム"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
    
    def split_chapters(self, content: str) -> List[Dict[str, str]]:
        """コンテンツをチャプターに分割
        
        Args:
            content (str): 分割するMarkdownコンテンツ
            
        Returns:
            List[Dict[str, str]]: チャプター情報のリスト
            各チャプターは {"title": "チャプタータイトル", "content": "チャプター内容"} の形式
        """
        chapters = []
        lines = content.split("\n")
        current_chapter = None
        chapter_content = []
        
        for line in lines:
            if line.startswith("## "):
                if current_chapter:
                    chapters.append({
                        "title": current_chapter,
                        "content": "\n".join(chapter_content)
                    })
                current_chapter = line[3:].strip()
                chapter_content = [line]
            elif current_chapter:
                chapter_content.append(line)
        
        if current_chapter:
            chapters.append({
                "title": current_chapter,
                "content": "\n".join(chapter_content)
            })
        
        self.logger.debug(f"{len(chapters)}個のチャプターに分割しました")
        return chapters
    
    def split_sections(self, chapter_content: str) -> List[Dict[str, str]]:
        """チャプターコンテンツをセクションに分割
        
        Args:
            chapter_content (str): 分割するチャプターのMarkdownコンテンツ
            
        Returns:
            List[Dict[str, str]]: セクション情報のリスト
            各セクションは {"title": "セクションタイトル", "content": "セクション内容"} の形式
        """
        sections = []
        lines = chapter_content.split("\n")
        current_section = None
        section_content = []
        
        for line in lines:
            if line.startswith("### "):
                if current_section:
                    sections.append({
                        "title": current_section,
                        "content": "\n".join(section_content)
                    })
                current_section = line[4:].strip()
                section_content = [line]
            elif current_section:
                section_content.append(line)
        
        if current_section:
            sections.append({
                "title": current_section,
                "content": "\n".join(section_content)
            })
        
        self.logger.debug(f"{len(sections)}個のセクションに分割しました")
        return sections
    
    def analyze_structure(self, section_content: str, images: List[Dict] = None) -> Dict:
        """セクションの構造を解析
        
        Args:
            section_content (str): 解析するセクションのMarkdownコンテンツ
            images (List[Dict], optional): 画像情報のリスト
            
        Returns:
            Dict: セクション構造情報
        """
        # 簡易的な実装（将来的にはClaudeAPIを使った詳細な解析を行う予定）
        lines = section_content.split("\n")
        title = ""
        paragraphs = []
        
        current_paragraph = []
        
        for line in lines:
            if line.startswith("### "):
                title = line[4:].strip()
            elif not line.strip():
                if current_paragraph:
                    paragraphs.append("\n".join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            paragraphs.append("\n".join(current_paragraph))
        
        structure = {
            "title": title,
            "paragraphs": paragraphs
        }
        
        if images:
            structure["images"] = images
        
        return structure
    
    def extract_metadata(self, content: str) -> Dict[str, str]:
        """コンテンツからメタデータを抽出
        
        Args:
            content (str): 解析するMarkdownコンテンツ
            
        Returns:
            Dict[str, str]: メタデータ情報
        """
        metadata = {}
        lines = content.split("\n")
        
        # タイトルを抽出（最初の # で始まる行）
        for line in lines:
            if line.startswith("# "):
                metadata["title"] = line[2:].strip()
                break
        
        return metadata
    
    def combine_contents(self, contents: List[str], content_type: str) -> str:
        """複数のコンテンツを結合
        
        Args:
            contents (List[str]): 結合するコンテンツのリスト
            content_type (str): コンテンツタイプ（"article", "script"など）
            
        Returns:
            str: 結合されたコンテンツ
        """
        combined = "\n\n".join(contents)
        self.logger.debug(f"{len(contents)}個の{content_type}を結合しました")
        return combined 