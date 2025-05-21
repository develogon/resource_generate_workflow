import logging
import os
from logging.handlers import RotatingFileHandler


def setup_logging(log_file, level=logging.INFO, max_bytes=10485760, backup_count=5):
    """
    ロギング設定を初期化します。
    
    Parameters
    ----------
    log_file : str
        ログファイルのパス
    level : int, optional
        ロギングレベル (default: logging.INFO)
    max_bytes : int, optional
        ログファイルの最大サイズ (バイト単位、デフォルト: 10MB)
    backup_count : int, optional
        保持するログファイルのバックアップ数 (デフォルト: 5)
        
    Returns
    -------
    logging.Logger
        設定されたロガーインスタンス
    """
    # ログディレクトリを確保
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # ルートロガーを取得
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # 既存のハンドラをクリア
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # ファイルハンドラを追加（ローテーション機能付き）
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=max_bytes, 
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # コンソールハンドラを追加
    console_handler = logging.StreamHandler()
    
    # フォーマッタを設定
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # ハンドラをロガーに追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 