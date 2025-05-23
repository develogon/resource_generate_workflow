#!/usr/bin/env python3
"""
簡単なワークフローテスト
アーキテクチャ設計の基本的な動作を確認
"""

import asyncio
import logging
from pathlib import Path

# 相対インポート
from src.config.settings import Config
from src.core.orchestrator import WorkflowOrchestrator

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def simple_test():
    """簡単なワークフローテスト"""
    print("🚀 アーキテクチャ設計書に基づくワークフローテスト開始")
    
    # 設定の作成
    config = Config.from_dict({
        "environment": "test",
        "debug": True,
        "max_concurrent_tasks": 2,
        "workers": {
            "max_concurrent_tasks": 2,
            "counts": {
                "parser": 1,
                "ai": 1,
                "media": 1,
                "aggregator": 1
            }
        },
        "api": {
            "claude_api_key": "test_key",
            "timeout": 5.0
        },
        "storage": {
            "data_dir": "./data",
            "output_dir": "./output"
        },
        "redis": {
            "url": "redis://localhost:6379/9"  # テスト用DB
        }
    })
    
    # 必要なディレクトリを作成
    config.setup_directories()
    
    # オーケストレーターの作成
    orchestrator = WorkflowOrchestrator(config)
    
    try:
        print("📁 入力ファイル確認...")
        input_file = Path("data/input/webapi_basics.md")
        if not input_file.exists():
            print(f"❌ 入力ファイルが見つかりません: {input_file}")
            return
            
        print(f"✅ 入力ファイル確認完了: {input_file}")
        
        print("🔧 ワークフロー実行...")
        
        # タイムアウト付きでワークフロー実行
        context = await asyncio.wait_for(
            orchestrator.execute(
                lang="ja",
                title="WebAPIの基本とGOでの実装例",
                input_file=str(input_file)
            ),
            timeout=30.0  # 30秒でタイムアウト
        )
        
        print(f"✅ ワークフロー完了: {context.workflow_id}")
        print(f"📊 ステータス: {context.status}")
        
        # 結果の確認
        output_dir = Path(config.storage.output_dir)
        if output_dir.exists():
            output_files = list(output_dir.glob("**/*"))
            print(f"📁 生成されたファイル数: {len(output_files)}")
            for file in output_files[:5]:  # 最初の5つを表示
                print(f"  - {file}")
        else:
            print("⚠️  出力ディレクトリが作成されていません")
            
    except asyncio.TimeoutError:
        print("⏰ ワークフローがタイムアウトしました（30秒）")
        print("🔍 現在の進行状況を確認...")
        
        # 進行状況を表示
        active_workflows = orchestrator.get_active_workflows()
        for workflow in active_workflows:
            print(f"  ワークフロー: {workflow.workflow_id}")
            print(f"  ステータス: {workflow.status}")
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        
    finally:
        print("🛑 オーケストレーター停止中...")
        await orchestrator.shutdown()
        print("✅ テスト完了")

if __name__ == "__main__":
    asyncio.run(simple_test()) 