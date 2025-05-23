"""バリデーションシステムのテスト."""

import tempfile
from pathlib import Path

import pytest

from src.utils.validation import (
    validate_api_response,
    validate_content_structure,
    validate_file_path,
    validate_markdown_content,
    validate_workflow_config,
)


class TestValidateMarkdownContent:
    """validate_markdown_contentのテスト."""
    
    def test_empty_content(self):
        """空のコンテンツのテスト."""
        result = validate_markdown_content("")
        
        assert not result["valid"]
        assert "Content is empty" in result["errors"][0]
        assert result["stats"]["character_count"] == 0
    
    def test_whitespace_only_content(self):
        """空白のみのコンテンツのテスト."""
        result = validate_markdown_content("   \n  \n  ")
        
        assert not result["valid"]
        assert "Content is empty" in result["errors"][0]
    
    def test_valid_basic_content(self):
        """基本的な有効コンテンツのテスト."""
        content = """# タイトル

これは段落です。

## サブタイトル

- リスト項目1
- リスト項目2
"""
        result = validate_markdown_content(content)
        
        assert result["valid"]
        assert len(result["errors"]) == 0
        assert result["stats"]["heading_count"] == 2
        assert result["stats"]["character_count"] > 0
        assert result["stats"]["word_count"] > 0
    
    def test_heading_validation(self):
        """見出しのバリデーション."""
        content = """# 正常な見出し

####### レベル7の見出し

#

## 正常なサブ見出し
"""
        result = validate_markdown_content(content)
        
        assert not result["valid"]  # 空の見出しがエラーになる
        assert len(result["warnings"]) == 2  # レベル7の警告 + 短いコンテンツの警告
        assert len(result["errors"]) == 1    # 空の見出しのエラー
        assert "Heading level 7 exceeds maximum" in result["warnings"][0]
        assert "Empty heading" in result["errors"][0]
        assert result["stats"]["heading_count"] == 4  # 4つの見出し（空の見出し含む）
    
    def test_code_block_validation(self):
        """コードブロックのバリデーション."""
        content = """# コードサンプル

```python
def hello():
    print("Hello")
```

```
未閉じのコードブロック
"""
        result = validate_markdown_content(content)
        
        assert not result["valid"]
        assert "Unclosed code block detected" in result["errors"]
        assert result["stats"]["code_block_count"] == 2
    
    def test_link_validation(self):
        """リンクのバリデーション."""
        content = """# リンクテスト

[正常なリンク](https://example.com)
[空のURL]()
[](https://example.com)
"""
        result = validate_markdown_content(content)
        
        assert not result["valid"]
        assert any("Empty link URL" in error for error in result["errors"])
        assert any("Empty link text" in warning for warning in result["warnings"])
        assert result["stats"]["link_count"] == 3
    
    def test_image_validation(self):
        """画像のバリデーション."""
        content = """# 画像テスト

![正常な画像](image.png)
![](empty-alt.png)
![alt text]()
"""
        result = validate_markdown_content(content)
        
        assert not result["valid"]
        assert any("Empty image URL" in error for error in result["errors"])
        assert any("Missing alt text" in warning for warning in result["warnings"])
        assert result["stats"]["image_count"] == 3
    
    def test_content_warnings(self):
        """コンテンツの警告テスト."""
        # 見出しなし
        content = "ただの段落です。"
        result = validate_markdown_content(content)
        
        assert result["valid"]
        assert any("No headings found" in warning for warning in result["warnings"])
        
        # 短すぎるコンテンツ
        short_content = "短い"
        result = validate_markdown_content(short_content)
        
        assert result["valid"]
        assert any("very short" in warning for warning in result["warnings"])


