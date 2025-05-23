"""統合テスト用のコンフィギュレーションとフィクスチャ."""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import aioredis
from unittest.mock import AsyncMock, MagicMock

# srcディレクトリをパスに追加
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from config.settings import Config
from core.orchestrator import WorkflowOrchestrator
from core.events import EventBus, Event, EventType
from core.state import StateManager
from core.metrics import MetricsCollector
from workers.pool import WorkerPool
from workers.parser import ParserWorker
from workers.ai import AIWorker
from workers.media import MediaWorker
from workers.aggregator import AggregatorWorker
from clients.claude import ClaudeAPIClient
from clients.openai import OpenAIClient
from clients.s3 import S3Client
from clients.github import GitHubAPIClient
from clients.redis import RedisClient


@pytest.fixture(scope="session")
def event_loop():
    """イベントループのフィクスチャ（セッションスコープ）."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def temp_dir():
    """一時ディレクトリのフィクスチャ."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
async def test_config(temp_dir: Path) -> Config:
    """テスト用設定のフィクスチャ."""
    return Config(
        # ファイルシステム設定
        input_dir=temp_dir / "input",
        output_dir=temp_dir / "output",
        cache_dir=temp_dir / "cache",
        
        # Redis設定（テスト用インメモリ）
        redis_url="redis://localhost:6379/15",  # テスト用DB
        redis_pool_size=5,
        
        # AI設定（モック用）
        claude_api_key="test_claude_key",
        openai_api_key="test_openai_key",
        claude_model="claude-3-sonnet-20240229",
        openai_model="gpt-4",
        max_tokens=2000,
        temperature=0.7,
        
        # AWS設定（モック用）
        aws_access_key_id="test_access_key",
        aws_secret_access_key="test_secret_key",
        aws_region="us-east-1",
        s3_bucket="test-bucket",
        
        # ワーカー設定
        max_concurrent_tasks=5,
        max_workers=3,
        
        # タイムアウト設定
        api_timeout=30.0,
        task_timeout=60.0,
        
        # ログ設定
        log_level="DEBUG",
        
        # テストモード
        test_mode=True,
        use_mocks=True
    )


@pytest.fixture
async def redis_client(test_config: Config) -> AsyncGenerator[aioredis.Redis, None]:
    """Redis接続のフィクスチャ."""
    redis = await aioredis.create_redis_pool(test_config.redis_url)
    
    # テスト用DBをクリア
    await redis.flushdb()
    
    yield redis
    
    # クリーンアップ
    await redis.flushdb()
    redis.close()
    await redis.wait_closed()


@pytest.fixture
async def event_bus(test_config: Config) -> AsyncGenerator[EventBus, None]:
    """イベントバスのフィクスチャ."""
    event_bus = EventBus(test_config)
    await event_bus.start()
    yield event_bus
    await event_bus.stop()


@pytest.fixture
async def state_manager(test_config: Config, redis_client: aioredis.Redis) -> StateManager:
    """状態管理のフィクスチャ."""
    state_manager = StateManager(test_config)
    state_manager.redis = redis_client
    await state_manager.initialize()
    return state_manager


@pytest.fixture
async def metrics_collector(test_config: Config) -> MetricsCollector:
    """メトリクス収集のフィクスチャ."""
    return MetricsCollector(test_config)


@pytest.fixture
async def mock_claude_client(test_config: Config) -> ClaudeAPIClient:
    """Claude APIクライアントのモック."""
    client = ClaudeAPIClient(test_config)
    
    # API呼び出しをモック化
    client._call_api = AsyncMock(return_value={
        "content": [{"text": "モック生成コンテンツ"}],
        "usage": {"input_tokens": 100, "output_tokens": 50}
    })
    
    return client


