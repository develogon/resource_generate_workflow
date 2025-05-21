#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from typing import Dict, Any, Optional

from config.settings import load_config
from core.processor import ContentProcessor
from core.state_manager import StateManager
from services.claude import ClaudeService
from services.github import GitHubService
from services.storage import StorageService
from services.notifier import NotifierService
from core.file_manager import FileManager
from utils.logging import setup_logger

logger = setup_logger(__name__)

def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析する"""
    parser = argparse.ArgumentParser(description='オライリーコンテンツ変換ワークフロー')
    parser.add_argument('--title', type=str, required=True, help='処理対象のタイトル名')
    parser.add_argument('--lang', type=str, default='go', help='プログラミング言語（デフォルト: go）')
    parser.add_argument('--input_path', type=str, help='入力ファイルのパス（指定しない場合は自動検出）')
    parser.add_argument('--resume', type=str, help='指定したチェックポイントから処理を再開')
    parser.add_argument('--verbose', '-v', action='store_true', help='詳細なログ出力を有効化')
    return parser.parse_args()

def main():
    """メイン処理フロー"""
    # 引数解析
    args = parse_arguments()
    
    # 設定読み込み
    config = load_config()
    
    # ロギングレベル設定
    if args.verbose:
        from utils.logging import set_verbose
        set_verbose()
    
    # ファイル管理
    file_manager = FileManager()
    
    # 状態管理
    state_manager = StateManager()
    
    # 前回のチェックポイントがあれば状態復元の提案
    if not args.resume:
        checkpoints = state_manager.list_checkpoints_for_title(args.title)
        if checkpoints:
            print(f"{len(checkpoints)}個のチェックポイントが見つかりました。再開する場合は --resume オプションを指定してください。")
            for idx, cp in enumerate(checkpoints):
                print(f"  {idx}: {cp.timestamp} - {cp.description}")
            return
    
    # サービスインスタンス化
    claude_service = ClaudeService(config)
    github_service = GitHubService(config)
    storage_service = StorageService(config)
    notifier = NotifierService(config)
    
    # メイン処理実行
    processor = None
    try:
        # 処理状態の復元または新規作成
        if args.resume:
            processor = state_manager.resume_process(args.resume)
            notifier.send_progress(f"{args.title}の処理を再開します。", processor.progress_percentage)
        else:
            # 入力パスの自動検出（未指定の場合）
            input_path = args.input_path
            if not input_path:
                input_path = f"til/{args.lang}/{args.title}/text.md"
                if not os.path.exists(input_path):
                    logger.error(f"入力ファイルが見つかりません: {input_path}")
                    notifier.send_error(f"入力ファイルが見つかりません: {input_path}")
                    return 1
            
            # 原稿読み込み
            logger.info(f"入力ファイル {input_path} を読み込みます")
            content = file_manager.read_content(input_path)
            
            # プロセッサ作成
            processor = ContentProcessor(
                content=content, 
                args=args, 
                file_manager=file_manager, 
                claude_service=claude_service,
                github_service=github_service, 
                storage_service=storage_service, 
                state_manager=state_manager
            )
        
        # 処理開始
        processor.process()
        
        # 完了通知
        notifier.send_success(f"{args.title}の処理が完了しました")
        return 0
        
    except Exception as e:
        logger.exception(f"処理中にエラーが発生しました: {str(e)}")
        
        # エラー発生時はチェックポイントを自動作成（プロセッサが初期化されている場合）
        checkpoint_id = None
        if processor:
            checkpoint_id = processor.save_checkpoint()
            resume_msg = f"チェックポイント {checkpoint_id} が作成されました。--resume {checkpoint_id} で再開できます。"
        else:
            resume_msg = "プロセッサの初期化に失敗したため、チェックポイントは作成されませんでした。"
        
        # エラー通知
        notifier.send_error(f"エラー発生: {str(e)}", resume_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 