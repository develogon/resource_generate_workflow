"""
記事生成を担当するモジュール。
Claude APIを使用して記事の生成を行う。
コンテンツが長い場合は適切に分割・結合する機能を提供する。
"""
import re
import math
from typing import Dict, Any, List, Optional, Union

from core.content_generator import ContentGenerator


class ArticleGenerator(ContentGenerator):
    """
    記事生成を担当するクラス。
    ContentGeneratorを継承し、記事特有の処理を実装する。
    """
    
    def __init__(self, claude_service: Any, file_manager: Any, template_dir: str = "templates"):
        """
        ArticleGeneratorを初期化する。
        
        Args:
            claude_service (Any): Claude APIサービス
            file_manager (Any): ファイル管理サービス
            template_dir (str, optional): テンプレートディレクトリのパス
        """
        super().__init__(claude_service, file_manager, template_dir)
        self.max_chunk_tokens = 8000  # APIリクエストあたりの最大トークン（文字）数
        self.max_prompt_tokens = 4000  # プロンプトの最大トークン（文字）数
        
    def generate(self, input_data: Dict[str, Any]) -> str:
        """
        記事を生成する。
        長い原稿は適切に分割・結合する。
        
        Args:
            input_data (dict): 生成に必要な入力データ
                - section_title: セクションタイトル
                - content: 原稿内容
                - template_path: テンプレートファイルのパス
                - images: (optional) プロンプトに含める画像データのリスト
                - language: (optional) 対象言語
                - system_prompt: (optional) システムプロンプト
        
        Returns:
            str: 生成された記事
        """
        # 入力データの取得
        content = input_data.get("content", "")
        
        # コンテンツサイズに基づいて処理方法を決定
        content_length = len(content)
        
        # コンテンツが長い場合は分割処理
        if content_length > self.max_prompt_tokens:
            # コンテンツを分割
            chunks = self._split_content(content)
            
            # 各チャンクを処理
            chunk_responses = []
            for i, chunk in enumerate(chunks):
                # チャンク用のデータ作成
                chunk_data = input_data.copy()
                chunk_data["content"] = chunk
                chunk_data["chunk_index"] = i
                chunk_data["total_chunks"] = len(chunks)
                
                # システムプロンプトを各チャンクに伝播
                # 既に入力データにsystem_promptが存在する場合はそのまま継承される
                
                # 通常の生成処理でチャンクを処理
                chunk_response = super().generate(chunk_data)
                chunk_responses.append(chunk_response)
            
            # チャンク応答を結合
            combined_content = self._combine_chunks(chunk_responses)
            return combined_content
        
        # 通常のケース（コンテンツが短い場合）
        return super().generate(input_data)
    
    def format_output(self, raw_content: str) -> str:
        """
        記事出力を整形する。
        
        Args:
            raw_content (str): 生成された生の記事内容
        
        Returns:
            str: 整形された記事
        """
        # 余分な空行を圧縮
        content = re.sub(r'\n{3,}', '\n\n', raw_content.strip())
        
        # Markdown形式の整形
        # リストアイテムの後の空行を確保
        content = re.sub(r'(\n- .+?)(\n)(?![\s\n-])', r'\1\n\n', content)
        
        # 見出しの前後に空行を確保
        content = re.sub(r'([^\n])\n(#+\s)', r'\1\n\n\2', content)
        content = re.sub(r'(#+\s.*?)\n([^#\n])', r'\1\n\n\2', content)
        
        return content
    
    def validate_content(self, content: str) -> bool:
        """
        生成された記事コンテンツを検証する。
        
        Args:
            content (str): 検証する記事コンテンツ
        
        Returns:
            bool: コンテンツが有効な場合はTrue、そうでない場合はFalse
        """
        if not content or not content.strip():
            return False
        
        # コンテンツの行を取得して、インデントを削除
        lines = [line.strip() for line in content.split('\n')]
        
        # 見出しが含まれているか確認
        for line in lines:
            if re.match(r'^#+\s+\S+', line):
                return True
        
        return False
    
    def _split_content(self, content: str, max_chunk_size: int = None) -> List[str]:
        """
        長いコンテンツを複数のチャンクに分割する。
        
        Args:
            content (str): 分割する原稿コンテンツ
            max_chunk_size (int, optional): チャンクの最大サイズ
        
        Returns:
            List[str]: 分割されたチャンクのリスト
        """
        if max_chunk_size is None:
            max_chunk_size = self.max_prompt_tokens
        
        # 段落で分割
        paragraphs = re.split(r'\n\s*\n', content)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for paragraph in paragraphs:
            paragraph_size = len(paragraph)
            
            # 現在のチャンクに段落を追加できる場合
            if current_size + paragraph_size <= max_chunk_size:
                current_chunk.append(paragraph)
                current_size += paragraph_size
            else:
                # 現在のチャンクが存在する場合は保存
                if current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                
                # 段落が単体でチャンクサイズを超える場合は分割
                if paragraph_size > max_chunk_size:
                    # 文で分割
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    
                    sub_chunk = []
                    sub_size = 0
                    
                    for sentence in sentences:
                        sentence_size = len(sentence)
                        
                        if sub_size + sentence_size <= max_chunk_size:
                            sub_chunk.append(sentence)
                            sub_size += sentence_size
                        else:
                            # 現在のサブチャンクを保存
                            if sub_chunk:
                                chunks.append(" ".join(sub_chunk))
                            
                            # 新しいサブチャンクを開始
                            if sentence_size > max_chunk_size:
                                # 文が長すぎる場合は文字単位で分割
                                for i in range(0, len(sentence), max_chunk_size):
                                    chunks.append(sentence[i:i+max_chunk_size])
                            else:
                                sub_chunk = [sentence]
                                sub_size = sentence_size
                    
                    # 残りのサブチャンクを保存
                    if sub_chunk:
                        chunks.append(" ".join(sub_chunk))
                else:
                    # 新しいチャンクを開始
                    current_chunk = [paragraph]
                    current_size = paragraph_size
        
        # 残りのチャンクを保存
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
        
        return chunks
    
    def _combine_chunks(self, chunk_responses: List[str]) -> str:
        """
        チャンク応答を結合して完全な記事を作成する。
        
        Args:
            chunk_responses (List[str]): チャンクの応答リスト
        
        Returns:
            str: 結合された記事
        """
        # 最初のチャンクの応答をベースにする
        if not chunk_responses:
            return ""
        
        combined = chunk_responses[0]
        
        # 2つ目以降のチャンクを処理
        for i in range(1, len(chunk_responses)):
            chunk = chunk_responses[i]
            
            # 各チャンクの冒頭の見出しを削除
            # 例: # タイトル や ## サブタイトル のような行を削除
            lines = chunk.split('\n')
            start_index = 0
            
            for j, line in enumerate(lines):
                if re.match(r'^#+\s+\S+', line):
                    start_index = j + 1
                    break
            
            # 見出し行を削除したチャンクを追加
            chunk_content = '\n'.join(lines[start_index:])
            combined += '\n\n' + chunk_content
        
        return combined 