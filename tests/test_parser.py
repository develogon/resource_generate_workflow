import pytest
from unittest.mock import patch, MagicMock

from core.parser import MarkdownParser, YAMLParser


class TestMarkdownParser:
    """Markdownパーサーのテストクラス"""

    def test_parse_markdown(self, sample_markdown_content):
        """Markdownの解析テスト"""
        parser = MarkdownParser()
        result = parser.parse_markdown(sample_markdown_content)
        
        # 基本的な解析結果の検証
        assert "title" in result
        assert "chapters" in result
        assert len(result["chapters"]) == 2
        assert result["title"] == "テストタイトル"
        
        # 章の検証
        chapter1 = result["chapters"][0]
        assert chapter1["title"] == "第1章 はじめに"
        assert len(chapter1["sections"]) == 2
        
        # セクションの検証
        section1 = chapter1["sections"][0]
        assert section1["title"] == "1.1 基礎知識"
        assert "このテキストは基礎知識についての説明です。" in section1["content"]

    def test_extract_sections(self, sample_markdown_content):
        """セクション抽出テスト"""
        parser = MarkdownParser()
        sections = parser.extract_sections(sample_markdown_content)
        
        assert len(sections) == 6  # 全セクション数
        assert sections[0]["level"] == 1  # タイトル
        assert sections[1]["level"] == 2  # 章
        assert sections[2]["level"] == 3  # セクション

    def test_extract_images(self, sample_markdown_content):
        """画像参照抽出テスト"""
        parser = MarkdownParser()
        images = parser.extract_images(sample_markdown_content)
        
        assert len(images) == 1
        assert images[0]["type"] == "mermaid"
        assert "graph TD" in images[0]["content"]


class TestYAMLParser:
    """YAMLパーサーのテストクラス"""

    def test_parse_yaml(self):
        """YAML解析テスト"""
        parser = YAMLParser()
        # テスト用の簡略化されたYAML
        yaml_content = """
        title: "テストタイトル"
        chapters:
          - id: "01"
            title: "第1章 はじめに"
            sections:
              - id: "01"
                title: "基礎知識"
                learning_objectives:
                  - "テスト目標1を理解する"
                  - "テスト目標2を習得する"
                paragraphs:
                  - type: "introduction_with_foreshadowing"
                    content_focus: "基礎知識の紹介"
                  - type: "basic_example"
                    content_focus: "応用知識の説明"
        """
        
        result = parser.parse_yaml(yaml_content)
        
        assert result["title"] == "テストタイトル"
        assert len(result["chapters"]) == 1
        assert result["chapters"][0]["title"] == "第1章 はじめに"
        
        # セクションの検証
        sections = result["chapters"][0]["sections"]
        assert len(sections) == 1
        assert sections[0]["title"] == "基礎知識"
        
        # パラグラフの検証
        paragraphs = sections[0]["paragraphs"]
        assert len(paragraphs) == 2
        assert paragraphs[0]["type"] == "introduction_with_foreshadowing"
        assert "基礎知識の紹介" in paragraphs[0]["content_focus"]

    def test_validate_yaml_structure(self):
        """YAML構造の検証テスト"""
        parser = YAMLParser()
        # 正常なYAML
        valid_yaml = """
        title: "テストタイトル"
        chapters:
          - id: "01"
            title: "テスト章"
        """
        # 正常なYAMLの検証
        assert parser.validate_structure(valid_yaml) is True
        
        # 不正なYAML（必須フィールドの欠落）
        invalid_yaml = """
        chapters:
          - id: "01"
            sections: []
        """
        with pytest.raises(ValueError):
            parser.validate_structure(invalid_yaml)

    def test_extract_learning_objectives(self):
        """学習目標抽出テスト"""
        parser = YAMLParser()
        yaml_content = """
        title: "テストタイトル"
        chapters:
          - id: "01"
            title: "第1章 はじめに"
            sections:
              - id: "01"
                title: "基礎知識"
                learning_objectives:
                  - "テスト目標1を理解する"
                  - "テスト目標2を習得する"
        """
        
        result = parser.parse_yaml(yaml_content)
        objectives = parser.extract_learning_objectives(result)
        
        assert len(objectives) == 2
        assert "テスト目標1を理解する" in objectives
        assert "テスト目標2を習得する" in objectives 