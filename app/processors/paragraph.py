import logging
import re
import json
from typing import List, Dict, Any, Optional

class ParagraphProcessor:
    """パラグラフ処理システム"""
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
    
    def extract_paragraphs(self, section_content: str, structure: Dict) -> List[Dict]:
        """セクション構造からパラグラフ情報を抽出
        
        Args:
            section_content (str): セクションのMarkdownコンテンツ
            structure (Dict): セクション構造情報
            
        Returns:
            List[Dict]: パラグラフ情報のリスト
        """
        paragraphs = []
        
        if not structure or "paragraphs" not in structure:
            self.logger.warning("有効な構造データが提供されていません")
            return paragraphs
            
        for i, p in enumerate(structure["paragraphs"]):
            paragraph = {
                "id": f"p{i+1}",
                "type": p.get("type", "text"),
                "content": p.get("content", "")
            }
            
            # リスト型の場合は項目も追加
            if paragraph["type"] == "list" and "items" in p:
                paragraph["items"] = p["items"]
            
            paragraphs.append(paragraph)
        
        self.logger.debug(f"{len(paragraphs)}個のパラグラフを抽出しました")
        return paragraphs
    
    def process_paragraph(self, paragraph: Dict, context: Optional[Dict] = None) -> Dict:
        """パラグラフを処理し、付加情報を追加
        
        Args:
            paragraph (Dict): 処理するパラグラフ情報
            context (Dict, optional): 追加コンテキスト情報
            
        Returns:
            Dict: 処理済みパラグラフ情報
        """
        # デフォルト値の設定
        paragraph_id = paragraph.get("id", f"p{id(paragraph)}")
        content = paragraph.get("content", "")
        paragraph_type = paragraph.get("type", "text")
        
        # メタデータの準備
        metadata = {
            "type": paragraph_type,
            "word_count": len(content.split()),
            "has_code": "```" in content,
            "has_list": paragraph_type == "list"
        }
        
        # リスト型の処理
        if paragraph_type == "list" and "items" in paragraph:
            items = paragraph["items"]
            list_content = "\n".join([f"- {item}" for item in items])
            content = list_content
            metadata["list_item_count"] = len(items)
        
        # コード型のフォーマット確認
        if paragraph_type == "code" and "```" in content:
            # コードブロックの言語を抽出
            match = re.search(r'```(\w+)', content)
            if match:
                metadata["code_language"] = match.group(1)
        
        # コンテキスト情報があれば追加
        if context:
            metadata.update({"context": context})
        
        processed = {
            "id": paragraph_id,
            "processed_content": content,
            "metadata": metadata
        }
        
        self.logger.debug(f"パラグラフ {paragraph_id} を処理しました")
        return processed
    
    def combine_processed_paragraphs(self, processed_paragraphs: List[Dict], format_type: str = "markdown") -> Any:
        """処理済みパラグラフを指定のフォーマットで結合
        
        Args:
            processed_paragraphs (List[Dict]): 処理済みパラグラフのリスト
            format_type (str): 出力フォーマット（"markdown"または"json"）
            
        Returns:
            Any: 結合されたコンテンツ（フォーマットによって型が異なる）
        """
        if not processed_paragraphs:
            self.logger.warning("結合するパラグラフがありません")
            return "" if format_type == "markdown" else {}
        
        if format_type == "markdown":
            combined = "\n\n".join([p.get("processed_content", "") for p in processed_paragraphs])
            self.logger.debug(f"{len(processed_paragraphs)}個のパラグラフをMarkdown形式で結合しました")
            return combined
            
        elif format_type == "json":
            combined = {
                "paragraphs": [
                    {
                        "id": p.get("id", "unknown"),
                        "content": p.get("processed_content", ""),
                        "metadata": p.get("metadata", {})
                    } for p in processed_paragraphs
                ]
            }
            self.logger.debug(f"{len(processed_paragraphs)}個のパラグラフをJSON形式で結合しました")
            return combined
            
        else:
            self.logger.error(f"無効なフォーマット形式が指定されました: {format_type}")
            return "" 