#!/usr/bin/env python3
"""
最小限のアーキテクチャテスト
各コンポーネントの基本動作を段階的に確認
"""

import asyncio
import logging
from pathlib import Path

# コンポーネントの個別インポート
from src.config.settings import Config
from src.core.events import EventBus, Event, EventType
from src.core.state import StateManager
from src.workers.parser import ParserWorker
from src.workers.ai import AIWorker
from src.workers.aggregator import AggregatorWorker

logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

async def test_basic_components():
    """基本コンポーネントのテスト"""
    print("🧪 アーキテクチャの基本コンポーネントテスト")
    
    # 設定作成
    config = Config.from_dict({
        "environment": "test",
        "storage": {"data_dir": "./data", "output_dir": "./output"},
        "redis": {"url": "redis://localhost:6379/9"}
    })
    config.setup_directories()
    
    # イベントバス初期化
    event_bus = EventBus(config)
    state_manager = StateManager(config)
    
    try:
        # 状態管理の初期化
        await state_manager.initialize()
        print("✅ StateManager初期化完了")
        
        # イベントバスの開始
        event_bus_task = asyncio.create_task(event_bus.start())
        await asyncio.sleep(0.1)  # 少し待機
        print("✅ EventBus開始完了")
        
        # ワーカーの作成
        parser_worker = ParserWorker(config, "parser-test")
        ai_worker = AIWorker(config, "ai-test") 
        aggregator_worker = AggregatorWorker(config, "aggregator-test")
        
        # ワーカーの初期化
        await parser_worker.start(event_bus, state_manager)
        await ai_worker.start(event_bus, state_manager)
        await aggregator_worker.start(event_bus, state_manager)
        print("✅ Workers初期化完了")
        
        # テスト用ワークフローIDを生成
        workflow_id = "test-workflow-001"
        
        # ステップ1: ワークフロー開始イベントを発行
        print("\n📤 ワークフロー開始イベント発行")
        start_event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            data={
                "lang": "ja",
                "title": "WebAPIテスト",
                "input_file": "data/input/webapi_basics.md"
            }
        )
        await event_bus.publish(start_event)
        
        # 少し待機してログを確認
        await asyncio.sleep(2)
        print("⏳ 2秒間の処理完了")
        
        # ステップ2: 手動でチャプターイベント発行
        print("\n📤 手動チャプターイベント発行")
        chapter_event = Event(
            type=EventType.CHAPTER_PARSED,
            workflow_id=workflow_id,
            data={
                "index": 0,
                "title": "はじめに",
                "content": "これはテスト用のチャプターです。\n\n## セクション1\n\nテストコンテンツです。",
            }
        )
        await event_bus.publish(chapter_event)
        
        await asyncio.sleep(2)
        print("⏳ チャプター処理完了")
        
        # ステップ3: 集約状況の確認
        print("\n📊 ワークフロー状況確認")
        workflow_status = aggregator_worker.get_workflow_status(workflow_id)
        if workflow_status:
            print(f"📋 ワークフロー状況: {workflow_status}")
        else:
            print("❌ ワークフロー状況が取得できません")
            
        print("✅ 基本コンポーネントテスト完了")
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # クリーンアップ
        event_bus.running = False
        await state_manager.close()
        print("🧹 クリーンアップ完了")

async def test_text_processing():
    """text.mdファイルの実際の処理テスト"""
    print("\n📄 text.md処理テスト")
    
    input_file = Path("data/input/webapi_basics.md")
    if not input_file.exists():
        print(f"❌ 入力ファイルが見つかりません: {input_file}")
        return
        
    # ファイル読み込みテスト
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"📖 ファイル読み込み完了: {len(content)}文字")
    print(f"📝 最初の100文字: {content[:100]}...")
    
    # パーサーワーカーのロジックテスト
    from src.workers.parser import ParserWorker
    config = Config()
    parser = ParserWorker(config, "test-parser")
    
    # チャプター分割テスト
    chapters = parser._split_by_chapters(content)
    print(f"📚 チャプター数: {len(chapters)}")
    
    for i, chapter in enumerate(chapters):
        print(f"  {i+1}. {chapter['title']} ({len(chapter['content'])}文字)")
        
        # セクション分割テスト
        sections = parser._split_by_sections(chapter['content'])
        print(f"     セクション数: {len(sections)}")
        
        for j, section in enumerate(sections[:2]):  # 最初の2つのみ表示
            print(f"     {j+1}. {section['title']} (レベル{section['level']}, {len(section['content'])}文字)")
            
            # パラグラフ分割テスト
            paragraphs = parser._split_by_paragraphs(section['content'])
            print(f"        パラグラフ数: {len(paragraphs)}")

if __name__ == "__main__":
    print("🔬 アーキテクチャ設計書の実装テスト開始\n")
    
    asyncio.run(test_basic_components())
    asyncio.run(test_text_processing()) 