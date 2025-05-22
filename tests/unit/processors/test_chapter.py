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
    def sample_chapter_data(self):
        """サンプルチャプターデータを返す"""
        return {
            "title": "第1章: はじめに",
            "content": """## 第1章: はじめに

この章では基本的な概念について説明します。

### 1.1 基本概念

基本的な概念は以下の通りです：

- 項目1
- 項目2
- 項目3

### 1.2 重要な考え方

重要な考え方について説明します。"""
        }
    
    def test_create_chapter_folder(self, chapter_processor, tmp_path):
        """チャプターフォルダ作成のテスト"""
        base_dir = tmp_path / "test_content"
        base_dir.mkdir()
        
        chapter_title = "第1章: はじめに"
        
        # 実際のインスタンスを使用
        chapter_dir = chapter_processor.create_chapter_folder(str(base_dir), chapter_title)
        
        # 結果が正しいことを確認
        assert chapter_dir is not None
        assert os.path.exists(chapter_dir)
        assert "第1章_はじめに" in chapter_dir
        assert str(base_dir) in chapter_dir
    
    @patch("builtins.open", new_callable=mock_open)
    def test_write_chapter_content(self, mock_file, chapter_processor, sample_chapter_data, tmp_path):
        """チャプターコンテンツ書き込みのテスト"""
        chapter_dir = tmp_path / "第1章_はじめに"
        chapter_dir.mkdir()
        
        chapter_file = chapter_processor.write_chapter_content(str(chapter_dir), sample_chapter_data["content"])
        
        # 結果が正しいことを確認
        mock_file.assert_called_with(os.path.join(str(chapter_dir), "text.md"), "w", encoding="utf-8")
        mock_file().write.assert_called_with(sample_chapter_data["content"])
        assert "text.md" in chapter_file
        assert str(chapter_dir) in chapter_file
    
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
    
    def test_extract_chapter_title(self, chapter_processor, sample_chapter_data):
        """チャプタータイトル抽出のテスト"""
        title = chapter_processor.extract_chapter_title(sample_chapter_data["content"])
        
        # 結果が正しいことを確認
        assert title is not None
        assert title == "第1章: はじめに"
    
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