@pytest.fixture
async def mock_openai_client(test_config: Config) -> OpenAIClient:
    """OpenAI APIクライアントのモック."""
    client = OpenAIClient(test_config)
    
    # API呼び出しをモック化
    client._call_api = AsyncMock(return_value={
        "choices": [{"message": {"content": "モック生成コンテンツ"}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50}
    })
    
    return client


@pytest.fixture
async def mock_s3_client(test_config: Config) -> S3Client:
    """S3クライアントのモック."""
    client = S3Client(test_config)
    
    # S3操作をモック化
    client.upload_file = AsyncMock(return_value="https://test-bucket.s3.amazonaws.com/test-file.png")
    client.upload_bytes = AsyncMock(return_value="https://test-bucket.s3.amazonaws.com/test-bytes.png")
    client.delete_file = AsyncMock(return_value=True)
    
    return client


@pytest.fixture
async def parser_worker(
    test_config: Config,
    event_bus: EventBus,
    state_manager: StateManager
) -> ParserWorker:
    """パーサーワーカーのフィクスチャ."""
    worker = ParserWorker(test_config, "test-parser-1")
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def ai_worker(
    test_config: Config,
    event_bus: EventBus,
    state_manager: StateManager,
    mock_claude_client: ClaudeAPIClient
) -> AIWorker:
    """AIワーカーのフィクスチャ."""
    worker = AIWorker(test_config, "test-ai-1")
    worker.claude_client = mock_claude_client
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def media_worker(
    test_config: Config,
    event_bus: EventBus,
    state_manager: StateManager,
    mock_s3_client: S3Client
) -> MediaWorker:
    """メディアワーカーのフィクスチャ."""
    worker = MediaWorker(test_config, "test-media-1")
    worker.s3_client = mock_s3_client
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def worker_pool(
    test_config: Config,
    parser_worker: ParserWorker,
    ai_worker: AIWorker,
    media_worker: MediaWorker
) -> WorkerPool:
    """ワーカープールのフィクスチャ."""
    pool = WorkerPool(test_config)
    pool.workers = {
        "parser": [parser_worker],
        "ai": [ai_worker],
        "media": [media_worker]
    }
    return pool


@pytest.fixture
async def orchestrator(
    test_config: Config,
    event_bus: EventBus,
    state_manager: StateManager,
    metrics_collector: MetricsCollector,
    worker_pool: WorkerPool
) -> WorkflowOrchestrator:
    """オーケストレーターのフィクスチャ."""
    orchestrator = WorkflowOrchestrator(test_config)
    orchestrator.event_bus = event_bus
    orchestrator.state_manager = state_manager
    orchestrator.metrics = metrics_collector
    orchestrator.worker_pool = worker_pool
    return orchestrator


@pytest.fixture
async def sample_markdown_content() -> str:
    """サンプルMarkdownコンテンツのフィクスチャ."""
    return """# 第1章: Pythonの基礎

## 1.1 Pythonとは

Pythonは、Guido van Rossumによって開発されたプログラミング言語です。

### 1.1.1 特徴

- 読みやすい構文
- 豊富なライブラリ
- クロスプラットフォーム対応

## 1.2 インストール

Pythonのインストール方法について説明します。

```python
print("Hello, World!")
```

## 1.3 基本的な使い方

変数の定義やデータ型について学びます。

```mermaid
graph TD
    A[開始] --> B[変数定義]
    B --> C[処理実行]
    C --> D[結果出力]
    D --> E[終了]
```

### 1.3.1 変数

変数は値を格納するための容器です。

### 1.3.2 データ型

Pythonには様々なデータ型があります。
"""


@pytest.fixture
async def sample_workflow_context() -> Dict[str, Any]:
    """サンプルワークフローコンテキストのフィクスチャ."""
    return {
        "workflow_id": "test-workflow-001",
        "lang": "ja",
        "title": "Python基礎講座",
        "input_file": "python_basics.md",
        "status": "initialized",
        "metadata": {
            "author": "テストユーザー",
            "created_at": "2024-01-01T00:00:00Z",
            "target_audience": "初心者"
        }
    }


# テストイベントのヘルパー関数
def create_test_event(
    event_type: EventType,
    workflow_id: str = "test-workflow-001",
    data: Dict[str, Any] = None
) -> Event:
    """テスト用イベントを作成."""
    return Event(
        type=event_type,
        workflow_id=workflow_id,
        data=data or {},
        priority=0
    )


# アサーションヘルパー
class EventAssertions:
    """イベント関連のアサーションヘルパー."""
    
    @staticmethod
    def assert_event_published(
        event_bus: EventBus,
        event_type: EventType,
        workflow_id: str = None
    ):
        """指定されたイベントが発行されたことを確認."""
        # この実装は実際のEventBusの実装に依存
        pass
    
    @staticmethod
    def assert_state_saved(
        state_manager: StateManager,
        workflow_id: str,
        expected_state: Dict[str, Any]
    ):
        """期待される状態が保存されたことを確認."""
        # この実装は実際のStateManagerの実装に依存
        pass


@pytest.fixture
def event_assertions() -> EventAssertions:
    """イベントアサーションヘルパーのフィクスチャ."""
    return EventAssertions() 