#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""コマンドラインインターフェース (CLI)

このモジュールはリソース生成ワークフローのコマンドラインインターフェースを提供します。
ユーザーはこのCLIを通じてワークフローを開始、再開、監視できます。
"""

import os
import sys
import argparse
import logging
from typing import Dict, List, Optional

from app.config import load_config
from app.workflow.engine import WorkflowEngine

# ロガーの設定
logger = logging.getLogger(__name__)


def setup_logging(log_level: str = "INFO") -> None:
    """
    ロギングの設定

    Args:
        log_level: ログレベル
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    level = log_levels.get(log_level.upper(), logging.INFO)
    logging.basicConfig(level=level, format=log_format)


def parse_args() -> argparse.Namespace:
    """
    コマンドライン引数の解析

    Returns:
        argparse.Namespace: 解析された引数
    """
    parser = argparse.ArgumentParser(
        description="リソース生成ワークフローツール"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="サブコマンド")
    
    # startコマンド
    start_parser = subparsers.add_parser("start", help="新しいワークフローを開始")
    start_parser.add_argument(
        "input_path", 
        help="処理する入力ファイルのパス"
    )
    start_parser.add_argument(
        "--config", 
        help="設定ファイルのパス",
        default=None
    )
    
    # resumeコマンド
    resume_parser = subparsers.add_parser("resume", help="中断されたワークフローを再開")
    resume_parser.add_argument(
        "--checkpoint", 
        help="再開するチェックポイントID（指定がない場合は最新のチェックポイント）",
        default=None
    )
    resume_parser.add_argument(
        "--config", 
        help="設定ファイルのパス",
        default=None
    )
    
    # statusコマンド
    status_parser = subparsers.add_parser("status", help="ワークフローの状態を確認")
    
    # 共通オプション
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="ログレベルを設定"
    )
    
    return parser.parse_args()


def main() -> int:
    """
    メインエントリーポイント

    Returns:
        int: 終了コード（0:成功, 1:失敗）
    """
    # 引数の解析
    args = parse_args()
    
    # ロギングの設定
    setup_logging(args.log_level)
    
    try:
        logger.debug(f"コマンドライン引数: {args}")
        
        # 設定の読み込み
        config = load_config(args.config if hasattr(args, "config") else None)
        
        # ワークフローエンジンの初期化
        engine = WorkflowEngine(config)
        
        if args.command == "start":
            # 新しいワークフローを開始
            logger.info(f"ワークフロー開始: {args.input_path}")
            
            # 入力ファイルパスの絶対パス変換
            input_path = os.path.abspath(args.input_path)
            
            # ワークフロー実行
            result = engine.start(input_path)
            if not result:
                logger.error("ワークフローの実行に失敗しました")
                return 1
            
        elif args.command == "resume":
            # 中断されたワークフローを再開
            logger.info(f"ワークフロー再開: {args.checkpoint or '最新のチェックポイント'}")
            
            # ワークフロー再開
            result = engine.resume(args.checkpoint)
            if not result:
                logger.error("ワークフローの再開に失敗しました")
                return 1
            
        elif args.command == "status":
            # ワークフローの状態を確認
            logger.info("ワークフローの状態確認")
            # TODO: 状態確認機能の実装
            print("状態確認機能は現在実装中です。")
            
        else:
            logger.error(f"不明なコマンド: {args.command}")
            return 1
        
        logger.info("コマンド実行が完了しました")
        return 0
        
    except Exception as e:
        logger.exception(f"予期せぬエラーが発生しました: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 