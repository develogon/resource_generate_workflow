import pytest
import os
import shutil
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート
from app.processors.chapter import ChapterProcessor

class TestChapterProcessor:
    """チャプタープロセッサのテストクラス"""
    
    @pytest.fixture
    def chapter_processor(self):
        """テスト用のチャプタープロセッサインスタンスを作成"""
        return ChapterProcessor()
    
    @pytest.fixture
    def sample_chapter_content(self):
        """サンプルのチャプターコンテンツを返す"""
        return """## 第1章: はじめに

この章では、システムの概要と基本的な考え方について説明します。

### 1.1 システム概要

システムは以下のコンポーネントで構成されています：

- コンポーネント1
- コンポーネント2
- コンポーネント3

### 1.2 基本的な考え方

基本的な考え方は次の通りです：

1. 原則1
2. 原則2
3. 原則3
"""
    
    def test_create_chapter_folder(self, chapter_processor, tmp_path):
        """チャプターフォルダ作成のテスト"""
        # フォルダパラメータの設定
        chapter_info = {
            "number": 1,
            "title": "はじめに"
        }
        base_dir = str(tmp_path)
        
        # チャプターフォルダを作成
        chapter_dir = chapter_processor.create_chapter_folder(chapter_info, base_dir)
        
        # フォルダが作成されていることを確認
        assert chapter_dir is not None
        assert chapter_dir.endswith("chapter1")
        assert (tmp_path / "chapter1").exists()
    
    def test_write_chapter_content(self, chapter_processor, sample_chapter_content, tmp_path):
        """チャプターコンテンツ書き込みのテスト"""
        # フォルダを作成
        chapter_dir = str(tmp_path / "chapter1")
        if not (tmp_path / "chapter1").exists():
            (tmp_path / "chapter1").mkdir()
        
        # コンテンツを書き込み
        file_path = chapter_processor.write_chapter_content(sample_chapter_content, chapter_dir)
        
        # ファイルが作成されていることを確認
        assert file_path is not None
        assert (tmp_path / "chapter1" / "text.md").exists()
        
        # ファイルの内容を確認
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert content == sample_chapter_content
    
    def test_extract_chapter_title(self, chapter_processor, sample_chapter_content):
        """チャプタータイトル抽出のテスト"""
        title = chapter_processor.extract_chapter_title(sample_chapter_content)
        
        # タイトルが正しく抽出されることを確認
        assert title is not None
        assert title == "第1章: はじめに"
    
    def test_get_chapter_number(self, chapter_processor):
        """チャプター番号取得のテスト"""
        chapter_titles = [
            "第1章: はじめに",
            "第2章: 基本概念",
            "第３章: 実装方法"  # 全角数字
        ]
        
        # 各チャプターの番号を取得
        numbers = [chapter_processor.get_chapter_number(title) for title in chapter_titles]
        
        # 番号が正しく取得されることを確認
        assert numbers == [1, 2, 3]
    
    def test_process_chapter(self, chapter_processor, sample_chapter_content, tmp_path):
        """チャプター処理のテスト"""
        # 処理パラメータの設定
        base_dir = str(tmp_path)
        
        # チャプターを処理
        result = chapter_processor.process_chapter(sample_chapter_content, base_dir)
        
        # 処理結果を確認
        assert result is not None
        assert "chapter_dir" in result
        assert "title" in result
        assert "number" in result
        assert "file_path" in result
        assert result["title"] == "第1章: はじめに"
        assert result["number"] == 1
        assert (tmp_path / "chapter1").exists()
        assert (tmp_path / "chapter1" / "text.md").exists()
    
    def test_extract_chapter_metadata(self, chapter_processor, sample_chapter_content):
        """チャプターメタデータ抽出のテスト"""
        metadata = chapter_processor.extract_chapter_metadata(sample_chapter_content)
        
        # メタデータが正しく抽出されることを確認
        assert metadata is not None
        assert "title" in metadata
        assert "number" in metadata
        assert "first_paragraph" in metadata
        assert metadata["title"] == "第1章: はじめに"
        assert metadata["number"] == 1
        assert "この章では" in metadata["first_paragraph"]
    
    def test_combine_chapter_contents(self, chapter_processor, tmp_path):
        """チャプターコンテンツ結合のテスト"""
        chapter_dir = tmp_path / "第1章_はじめに"
        chapter_dir.mkdir()
        
        # テスト用のセクションコンテンツを作成
        section1_article = "# セクション1の記事\n\nセクション1の内容です。"
        section2_article = "# セクション2の記事\n\nセクション2の内容です。"
        
        section1_dir = chapter_dir / "1_1_基本概念"
        section2_dir = chapter_dir / "1_2_重要な考え方"
        section1_dir.mkdir()
        section2_dir.mkdir()
        
        with open(section1_dir / "article.md", "w") as f:
            f.write(section1_article)
        
        with open(section2_dir / "article.md", "w") as f:
            f.write(section2_article)
        
        # 結合処理
        combined_article = chapter_processor.combine_chapter_contents(str(chapter_dir), "article.md")
        
        # 結果が正しいことを確認
        assert combined_article is not None
        assert "セクション1の内容" in combined_article
        assert "セクション2の内容" in combined_article
        
        # 結合ファイルが作成されたことを確認
        combined_file = chapter_dir / "article.md"
        assert os.path.exists(combined_file)
    
    def test_sanitize_filename(self, chapter_processor):
        """ファイル名のサニタイズテスト"""
        # テスト用のタイトル
        titles = [
            "第1章: はじめに",
            "第2章：実践編",
            "第3章 - 応用",
            "第4章 (補足)",
            "第5章/まとめ"
        ]
        
        expected_results = [
            "第1章_はじめに",
            "第2章_実践編",
            "第3章_応用",
            "第4章_補足",
            "第5章_まとめ"
        ]
        
        # 各タイトルをサニタイズ
        for i, title in enumerate(titles):
            result = chapter_processor.sanitize_filename(title)
            assert result == expected_results[i] 