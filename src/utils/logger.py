"""ログシステム."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import structlog

from ..config.constants import DEFAULT_LOG_FORMAT, DEFAULT_LOG_LEVEL


def setup_logging(
    level: str = DEFAULT_LOG_LEVEL,
    format_string: str = DEFAULT_LOG_FORMAT,
    log_file: Optional[Path] = None,
    json_logs: bool = False,
    correlation_id_key: str = "correlation_id"
) -> None:
    """ログシステムのセットアップ."""
    
    # ログレベルの設定
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # ハンドラーの設定
    handlers = []
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if json_logs:
        # JSON形式でのログ出力
        console_formatter = logging.Formatter('%(message)s')
    else:
        # 標準形式でのログ出力
        console_formatter = logging.Formatter(format_string)
    
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # ファイルハンドラー（指定された場合）
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        
        if json_logs:
            file_formatter = logging.Formatter('%(message)s')
        else:
            file_formatter = logging.Formatter(format_string)
        
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # 基本ログ設定
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )
    
    # structlogの設定
    if json_logs:
        # JSON形式の場合
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # 開発者向け形式の場合
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
    
    # correlation_idの処理
    def add_correlation_id(logger, method_name, event_dict):
        """correlation_idをログに追加."""
        correlation_id = structlog.contextvars.get_contextvars().get(correlation_id_key)
        if correlation_id:
            event_dict[correlation_id_key] = correlation_id
        return event_dict
    
    processors.insert(-1, add_correlation_id)
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """ロガーを取得."""
    return structlog.get_logger(name)


class LogContext:
    """ログコンテキスト管理."""
    
    def __init__(self, **kwargs) -> None:
        """初期化."""
        self.context = kwargs
        self.token = None
    
    def __enter__(self) -> LogContext:
        """コンテキストマネージャーの開始."""
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャーの終了."""
        if self.token:
            structlog.contextvars.unbind_contextvars(self.token)


def log_function_call(logger: structlog.BoundLogger):
    """関数呼び出しをログに記録するデコレータ."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                "Function called",
                function=func_name,
                args=len(args),
                kwargs=list(kwargs.keys())
            )
            
            try:
                result = func(*args, **kwargs)
                logger.debug(
                    "Function completed",
                    function=func_name,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    "Function failed",
                    function=func_name,
                    error=str(e),
                    exception_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


def log_async_function_call(logger: structlog.BoundLogger):
    """非同期関数呼び出しをログに記録するデコレータ."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.debug(
                "Async function called",
                function=func_name,
                args=len(args),
                kwargs=list(kwargs.keys())
            )
            
            try:
                result = await func(*args, **kwargs)
                logger.debug(
                    "Async function completed",
                    function=func_name,
                    success=True
                )
                return result
            except Exception as e:
                logger.error(
                    "Async function failed",
                    function=func_name,
                    error=str(e),
                    exception_type=type(e).__name__
                )
                raise
        
        return wrapper
    return decorator


class PerformanceLogger:
    """パフォーマンスログ記録."""
    
    def __init__(self, logger: structlog.BoundLogger, operation: str):
        """初期化."""
        self.logger = logger
        self.operation = operation
        self.start_time = None
    
    def __enter__(self) -> PerformanceLogger:
        """コンテキストマネージャーの開始."""
        import time
        self.start_time = time.perf_counter()
        self.logger.info("Operation started", operation=self.operation)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """コンテキストマネージャーの終了."""
        import time
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            
            if exc_type:
                self.logger.error(
                    "Operation failed",
                    operation=self.operation,
                    duration_seconds=round(duration, 4),
                    error=str(exc_val),
                    exception_type=exc_type.__name__
                )
            else:
                self.logger.info(
                    "Operation completed",
                    operation=self.operation,
                    duration_seconds=round(duration, 4)
                )


def sanitize_log_data(data: dict) -> dict:
    """ログデータからセンシティブな情報を除去."""
    sensitive_keys = {
        'password', 'passwd', 'pwd',
        'token', 'api_key', 'secret', 'key',
        'auth', 'authorization', 'credential',
        'private_key', 'access_token', 'refresh_token'
    }
    
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        
        # センシティブなキーの場合は値をマスク
        if any(sensitive in key_lower for sensitive in sensitive_keys):
            if isinstance(value, str) and len(value) > 0:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = "***REDACTED***"
        # 辞書の場合は再帰的に処理
        elif isinstance(value, dict):
            sanitized[key] = sanitize_log_data(value)
        # リストの場合は要素をチェック
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_log_data(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized 