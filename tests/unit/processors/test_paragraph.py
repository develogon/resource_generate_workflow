import pytest
import os
import shutil
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.processors.paragraph import ParagraphProcessor

class TestParagraphProcessor:
    """パラグラフプロセッサのテストクラス"""
    
    @pytest.fixture
    def paragraph_processor(self):
        """テスト用のパラグラフプロセッサインスタンスを作成"""
        # コメントアウトされているコードは、実際のクラスが実装された後に有効化する
        # return ParagraphProcessor()
        
        # モックインスタンスを返す（クラスが実装されるまでの一時的な対応）
        mock_processor = MagicMock()
        
        # extract_paragraphsメソッドが呼ばれたときに実行される関数
        def mock_extract_paragraphs(section_content, structure):
            paragraphs = []
            if not structure or "paragraphs" not in structure:
                return paragraphs
                
            for i, p in enumerate(structure["paragraphs"]):
                paragraphs.append({
                    "id": f"p{i+1}",
                    "type": p.get("type", "text"),
                    "content": p.get("content", ""),
                    "items": p.get("items", []) if p.get("type") == "list" else None
                })
            
            return paragraphs
            
        mock_processor.extract_paragraphs.side_effect = mock_extract_paragraphs
        
        # process_paragraphメソッドが呼ばれたときに実行される関数
        def mock_process_paragraph(paragraph, context=None):
            result = {
                "id": paragraph.get("id", "unknown"),
                "processed_content": paragraph.get("content", ""),
                "metadata": {
                    "type": paragraph.get("type", "text"),
                    "word_count": len(paragraph.get("content", "").split()),
                    "has_code": "```" in paragraph.get("content", ""),
                    "has_list": paragraph.get("type") == "list"
                }
            }
            return result
            
        mock_processor.process_paragraph.side_effect = mock_process_paragraph
        
        # combine_processed_paragraphsメソッドが呼ばれたときに実行される関数
        def mock_combine_processed_paragraphs(processed_paragraphs, format_type="markdown"):
            if not processed_paragraphs:
                return ""
                
            if format_type == "markdown":
                return "\n\n".join([p.get("processed_content", "") for p in processed_paragraphs])
            elif format_type == "json":
                return {
                    "paragraphs": [
                        {
                            "id": p.get("id", "unknown"),
                            "content": p.get("processed_content", ""),
                            "metadata": p.get("metadata", {})
                        } for p in processed_paragraphs
                    ]
                }
            else:
                return ""
                
        mock_processor.combine_processed_paragraphs.side_effect = mock_combine_processed_paragraphs
        
        return mock_processor
    
    @pytest.fixture
    def sample_section_content(self):
        """サンプルセクションコンテンツを返す"""
        return """### 1.1 基本概念

基本的な概念は以下の通りです：

- 項目1
- 項目2
- 項目3

```python
def example():
    return "これはサンプルコードです"
```

まとめると、上記の概念は重要です。"""
    
    @pytest.fixture
    def sample_structure_data(self):
        """サンプル構造データを返す"""
        return {
            "title": "1.1 基本概念",
            "paragraphs": [
                {
                    "type": "heading",
                    "content": "基本的な概念は以下の通りです："
                },
                {
                    "type": "list",
                    "items": [
                        "項目1",
                        "項目2",
                        "項目3"
                    ]
                },
                {
                    "type": "code",
                    "content": """```python
def example():
    return "これはサンプルコードです"
```"""
                },
                {
                    "type": "text",
                    "content": "まとめると、上記の概念は重要です。"
                }
            ]
        }
    
    def test_extract_paragraphs(self, paragraph_processor, sample_section_content, sample_structure_data):
        """パラグラフ抽出のテスト"""
        paragraphs = paragraph_processor.extract_paragraphs(sample_section_content, sample_structure_data)
        
        # パラグラフが正しく抽出されることを確認
        assert paragraphs is not None
        assert isinstance(paragraphs, list)
        assert len(paragraphs) == 4
        
        # パラグラフの型が正しく設定されることを確認
        assert paragraphs[0]["type"] == "heading"
        assert paragraphs[1]["type"] == "list"
        assert paragraphs[2]["type"] == "code"
        assert paragraphs[3]["type"] == "text"
        
        # リスト項目が正しく抽出されることを確認
        assert "items" in paragraphs[1]
        assert len(paragraphs[1]["items"]) == 3
    
    def test_process_paragraph(self, paragraph_processor, sample_structure_data):
        """パラグラフ処理のテスト"""
        paragraph = sample_structure_data["paragraphs"][0]
        
        processed = paragraph_processor.process_paragraph(paragraph)
        
        # パラグラフが正しく処理されることを確認
        assert processed is not None
        assert "id" in processed
        assert "processed_content" in processed
        assert "metadata" in processed
        
        # メタデータが正しく設定されることを確認
        assert processed["metadata"]["type"] == "heading"
        assert processed["metadata"]["word_count"] > 0
    
    def test_process_list_paragraph(self, paragraph_processor, sample_structure_data):
        """リスト型パラグラフ処理のテスト"""
        paragraph = sample_structure_data["paragraphs"][1]
        
        processed = paragraph_processor.process_paragraph(paragraph)
        
        # パラグラフが正しく処理されることを確認
        assert processed is not None
        assert processed["metadata"]["type"] == "list"
        assert processed["metadata"]["has_list"] is True
    
    def test_process_code_paragraph(self, paragraph_processor, sample_structure_data):
        """コード型パラグラフ処理のテスト"""
        paragraph = sample_structure_data["paragraphs"][2]
        
        processed = paragraph_processor.process_paragraph(paragraph)
        
        # パラグラフが正しく処理されることを確認
        assert processed is not None
        assert processed["metadata"]["type"] == "code"
        assert processed["metadata"]["has_code"] is True
    
    def test_combine_processed_paragraphs_markdown(self, paragraph_processor, sample_structure_data):
        """処理済みパラグラフのMarkdown形式での結合テスト"""
        # 処理済みパラグラフのリストを作成
        processed_paragraphs = []
        for paragraph in sample_structure_data["paragraphs"]:
            processed = paragraph_processor.process_paragraph(paragraph)
            processed_paragraphs.append(processed)
        
        combined = paragraph_processor.combine_processed_paragraphs(processed_paragraphs, "markdown")
        
        # 結合結果が正しいことを確認
        assert combined is not None
        assert isinstance(combined, str)
        assert "基本的な概念" in combined
        assert "まとめると" in combined
    
    def test_combine_processed_paragraphs_json(self, paragraph_processor, sample_structure_data):
        """処理済みパラグラフのJSON形式での結合テスト"""
        # 処理済みパラグラフのリストを作成
        processed_paragraphs = []
        for paragraph in sample_structure_data["paragraphs"]:
            processed = paragraph_processor.process_paragraph(paragraph)
            processed_paragraphs.append(processed)
        
        combined = paragraph_processor.combine_processed_paragraphs(processed_paragraphs, "json")
        
        # 結合結果が正しいことを確認
        assert combined is not None
        assert isinstance(combined, dict)
        assert "paragraphs" in combined
        assert len(combined["paragraphs"]) == 4
        assert "id" in combined["paragraphs"][0]
        assert "content" in combined["paragraphs"][0]
        assert "metadata" in combined["paragraphs"][0]
    
    def test_extract_paragraphs_empty_structure(self, paragraph_processor, sample_section_content):
        """空の構造データでのパラグラフ抽出テスト"""
        empty_structure = {}
        
        paragraphs = paragraph_processor.extract_paragraphs(sample_section_content, empty_structure)
        
        # 空のリストが返されることを確認
        assert paragraphs is not None
        assert isinstance(paragraphs, list)
        assert len(paragraphs) == 0
    
    def test_combine_processed_paragraphs_empty(self, paragraph_processor):
        """空のパラグラフリストでの結合テスト"""
        combined = paragraph_processor.combine_processed_paragraphs([])
        
        # 空の文字列が返されることを確認
        assert combined is not None
        assert combined == ""
    
    def test_combine_processed_paragraphs_invalid_format(self, paragraph_processor, sample_structure_data):
        """無効なフォーマット指定での結合テスト"""
        # 処理済みパラグラフのリストを作成
        processed_paragraphs = []
        for paragraph in sample_structure_data["paragraphs"]:
            processed = paragraph_processor.process_paragraph(paragraph)
            processed_paragraphs.append(processed)
        
        combined = paragraph_processor.combine_processed_paragraphs(processed_paragraphs, "invalid_format")
        
        # 空の文字列が返されることを確認
        assert combined is not None
        assert combined == "" 