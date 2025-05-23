"""E2Eテスト用フィクスチャ"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock
import asyncio

@pytest.fixture(scope="session")
def e2e_test_dir():
    """E2Eテスト用一時ディレクトリ"""
    temp_dir = tempfile.mkdtemp(prefix="e2e_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_markdown_file(e2e_test_dir):
    """サンプルMarkdownファイル"""
    content = """# 第1章: システム概要

## 1.1 システムの目的

このシステムは、技術書籍のMarkdownコンテンツから多様な派生コンテンツを自動生成する高性能ワークフローエンジンです。

主要機能:
- 階層的コンテンツ分割（Chapter → Section → Paragraph）
- AI駆動のコンテンツ生成（記事、台本、ツイート、説明文）
- 自動画像処理とクラウドストレージ連携
- 堅牢なエラー処理と自動復旧

## 1.2 アーキテクチャ概要

システムは以下の主要コンポーネントで構成されています：

### オーケストレーター
- ワークフロー全体の制御
- イベント駆動による処理制御
- 状態管理とリカバリー

### ワーカープール
- パーサーワーカー：コンテンツ解析
- AIワーカー：コンテンツ生成
- メディアワーカー：画像処理
- 集約ワーカー：結果のまとめ

# 第2章: 実装詳細

## 2.1 パーサーワーカー

パーサーワーカーは階層的なコンテンツ分割を担当します。

### 主要機能
- Markdownの構造解析
- チャプター、セクション、パラグラフへの分割
- メタデータの抽出

## 2.2 AIワーカー

AIワーカーはコンテンツ生成を担当します。

### 生成タイプ
- 記事：技術記事形式
- 台本：プレゼンテーション用
- ツイート：SNS投稿用
- 説明文：概要説明
"""
    
    file_path = e2e_test_dir / "sample_book.md"
    file_path.write_text(content, encoding='utf-8')
    return file_path

@pytest.fixture
def mock_api_responses():
    """APIレスポンスのモック"""
    return {
        "claude": {
            "structure_analysis": {
                "content": [{
                    "text": '''```json
{
  "sections": [
    {
      "title": "システムの目的",
      "key_points": ["技術書籍処理", "自動生成", "高性能"],
      "content_type": "overview"
    },
    {
      "title": "アーキテクチャ概要",
      "key_points": ["オーケストレーター", "ワーカープール", "イベント駆動"],
      "content_type": "technical"
    }
  ]
}
```'''
                }]
            },
            "article_generation": {
                "content": [{
                    "text": "# 技術記事：システム概要\n\n技術書籍のMarkdownコンテンツから多様なコンテンツを自動生成するシステムについて解説します。\n\n## 主要な特徴\n\n1. **階層的コンテンツ分割**\n   - Chapter → Section → Paragraph の構造で分析\n   \n2. **AI駆動の生成**\n   - 記事、台本、ツイート等の多様な形式\n   \n3. **自動画像処理**\n   - クラウドストレージとの連携\n\n## まとめ\n\nこのシステムにより、効率的なコンテンツ生成が可能になります。"
                }]
            },
            "script_generation": {
                "content": [{
                    "text": "# プレゼンテーション台本\n\n## スライド1: タイトル\n「技術書籍コンテンツ自動生成システム」\n\n## スライド2: システム概要\n皆さん、こんにちは。今日は技術書籍から多様なコンテンツを自動生成するシステムについてお話しします。\n\n## スライド3: 主要機能\nこのシステムの主要機能は3つあります：\n1. 階層的コンテンツ分割\n2. AI駆動のコンテンツ生成\n3. 自動画像処理\n\n## スライド4: まとめ\nこのシステムにより、コンテンツ生成が大幅に効率化されます。"
                }]
            }
        }
    }

@pytest.fixture
def mock_s3_client():
    """モックS3クライアント"""
    client = AsyncMock()
    client.upload.return_value = "https://example-bucket.s3.amazonaws.com/test-image.png"
    return client

@pytest.fixture
def e2e_config(e2e_test_dir, mock_s3_client):
    """E2Eテスト用設定"""
    from types import SimpleNamespace
    
    config = SimpleNamespace()
    
    # パス設定
    config.data_dir = e2e_test_dir / "data"
    config.output_dir = e2e_test_dir / "output"
    config.cache_dir = e2e_test_dir / "cache"
    config.log_dir = e2e_test_dir / "logs"
    
    # 必要なディレクトリを作成
    for dir_path in [config.data_dir, config.output_dir, config.cache_dir, config.log_dir]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # ワーカー設定
    config.workers = SimpleNamespace()
    config.workers.max_concurrent_tasks = 3
    config.workers.parser_count = 2
    config.workers.ai_count = 2
    config.workers.media_count = 1
    
    # API設定（テスト用）
    config.claude_api_key = "test-claude-key"
    config.openai_api_key = "test-openai-key"
    config.api_timeout = 30.0
    config.max_retries = 2
    
    # S3設定（モック）
    config.s3_bucket = "test-bucket"
    config.s3_region = "us-east-1"
    
    # その他設定
    config.environment = "test"
    config.debug = True
    config.test_mode = True
    
    return config

@pytest.fixture
async def e2e_event_bus(e2e_config):
    """E2Eテスト用イベントバス"""
    from tests.integration.conftest import MockEventBus
    bus = MockEventBus(e2e_config)
    await bus.start()
    yield bus
    await bus.stop()

@pytest.fixture
async def e2e_state_manager(e2e_config):
    """E2Eテスト用状態管理"""
    from tests.integration.conftest import MockStateManager
    manager = MockStateManager(e2e_config)
    await manager.initialize()
    yield manager
    await manager.close()

@pytest.fixture
def mock_claude_client_e2e(mock_api_responses):
    """E2E用モックClaudeクライアント"""
    client = AsyncMock()
    
    def get_response(prompt, **kwargs):
        if "構造解析" in prompt or "structure" in prompt.lower():
            return mock_api_responses["claude"]["structure_analysis"]
        elif "記事" in prompt or "article" in prompt.lower():
            return mock_api_responses["claude"]["article_generation"]
        elif "台本" in prompt or "script" in prompt.lower():
            return mock_api_responses["claude"]["script_generation"]
        else:
            return {"content": [{"text": "モック応答"}]}
    
    client.generate.side_effect = get_response
    return client

@pytest.fixture
def mock_workflow_metrics():
    """ワークフローメトリクスのモック"""
    metrics = Mock()
    metrics.workflows_started = Mock()
    metrics.workflows_completed = Mock()
    metrics.workflows_failed = Mock()
    metrics.total_processing_time = 0
    metrics.measure_time.return_value.__enter__ = Mock()
    metrics.measure_time.return_value.__exit__ = Mock()
    return metrics 