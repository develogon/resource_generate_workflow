"""YAMLパーサーのテスト."""

import tempfile
from pathlib import Path

import pytest
import yaml

from src.parsers.yaml import ConfigParser, MetadataParser, YAMLParser


class TestYAMLParser:
    """YAMLParserのテスト."""
    
    @pytest.fixture
    def parser(self):
        """YAMLParserフィクスチャ."""
        return YAMLParser()
    
    def test_initialization(self, parser):
        """初期化のテスト."""
        assert parser.loader == yaml.SafeLoader
    
    def test_parse_valid_yaml(self, parser):
        """有効なYAMLのパーステスト."""
        content = """
title: テストタイトル
description: テストの説明
tags:
  - Python
  - YAML
settings:
  debug: true
  port: 8080
"""
        
        result = parser.parse(content)
        
        assert result["title"] == "テストタイトル"
        assert result["description"] == "テストの説明"
        assert result["tags"] == ["Python", "YAML"]
        assert result["settings"]["debug"] is True
        assert result["settings"]["port"] == 8080
    
    def test_parse_empty_content(self, parser):
        """空のコンテンツのパーステスト."""
        result = parser.parse("")
        assert result == {}
        
        result = parser.parse("   ")
        assert result == {}
        
        result = parser.parse(None)
        assert result == {}
    
    def test_parse_null_document(self, parser):
        """null ドキュメントのパーステスト."""
        content = "---\n---"
        result = parser.parse(content)
        assert result == {}
    
    def test_parse_invalid_yaml(self, parser):
        """不正なYAMLのパーステスト."""
        invalid_content = """
title: テスト
  invalid_indent: value
"""
        
        with pytest.raises(ValueError, match="Invalid YAML content"):
            parser.parse(invalid_content)
    
    def test_parse_non_dict_yaml(self, parser):
        """辞書以外のYAMLのパーステスト."""
        # リストのYAML
        list_content = """
- item1
- item2
- item3
"""
        
        with pytest.raises(ValueError, match="YAML content must be a dictionary"):
            parser.parse(list_content)
        
        # 文字列のYAML
        string_content = "just a string"
        
        with pytest.raises(ValueError, match="YAML content must be a dictionary"):
            parser.parse(string_content)
    
    def test_parse_file_valid(self, parser):
        """有効なファイルからのパーステスト."""
        content = """
title: ファイルテスト
description: ファイルからの読み込みテスト
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(content)
            f.flush()
            
            temp_path = Path(f.name)
            
            try:
                result = parser.parse_file(temp_path)
                
                assert result["title"] == "ファイルテスト"
                assert result["description"] == "ファイルからの読み込みテスト"
            finally:
                temp_path.unlink()
    
    def test_parse_file_not_found(self, parser):
        """存在しないファイルのパーステスト."""
        with pytest.raises(ValueError, match="Invalid file path"):
            parser.parse_file("nonexistent.yml")
    
    def test_parse_file_invalid_extension(self, parser):
        """無効な拡張子のファイルのパーステスト."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("title: test")
            f.flush()
            
            temp_path = Path(f.name)
            
            try:
                with pytest.raises(ValueError, match="Invalid file path"):
                    parser.parse_file(temp_path)
            finally:
                temp_path.unlink()
    
    def test_parse_multiple_documents(self, parser):
        """複数ドキュメントのパーステスト."""
        content = """
title: ドキュメント1
type: config
---
title: ドキュメント2
type: metadata
---
title: ドキュメント3
type: schema
"""
        
        documents = parser.parse_multiple(content)
        
        assert len(documents) == 3
        assert documents[0]["title"] == "ドキュメント1"
        assert documents[1]["title"] == "ドキュメント2"
        assert documents[2]["title"] == "ドキュメント3"
    
    def test_parse_multiple_empty_content(self, parser):
        """空の複数ドキュメントのパーステスト."""
        result = parser.parse_multiple("")
        assert result == []
    
    def test_parse_multiple_with_null_documents(self, parser):
        """null ドキュメントを含む複数ドキュメントのパーステスト."""
        content = """
title: ドキュメント1
---
---
title: ドキュメント2
"""
        
        documents = parser.parse_multiple(content)
        
        assert len(documents) == 2
        assert documents[0]["title"] == "ドキュメント1"
        assert documents[1]["title"] == "ドキュメント2"
    
    def test_parse_multiple_non_dict_document(self, parser):
        """辞書以外の複数ドキュメントのパーステスト."""
        content = """
title: ドキュメント1
---
- リスト項目1
- リスト項目2
"""
        
        with pytest.raises(ValueError, match="Each YAML document must be a dictionary"):
            parser.parse_multiple(content)
    
    def test_validate_schema_valid(self, parser):
        """有効なスキーマバリデーション."""
        data = {
            "title": "テストタイトル",
            "count": 42,
            "enabled": True,
            "tags": ["tag1", "tag2"],
            "config": {"debug": True}
        }
        
        schema = {
            "required": ["title", "count"],
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 100},
                "count": {"type": "integer", "minimum": 0, "maximum": 100},
                "enabled": {"type": "boolean"},
                "tags": {"type": "array"},
                "config": {"type": "object"}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is True
        assert result["errors"] == []
    
    def test_validate_schema_missing_required(self, parser):
        """必須フィールド不足のスキーマバリデーション."""
        data = {
            "title": "テスト"
            # countが不足
        }
        
        schema = {
            "required": ["title", "count"],
            "properties": {
                "title": {"type": "string"},
                "count": {"type": "integer"}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is False
        assert "Required field missing: count" in result["errors"]
    
    def test_validate_schema_null_required(self, parser):
        """必須フィールドがnullのスキーマバリデーション."""
        data = {
            "title": "テスト",
            "count": None
        }
        
        schema = {
            "required": ["title", "count"],
            "properties": {
                "title": {"type": "string"},
                "count": {"type": "integer"}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is False
        assert "Required field is null: count" in result["errors"]
    
    def test_validate_schema_type_errors(self, parser):
        """型エラーのスキーマバリデーション."""
        data = {
            "title": 123,  # 文字列であるべき
            "count": "42",  # 整数であるべき
            "enabled": "true",  # ブール値であるべき
            "tags": "tag1,tag2",  # 配列であるべき
            "config": "debug=true"  # オブジェクトであるべき
        }
        
        schema = {
            "properties": {
                "title": {"type": "string"},
                "count": {"type": "integer"},
                "enabled": {"type": "boolean"},
                "tags": {"type": "array"},
                "config": {"type": "object"}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is False
        assert any("must be a string" in error for error in result["errors"])
        assert any("must be an integer" in error for error in result["errors"])
        assert any("must be a boolean" in error for error in result["errors"])
        assert any("must be an array" in error for error in result["errors"])
        assert any("must be an object" in error for error in result["errors"])
    
    def test_validate_schema_range_errors(self, parser):
        """範囲エラーのスキーマバリデーション."""
        data = {
            "count": -5,  # 最小値未満
            "score": 150,  # 最大値超過
            "short_text": "",  # 最小長未満
            "long_text": "a" * 101  # 最大長超過
        }
        
        schema = {
            "properties": {
                "count": {"type": "integer", "minimum": 0},
                "score": {"type": "integer", "maximum": 100},
                "short_text": {"type": "string", "minLength": 1},
                "long_text": {"type": "string", "maxLength": 100}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is False
        assert any("must be >= 0" in error for error in result["errors"])
        assert any("must be <= 100" in error for error in result["errors"])
        assert any("must be at least 1 characters" in error for error in result["errors"])
        assert any("must be at most 100 characters" in error for error in result["errors"])
    
    def test_validate_schema_enum_error(self, parser):
        """列挙値エラーのスキーマバリデーション."""
        data = {
            "status": "invalid"
        }
        
        schema = {
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is False
        assert "must be one of ['active', 'inactive', 'pending']" in result["errors"][0]
    
    def test_validate_schema_additional_properties(self, parser):
        """追加プロパティのスキーマバリデーション."""
        data = {
            "title": "テスト",
            "unknown_field": "value"
        }
        
        schema = {
            "additionalProperties": False,
            "properties": {
                "title": {"type": "string"}
            }
        }
        
        result = parser.validate_schema(data, schema)
        
        assert result["valid"] is True  # エラーではなく警告
        assert "Unknown field: unknown_field" in result["warnings"]


class TestConfigParser:
    """ConfigParserのテスト."""
    
    @pytest.fixture
    def config_parser(self):
        """ConfigParserフィクスチャ."""
        return ConfigParser()
    
    def test_initialization(self, config_parser):
        """初期化のテスト."""
        assert config_parser.loader == yaml.SafeLoader
        assert "lang" in config_parser.config_schema["required"]
        assert "title" in config_parser.config_schema["required"]
    
    def test_parse_config_valid(self, config_parser):
        """有効な設定のパーステスト."""
        content = """
lang: ja
title: テスト設定
description: テスト用の設定ファイル
max_concurrent_tasks: 10
batch_size: 50
timeout: 300
output:
  formats:
    - article
    - script
  directory: output
"""
        
        result = config_parser.parse_config(content)
        
        assert result["lang"] == "ja"
        assert result["title"] == "テスト設定"
        assert result["max_concurrent_tasks"] == 10
        assert "article" in result["output"]["formats"]
    
    def test_parse_config_minimal(self, config_parser):
        """最小限の設定のパーステスト."""
        content = """
lang: en
title: Minimal Config
"""
        
        result = config_parser.parse_config(content)
        
        assert result["lang"] == "en"
        assert result["title"] == "Minimal Config"
    
    def test_parse_config_missing_required(self, config_parser):
        """必須フィールド不足の設定パーステスト."""
        content = """
description: 説明のみ
"""
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_parser.parse_config(content)
    
    def test_parse_config_invalid_lang(self, config_parser):
        """無効な言語の設定パーステスト."""
        content = """
lang: invalid_lang
title: Test
"""
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_parser.parse_config(content)
    
    def test_parse_config_invalid_types(self, config_parser):
        """無効な型の設定パーステスト."""
        content = """
lang: ja
title: Test
max_concurrent_tasks: "not_a_number"
"""
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_parser.parse_config(content)


class TestMetadataParser:
    """MetadataParserのテスト."""
    
    @pytest.fixture
    def metadata_parser(self):
        """MetadataParserフィクスチャ."""
        return MetadataParser()
    
    def test_initialization(self, metadata_parser):
        """初期化のテスト."""
        assert metadata_parser.loader == yaml.SafeLoader
        assert "title" in metadata_parser.metadata_schema["required"]
    
    def test_parse_metadata_valid(self, metadata_parser):
        """有効なメタデータのパーステスト."""
        content = """
title: テスト記事
author: テスト太郎
date: 2024-01-01
tags:
  - Python
  - テスト
category: プログラミング
"""
        
        result = metadata_parser.parse_metadata(content)
        
        assert result["title"] == "テスト記事"
        assert result["author"] == "テスト太郎"
        assert result["date"] == "2024-01-01"
        assert "Python" in result["tags"]
        assert result["category"] == "プログラミング"
    
    def test_parse_metadata_missing_title(self, metadata_parser):
        """タイトル不足のメタデータパーステスト."""
        content = """
author: テスト太郎
description: 説明のみ
"""
        
        with pytest.raises(ValueError, match="Metadata validation failed"):
            metadata_parser.parse_metadata(content)
    
    def test_extract_from_frontmatter_valid(self, metadata_parser):
        """有効なfront matterからの抽出テスト."""
        content = """---
title: Front Matter Test
author: Test Author
tags: [python, yaml]
---

# コンテンツ

本文がここに続きます。
"""
        
        result = metadata_parser.extract_from_frontmatter(content)
        
        assert result["title"] == "Front Matter Test"
        assert result["author"] == "Test Author"
        assert result["tags"] == ["python", "yaml"]
        assert "metadata" in result
        assert result["metadata"]["has_frontmatter"] is True
    
    def test_extract_from_frontmatter_no_frontmatter(self, metadata_parser):
        """front matterなしの抽出テスト."""
        content = """# タイトル

front matterのないコンテンツです。
"""
        
        result = metadata_parser.extract_from_frontmatter(content)
        
        assert "title" not in result or result["title"] == ""
        assert result["metadata"]["has_frontmatter"] is False
    
    def test_extract_from_frontmatter_invalid_yaml(self, metadata_parser):
        """無効なYAMLのfront matter抽出テスト."""
        content = """---
title: Test
  invalid_indent: value
---

# コンテンツ
"""
        
        result = metadata_parser.extract_from_frontmatter(content)
        
        # 無効なYAMLの場合は空の結果を返す
        assert result["metadata"]["has_frontmatter"] is False
        assert result["metadata"]["parse_error"] is True
    
    def test_extract_from_frontmatter_empty(self, metadata_parser):
        """空のfront matter抽出テスト."""
        content = """---
---

# コンテンツ
"""
        
        result = metadata_parser.extract_from_frontmatter(content)
        
        assert result["metadata"]["has_frontmatter"] is True
        # 空のfront matterでも正常に処理される
    
    def test_extract_from_frontmatter_complex(self, metadata_parser):
        """複雑なfront matter抽出テスト."""
        content = """---
title: 複雑なメタデータテスト
author: 
  name: テスト太郎
  email: test@example.com
date: 2024-01-01T10:00:00Z
tags:
  - Python
  - YAML
  - テスト
seo:
  description: SEO用の説明
  keywords: [Python, YAML, メタデータ]
custom_fields:
  priority: high
  version: 1.2.3
---

# メイン記事

複雑なメタデータを持つ記事のコンテンツです。
"""
        
        result = metadata_parser.extract_from_frontmatter(content)
        
        assert result["title"] == "複雑なメタデータテスト"
        assert result["author"]["name"] == "テスト太郎"
        assert result["author"]["email"] == "test@example.com"
        assert len(result["tags"]) == 3
        assert result["seo"]["description"] == "SEO用の説明"
        assert result["custom_fields"]["priority"] == "high"
        assert result["metadata"]["has_frontmatter"] is True
        assert result["metadata"]["field_count"] > 5


class TestYAMLParserIntegration:
    """YAMLパーサーの統合テスト."""
    
    def test_yaml_parser_inheritance(self):
        """継承関係のテスト."""
        config_parser = ConfigParser()
        metadata_parser = MetadataParser()
        
        assert isinstance(config_parser, YAMLParser)
        assert isinstance(metadata_parser, YAMLParser)
    
    def test_file_processing_workflow(self):
        """ファイル処理ワークフローのテスト."""
        # 設定ファイル
        config_content = """
lang: ja
title: ワークフローテスト
max_concurrent_tasks: 5
output:
  formats: [article, script]
  directory: output
"""
        
        # メタデータファイル
        metadata_content = """---
title: テスト記事
author: テスト作者
tags: [workflow, integration]
---

# 記事コンテンツ

統合テスト用の記事です。
"""
        
        config_parser = ConfigParser()
        metadata_parser = MetadataParser()
        
        # 設定の解析
        config = config_parser.parse_config(config_content)
        assert config["lang"] == "ja"
        assert config["max_concurrent_tasks"] == 5
        
        # メタデータの抽出
        metadata = metadata_parser.extract_from_frontmatter(metadata_content)
        assert metadata["title"] == "テスト記事"
        assert metadata["author"] == "テスト作者"
        
        # 統合確認
        assert config["lang"] == "ja"  # 設定から言語取得
        assert metadata["title"] == "テスト記事"  # メタデータからタイトル取得
    
    def test_error_handling_consistency(self):
        """エラーハンドリングの一貫性テスト."""
        yaml_parser = YAMLParser()
        config_parser = ConfigParser()
        metadata_parser = MetadataParser()
        
        invalid_yaml = "title: test\n  invalid: indent"
        
        # 全てのパーサーで同様のエラーが発生することを確認
        with pytest.raises(ValueError):
            yaml_parser.parse(invalid_yaml)
        
        with pytest.raises(ValueError):
            config_parser.parse_config(invalid_yaml)
        
        with pytest.raises(ValueError):
            metadata_parser.parse_metadata(invalid_yaml) 