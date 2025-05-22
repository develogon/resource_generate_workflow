import logging
import os
import warnings


class LoggerUtils:
    """ロギングユーティリティクラス

    ロガーの設定と管理を行うユーティリティクラスです。
    """

    @staticmethod
    def setup_logger(name, log_file=None, level=logging.INFO, format_str=None):
        """ロガーをセットアップする

        Args:
            name (str): ロガー名
            log_file (str, optional): ログファイルパス. デフォルトはNone
            level (int, optional): ログレベル. デフォルトはlogging.INFO
            format_str (str, optional): ログフォーマット. デフォルトはNone

        Returns:
            logging.Logger: セットアップされたロガー
        """
        # ロガーを取得
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
            try:
                # 必要な場合はディレクトリを作成
                os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
                file_handler = logging.FileHandler(log_file)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except (PermissionError, OSError) as e:
                warnings.warn(f"ログファイルの作成に失敗しました: {str(e)}")

        return logger

    @staticmethod
    def get_logger(name):
        """既存のロガーを取得する

        Args:
            name (str): ロガー名

        Returns:
            logging.Logger: 指定された名前のロガー
        """
        return logging.getLogger(name)

    @staticmethod
    def log_exception(logger, exception, context=None):
        """例外をロギングする

        Args:
            logger (logging.Logger): ロガーインスタンス
            exception (Exception): 記録する例外
            context (dict, optional): コンテキスト情報. デフォルトはNone
        """
        error_message = f"例外が発生しました: {str(exception)}"
        
        # コンテキストが存在し、空でない場合のみコンテキスト情報を追加
        if context and len(context) > 0:
            context_str = ", ".join([f"{k}={v}" for k, v in context.items()])
            error_message += f" [コンテキスト: {context_str}]"

        logger.error(error_message, exc_info=True) 