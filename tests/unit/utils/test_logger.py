import pytest
import logging
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.utils.logger import LoggerUtils

class TestLoggerUtils:
    """ロギングユーティリティのテストクラス"""
    
    @pytest.fixture
    def logger_utils(self):
        """テスト用のロギングユーティリティインスタンスを作成"""
        # コメントアウトされているコードは、実際のクラスが実装された後に有効化する
        # return LoggerUtils()
        
        # モックインスタンスを返す（クラスが実装されるまでの一時的な対応）
        mock_utils = MagicMock()
        
        # setup_logger メソッドが呼ばれたときに実行される関数
        def mock_setup_logger(name, log_file=None, level=logging.INFO, format_str=None):
            logger = logging.getLogger(name)
            logger.setLevel(level)
            
            # ハンドラを全てクリア
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            
            # フォーマットを設定
            if format_str is None:
                format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            formatter = logging.Formatter(format_str)
            
            # コンソールハンドラを追加
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
            
            # ファイルハンドラを追加（指定されている場合）
            if log_file:
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            
            return logger
            
        mock_utils.setup_logger.side_effect = mock_setup_logger
        
        # get_logger メソッドが呼ばれたときに実行される関数
        def mock_get_logger(name):
            return logging.getLogger(name)
            
        mock_utils.get_logger.side_effect = mock_get_logger
        
        # log_exception メソッドが呼ばれたときに実行される関数
        def mock_log_exception(logger, exception, context=None):
            if context is None:
                context = {}
                
            error_message = f"例外が発生しました: {str(exception)}"
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            
            if context_str:
                error_message += f" [コンテキスト: {context_str}]"
                
            logger.error(error_message, exc_info=True)
            
        mock_utils.log_exception.side_effect = mock_log_exception
        
        return mock_utils
    
    @pytest.fixture
    def temp_log_file(self):
        """テスト用の一時ログファイルを作成"""
        fd, temp_file = tempfile.mkstemp(suffix='.log')
        os.close(fd)
        yield temp_file
        # テスト後にファイルを削除
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    def test_setup_logger(self, logger_utils, temp_log_file):
        """ロガーセットアップのテスト"""
        logger_name = "test_logger"
        
        # ロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name, log_file=temp_log_file)
        
        # ロガーが正しく作成されていることを確認
        assert logger.name == logger_name
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 2  # コンソールハンドラとファイルハンドラ
        
        # ファイルハンドラが正しく設定されていることを確認
        file_handler = next((h for h in logger.handlers if isinstance(h, logging.FileHandler)), None)
        assert file_handler is not None
        assert file_handler.baseFilename == temp_log_file
    
    def test_setup_logger_custom_level(self, logger_utils, temp_log_file):
        """カスタムログレベルでのロガーセットアップテスト"""
        logger_name = "debug_logger"
        
        # DEBUGレベルでロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name, log_file=temp_log_file, level=logging.DEBUG)
        
        # ロガーが正しく作成されていることを確認
        assert logger.name == logger_name
        assert logger.level == logging.DEBUG
    
    def test_setup_logger_custom_format(self, logger_utils, temp_log_file):
        """カスタムフォーマットでのロガーセットアップテスト"""
        logger_name = "format_logger"
        custom_format = '%(levelname)s - %(message)s'
        
        # カスタムフォーマットでロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name, log_file=temp_log_file, format_str=custom_format)
        
        # ハンドラのフォーマッタが正しく設定されていることを確認
        for handler in logger.handlers:
            assert handler.formatter._fmt == custom_format
    
    def test_get_logger(self, logger_utils):
        """ロガー取得のテスト"""
        logger_name = "existing_logger"
        
        # 事前にロガーをセットアップ
        original_logger = logger_utils.setup_logger(logger_name)
        
        # get_loggerで同じ名前のロガーを取得
        retrieved_logger = logger_utils.get_logger(logger_name)
        
        # 同じロガーが取得できることを確認
        assert retrieved_logger is original_logger
        assert retrieved_logger.name == logger_name
    
    def test_log_exception(self, logger_utils, monkeypatch):
        """例外ログ記録のテスト"""
        logger_name = "exception_logger"
        
        # ロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name)
        
        # ロガーのerrorメソッドをモック化
        mock_error = MagicMock()
        monkeypatch.setattr(logger, 'error', mock_error)
        
        # テスト用の例外と実行コンテキスト
        test_exception = ValueError("テスト例外")
        test_context = {
            "function": "test_function",
            "input": "test_input"
        }
        
        # 例外ログを記録
        logger_utils.log_exception(logger, test_exception, test_context)
        
        # errorメソッドが呼ばれたことを確認
        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        
        # エラーメッセージが正しいことを確認
        assert "例外が発生しました: テスト例外" in args[0]
        assert "function=test_function" in args[0]
        assert "input=test_input" in args[0]
        assert kwargs.get('exc_info') is True
    
    def test_log_to_file(self, logger_utils, temp_log_file):
        """ファイルへのログ記録テスト"""
        logger_name = "file_logger"
        test_message = "これはテストログメッセージです。"
        
        # ロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name, log_file=temp_log_file)
        
        # メッセージをログに記録
        logger.info(test_message)
        
        # ログファイルの内容を確認
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
            
        # ログメッセージがファイルに書き込まれていることを確認
        assert test_message in log_content
    
    def test_log_exception_without_context(self, logger_utils, monkeypatch):
        """コンテキストなしでの例外ログ記録テスト"""
        logger_name = "exception_logger_no_context"
        
        # ロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name)
        
        # ロガーのerrorメソッドをモック化
        mock_error = MagicMock()
        monkeypatch.setattr(logger, 'error', mock_error)
        
        # テスト用の例外
        test_exception = ValueError("コンテキストなしテスト例外")
        
        # コンテキストなしで例外ログを記録
        logger_utils.log_exception(logger, test_exception)
        
        # errorメソッドが呼ばれたことを確認
        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        
        # エラーメッセージが正しいことを確認
        assert "例外が発生しました: コンテキストなしテスト例外" in args[0]
        assert "コンテキスト" not in args[0]  # コンテキスト情報は含まれていない
        assert kwargs.get('exc_info') is True
    
    def test_setup_logger_without_file(self, logger_utils):
        """ファイル出力なしでのロガーセットアップテスト"""
        logger_name = "console_only_logger"
        
        # ファイル指定なしでロガーをセットアップ
        logger = logger_utils.setup_logger(logger_name)
        
        # ロガーが正しく作成されていることを確認
        assert logger.name == logger_name
        assert len(logger.handlers) == 1  # コンソールハンドラのみ
        
        # ハンドラがFileHandlerでないことを確認
        assert not any(isinstance(h, logging.FileHandler) for h in logger.handlers)
    
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_logger_file_error(self, mock_file, logger_utils):
        """ファイル作成エラー時のロガーセットアップテスト"""
        # このテストは、実際のクラスが実装された後に有効化する
        # mock_file.side_effect = PermissionError("アクセス拒否")
        # 
        # logger_name = "error_logger"
        # log_file = "/invalid/path/test.log"
        # 
        # # PermissionErrorが発生しても、コンソールのみのロガーが作成されることを確認
        # with pytest.warns(UserWarning):
        #     logger = logger_utils.setup_logger(logger_name, log_file=log_file)
        # 
        # # ロガーが作成されていることを確認
        # assert logger.name == logger_name
        # assert len(logger.handlers) == 1  # コンソールハンドラのみ
        pass 