class TestValidateFilePath:
    """validate_file_pathのテスト."""
    
    def test_empty_path(self):
        """空のパスのテスト."""
        result = validate_file_path("")
        
        assert not result["valid"]
        assert "File path is empty" in result["errors"][0]
        assert not result["exists"]
    
    def test_nonexistent_file_required(self):
        """存在しないファイル（必須）のテスト."""
        result = validate_file_path("nonexistent.txt")
        
        assert not result["valid"]
        assert "File does not exist" in result["errors"][0]
        assert not result["exists"]
    
    def test_nonexistent_file_optional(self):
        """存在しないファイル（任意）のテスト."""
        result = validate_file_path("nonexistent.txt", must_exist=False)
        
        assert result["valid"]
        assert len(result["errors"]) == 0
        assert not result["exists"]
    
    def test_existing_file(self):
        """存在するファイルのテスト."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        try:
            result = validate_file_path(temp_path)
            
            assert result["valid"]
            assert len(result["errors"]) == 0
            assert result["exists"]
            assert result["extension"] == ".txt"
        finally:
            temp_path.unlink()
    
    def test_directory_as_file(self):
        """ディレクトリを指定した場合のテスト."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_file_path(temp_dir)
            
            assert result["valid"]  # 警告のみ
            assert any("directory" in warning for warning in result["warnings"])
            assert result["exists"]
    
    def test_extension_validation(self):
        """拡張子のバリデーション."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('test')")
            temp_path = Path(f.name)
        
        try:
            # 許可されていない拡張子
            result = validate_file_path(temp_path, allowed_extensions=['.txt', '.md'])
            assert not result["valid"]
            assert "Invalid file extension" in result["errors"][0]
            
            # 許可された拡張子
            result = validate_file_path(temp_path, allowed_extensions=['.py', '.txt'])
            assert result["valid"]
        finally:
            temp_path.unlink()
    
    def test_file_size_validation(self):
        """ファイルサイズのバリデーション."""
        content = "x" * 1000  # 1KB
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)
        
        try:
            # サイズ制限以下
            result = validate_file_path(temp_path, max_size_mb=0.01)  # 10KB制限
            assert result["valid"]
            
            # サイズ制限超過
            result = validate_file_path(temp_path, max_size_mb=0.0001)  # 0.1KB制限
            assert not result["valid"]
            assert "File size" in result["errors"][0]
        finally:
            temp_path.unlink()
    
    def test_path_security(self):
        """パスのセキュリティチェック."""
        # 親ディレクトリ参照
        result = validate_file_path("../dangerous.txt", must_exist=False)
        
        assert result["valid"]  # 警告のみ
        assert any("parent directory" in warning for warning in result["warnings"])


class TestValidateContentStructure:
    """validate_content_structureのテスト."""
    
    def test_valid_content(self):
        """有効なコンテンツ構造のテスト."""
        content = {
            "id": "test_content_123",
            "title": "テストコンテンツ",
            "content": "これは十分な長さのコンテンツです。" * 10,
            "metadata": {"author": "test"}
        }
        
        result = validate_content_structure(content)
        
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_missing_required_fields(self):
        """必須フィールドが不足している場合のテスト."""
        content = {
            "title": "テストコンテンツ"
            # id と content が不足
        }
        
        result = validate_content_structure(content)
        
        assert not result["valid"]
        assert len(result["errors"]) == 2
        assert any("Required field missing: id" in error for error in result["errors"])
        assert any("Required field missing: content" in error for error in result["errors"])
    
    def test_empty_required_fields(self):
        """必須フィールドが空の場合のテスト."""
        content = {
            "id": "",
            "title": "   ",
            "content": None
        }
        
        result = validate_content_structure(content)
        
        assert not result["valid"]
        assert len(result["errors"]) == 3
    
    def test_id_validation(self):
        """IDのバリデーション."""
        # 無効なID（非文字列）
        content1 = {
            "id": 123,
            "title": "テスト",
            "content": "コンテンツ"
        }
        result1 = validate_content_structure(content1)
        assert not result1["valid"]
        assert "ID must be a string" in result1["errors"][0]
        
        # 特殊文字を含むID
        content2 = {
            "id": "test@content!",
            "title": "テスト",
            "content": "コンテンツ"
        }
        result2 = validate_content_structure(content2)
        assert result2["valid"]  # 警告のみ
        assert any("special characters" in warning for warning in result2["warnings"])
    
    def test_content_length_warnings(self):
        """コンテンツ長の警告テスト."""
        # 短すぎるタイトル
        content1 = {
            "id": "test",
            "title": "短",
            "content": "コンテンツ" * 20
        }
        result1 = validate_content_structure(content1)
        assert result1["valid"]
        assert any("very short" in warning for warning in result1["warnings"])
        
        # 長すぎるタイトル（200文字を超える）
        content2 = {
            "id": "test",
            "title": "非常に長いタイトルです。" * 25,  # 25回繰り返すと250文字程度
            "content": "コンテンツ" * 20
        }
        result2 = validate_content_structure(content2)
        assert result2["valid"]
        assert any("very long" in warning for warning in result2["warnings"])
    
    def test_metadata_validation(self):
        """メタデータのバリデーション."""
        content = {
            "id": "test",
            "title": "テスト",
            "content": "コンテンツ",
            "metadata": "not a dict"
        }
        
        result = validate_content_structure(content)
        
        assert not result["valid"]
        assert "Metadata must be a dictionary" in result["errors"][0]


class TestValidateWorkflowConfig:
    """validate_workflow_configのテスト."""
    
    def test_valid_config(self):
        """有効な設定のテスト."""
        config = {
            "lang": "ja",
            "title": "テストワークフロー",
            "max_concurrent_tasks": 10,
            "batch_size": 50,
            "timeout": 300
        }
        
        result = validate_workflow_config(config)
        
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_missing_required_fields(self):
        """必須フィールドが不足している場合のテスト."""
        config = {
            "max_concurrent_tasks": 10
            # lang と title が不足
        }
        
        result = validate_workflow_config(config)
        
        assert not result["valid"]
        assert len(result["errors"]) == 2
    
    def test_language_validation(self):
        """言語設定のバリデーション."""
        config = {
            "lang": "fr",  # サポートされていない言語
            "title": "テスト"
        }
        
        result = validate_workflow_config(config)
        
        assert result["valid"]  # 警告のみ
        assert any("may not be fully supported" in warning for warning in result["warnings"])
    
    def test_numeric_parameter_validation(self):
        """数値パラメータのバリデーション."""
        # 無効な max_concurrent_tasks
        config1 = {
            "lang": "ja",
            "title": "テスト",
            "max_concurrent_tasks": 0
        }
        result1 = validate_workflow_config(config1)
        assert not result1["valid"]
        
        # 高すぎる値
        config2 = {
            "lang": "ja",
            "title": "テスト",
            "max_concurrent_tasks": 100
        }
        result2 = validate_workflow_config(config2)
        assert result2["valid"]  # 警告のみ
        assert any("very high" in warning for warning in result2["warnings"])


class TestValidateApiResponse:
    """validate_api_responseのテスト."""
    
    def test_valid_response(self):
        """有効なAPIレスポンスのテスト."""
        response = {
            "success": True,
            "data": {"result": "test"},
            "message": "OK"
        }
        
        result = validate_api_response(response, ["success", "data"])
        
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_non_dict_response(self):
        """辞書でないレスポンスのテスト."""
        result = validate_api_response("not a dict", [])
        
        assert not result["valid"]
        assert "Response must be a dictionary" in result["errors"][0]
    
    def test_missing_required_fields(self):
        """必須フィールドが不足している場合のテスト."""
        response = {
            "data": {"result": "test"}
            # success フィールドが不足
        }
        
        result = validate_api_response(response, ["success", "data"])
        
        assert not result["valid"]
        assert "Required field missing: success" in result["errors"][0]
    
    def test_error_field_validation(self):
        """エラーフィールドのバリデーション."""
        response = {
            "success": False,
            "error": "Something went wrong",
            "data": None
        }
        
        result = validate_api_response(response, ["success"])
        
        assert not result["valid"]
        assert "API returned error" in result["errors"][0]
    
    def test_data_warnings(self):
        """データフィールドの警告テスト."""
        # null データ
        response1 = {
            "success": True,
            "data": None
        }
        result1 = validate_api_response(response1, ["success"])
        assert result1["valid"]
        assert any("data is null" in warning for warning in result1["warnings"])
        
        # 空文字列データ
        response2 = {
            "success": True,
            "data": "   "
        }
        result2 = validate_api_response(response2, ["success"])
        assert result2["valid"]
        assert any("empty string" in warning for warning in result2["warnings"]) 