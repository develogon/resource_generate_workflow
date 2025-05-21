import pytest
import logging
import os
from unittest.mock import patch, MagicMock

from utils.logging import setup_logging
from utils.helpers import sanitize_filename, ensure_directory_exists, extract_title
from utils.exceptions import AppException, APIException, ProcessingException


class TestLogging:
    """ロギングユーティリティのテスト"""

    def test_setup_logging(self, temp_dir):
        """ロギング設定のテスト"""
        # ログファイルパス
        log_file = os.path.join(str(temp_dir), "test.log")
        
        # ロギング設定
        logger = setup_logging(log_file, level=logging.DEBUG)
        
        # ロガーが正しく設定されていることを確認
        assert logger.level == logging.DEBUG
        
        # ログファイルが作成されたことを確認
        assert os.path.exists(log_file)
        
        # テストメッセージをログ出力
        test_message = "テストログメッセージ"
        logger.info(test_message)
        
        # ログファイルにメッセージが書き込まれたことを確認
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert test_message in log_content


class TestHelpers:
    """ヘルパー関数のテスト"""

    def test_sanitize_filename(self):
        """ファイル名サニタイズのテスト"""
        # 特殊文字を含むファイル名
        filename = "test/file:name*with?invalid<chars>"
        sanitized = sanitize_filename(filename)
        
        # 特殊文字が置換されていることを確認
        assert "/" not in sanitized
        assert ":" not in sanitized
        assert "*" not in sanitized
        assert "?" not in sanitized
        assert "<" not in sanitized
        assert ">" not in sanitized
        
        # スペースがアンダースコアに置換されていることを確認
        space_filename = "test file name"
        sanitized_space = sanitize_filename(space_filename)
        assert " " not in sanitized_space
        assert "_" in sanitized_space
        
        # 日本語ファイル名
        japanese_filename = "テストファイル名"
        sanitized_japanese = sanitize_filename(japanese_filename)
        assert sanitized_japanese == "テストファイル名"

    def test_ensure_directory_exists(self, temp_dir):
        """ディレクトリ存在確認のテスト"""
        # 存在しないディレクトリパス
        new_dir = os.path.join(str(temp_dir), "new_directory")
        
        # ディレクトリが存在しないことを確認
        assert not os.path.exists(new_dir)
        
        # ディレクトリ作成
        ensure_directory_exists(new_dir)
        
        # ディレクトリが作成されたことを確認
        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)
        
        # 既存ディレクトリに対しても正常に動作することを確認
        ensure_directory_exists(new_dir)
        assert os.path.exists(new_dir)

    def test_extract_title(self):
        """タイトル抽出のテスト"""
        # Markdownテキスト
        markdown = """# メインタイトル

## セクション1

テキスト内容。

## セクション2

その他のテキスト。
"""
        # タイトル抽出
        title = extract_title(markdown)
        assert title == "メインタイトル"
        
        # タイトルがない場合
        no_title_markdown = """テキスト内容。

## セクション

その他のテキスト。
"""
        assert extract_title(no_title_markdown) is None
        
        # 複数のタイトルがある場合（最初のみ抽出）
        multiple_titles = """# タイトル1

テキスト。

# タイトル2

その他のテキスト。
"""
        assert extract_title(multiple_titles) == "タイトル1"


class TestExceptions:
    """例外クラスのテスト"""

    def test_app_exception(self):
        """アプリケーション例外のテスト"""
        # 基本例外
        ex = AppException("テストエラー")
        assert str(ex) == "テストエラー"
        
        # エラーコード付き例外
        ex_with_code = AppException("テストエラー", error_code="E001")
        assert str(ex_with_code) == "E001: テストエラー"
        
        # 内部例外付き例外
        inner_ex = ValueError("内部エラー")
        ex_with_inner = AppException("テストエラー", inner_exception=inner_ex)
        assert "テストエラー" in str(ex_with_inner)
        assert "内部エラー" in str(ex_with_inner)

    def test_api_exception(self):
        """API例外のテスト"""
        # API例外
        ex = APIException("API呼び出しエラー", service_name="テストサービス")
        assert "API呼び出しエラー" in str(ex)
        assert "テストサービス" in str(ex)
        
        # ステータスコード付きAPI例外
        ex_with_status = APIException(
            "API呼び出しエラー", 
            service_name="テストサービス",
            status_code=429
        )
        assert "API呼び出しエラー" in str(ex_with_status)
        assert "テストサービス" in str(ex_with_status)
        assert "429" in str(ex_with_status)

    def test_processing_exception(self):
        """処理例外のテスト"""
        # 処理例外
        ex = ProcessingException("処理エラー", step="テストステップ")
        assert "処理エラー" in str(ex)
        assert "テストステップ" in str(ex)
        
        # リカバリー情報付き処理例外
        ex_with_recovery = ProcessingException(
            "処理エラー", 
            step="テストステップ",
            recovery_hint="再試行してください"
        )
        assert "処理エラー" in str(ex_with_recovery)
        assert "テストステップ" in str(ex_with_recovery)
        assert "再試行してください" in str(ex_with_recovery) 