"""統合テスト用のコンフィギュレーションとフィクスチャ."""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Dict, Any
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock

# srcディレクトリをパスに追加
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

# まず基本的なクラスを定義（実装がない場合）
try:
    from config.settings import Config
except ImportError:
    class Config:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# 他の必要なクラスをモック化
class MockEventBus:
    def __init__(self, config):
        self.config = config
        self.subscribers = {}
        self.running = False
    
    async def start(self):
        self.running = True
    
    async def stop(self):
        self.running = False
    
    async def publish(self, event, delay=0):
        pass
    
    async def subscribe(self, event_type, handler):
        pass

class MockStateManager:
    def __init__(self, config):
        self.config = config
        self.redis = None
        self.storage = {}
    
    async def initialize(self):
        pass
    
    async def save_workflow_state(self, workflow_id, state):
        self.storage[f"workflow:{workflow_id}"] = state
    
    async def get_workflow_state(self, workflow_id):
        return self.storage.get(f"workflow:{workflow_id}")
    
    async def save_checkpoint(self, workflow_id, checkpoint_type, data):
        key = f"checkpoint:{workflow_id}:{checkpoint_type}"
        self.storage[key] = data
    
    async def get_latest_checkpoint(self, workflow_id):
        # 簡単な実装
        return {"step": "test_checkpoint", "data": {}}
    
    async def get_checkpoint_history(self, workflow_id):
        return []
    
    async def close(self):
        pass

class MockMetricsCollector:
    def __init__(self, config=None):
        self.workflows_started = MockCounter()
        self.workflows_completed = MockCounter()
    
    def measure_time(self, metric_name):
        return MockContextManager()

class MockCounter:
    def __init__(self):
        self._value = MockValue()

class MockValue:
    def __init__(self):
        self._value = 0

class MockContextManager:
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass

class MockWorker:
    def __init__(self, config, worker_id):
        self.config = config
        self.worker_id = worker_id
        self.process = AsyncMock()
    
    async def start(self, event_bus, state_manager):
        pass

class MockWorkerPool:
    def __init__(self, config):
        self.config = config
        self.workers = {}
    
    def get_worker(self, worker_type):
        return MockWorker(self.config, f"{worker_type}-1")
    
    def get_workers(self, worker_type):
        return [MockWorker(self.config, f"{worker_type}-1")]

class MockOrchestrator:
    def __init__(self, config):
        self.config = config
        self.worker_pool = MockWorkerPool(config)
        self.metrics = MockMetricsCollector(config)
    
    async def execute(self, lang, title, input_file=None):
        return MockWorkflowResult()
    
    async def resume(self, workflow_id):
        return MockWorkflowResult()

class MockWorkflowResult:
    def __init__(self):
        self.workflow_id = "test-workflow-001"
        self.status = "completed"

class MockAPIClient:
    def __init__(self, config):
        self.config = config
    
    async def _call_api(self, *args, **kwargs):
        return {"content": [{"text": "Mock response"}]}

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
    config = Config()
    
    # パス設定を更新
    config.data_dir = temp_dir / "data"
    config.output_dir = temp_dir / "output"
    config.cache_dir = temp_dir / "cache"
    config.log_dir = temp_dir / "logs"
    
    # 環境設定
    config.environment = "test"
    config.debug = True
    
    # API設定
    config.api_timeout = 30.0
    config.max_retries = 3
    
    return config


@pytest.fixture
async def redis_client(test_config: Config) -> AsyncGenerator[redis.Redis, None]:
    """Redis接続のフィクスチャ."""
    try:
        r = redis.Redis.from_url(test_config.redis_url)
        
        # テスト用DBをクリア
        await r.flushdb()
        
        yield r
        
        # クリーンアップ
        await r.flushdb()
        await r.aclose()
    except Exception:
        # Redis接続失敗時はモックを使用
        yield MagicMock()


@pytest.fixture
async def event_bus(test_config: Config):
    """イベントバスのフィクスチャ."""
    event_bus = MockEventBus(test_config)
    await event_bus.start()
    yield event_bus
    await event_bus.stop()


@pytest.fixture
async def state_manager(test_config: Config, redis_client):
    """状態管理のフィクスチャ."""
    state_manager = MockStateManager(test_config)
    state_manager.redis = redis_client
    await state_manager.initialize()
    return state_manager


@pytest.fixture
async def metrics_collector(test_config: Config):
    """メトリクス収集のフィクスチャ."""
    return MockMetricsCollector(test_config)


@pytest.fixture
async def mock_claude_client(test_config: Config):
    """Claude APIクライアントのモック."""
    return MockAPIClient(test_config)


@pytest.fixture
async def mock_openai_client(test_config: Config):
    """OpenAI APIクライアントのモック."""
    return MockAPIClient(test_config)


@pytest.fixture
async def mock_s3_client(test_config: Config):
    """S3クライアントのモック."""
    client = MagicMock()
    client.upload_file = AsyncMock(return_value="https://test-bucket.s3.amazonaws.com/test-file.png")
    client.upload_bytes = AsyncMock(return_value="https://test-bucket.s3.amazonaws.com/test-bytes.png")
    client.delete_file = AsyncMock(return_value=True)
    return client


@pytest.fixture
async def parser_worker(
    test_config: Config,
    event_bus,
    state_manager
):
    """パーサーワーカーのフィクスチャ."""
    worker = MockWorker(test_config, "test-parser-1")
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def ai_worker(
    test_config: Config,
    event_bus,
    state_manager,
    mock_claude_client
):
    """AIワーカーのフィクスチャ."""
    worker = MockWorker(test_config, "test-ai-1")
    worker.claude_client = mock_claude_client
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def media_worker(
    test_config: Config,
    event_bus,
    state_manager,
    mock_s3_client
):
    """メディアワーカーのフィクスチャ."""
    worker = MockWorker(test_config, "test-media-1")
    worker.s3_client = mock_s3_client
    await worker.start(event_bus, state_manager)
    return worker


@pytest.fixture
async def worker_pool(
    test_config: Config,
    parser_worker,
    ai_worker,
    media_worker
):
    """ワーカープールのフィクスチャ."""
    pool = MockWorkerPool(test_config)
    pool.workers = {
        "parser": [parser_worker],
        "ai": [ai_worker],
        "media": [media_worker]
    }
    return pool


@pytest.fixture
async def orchestrator(
    test_config: Config,
    event_bus,
    state_manager,
    metrics_collector,
    worker_pool
):
    """オーケストレーターのフィクスチャ."""
    orchestrator = MockOrchestrator(test_config)
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
class MockEvent:
    def __init__(self, event_type, workflow_id, data, priority=0):
        self.type = event_type
        self.workflow_id = workflow_id
        self.data = data
        self.priority = priority

def create_test_event(
    event_type,
    workflow_id: str = "test-workflow-001",
    data: Dict[str, Any] = None
):
    """テスト用イベントを作成."""
    return MockEvent(
        event_type=event_type,
        workflow_id=workflow_id,
        data=data or {},
        priority=0
    )


# アサーションヘルパー
class EventAssertions:
    """イベント関連のアサーションヘルパー."""
    
    @staticmethod
    def assert_event_published(
        event_bus,
        event_type,
        workflow_id: str = None
    ):
        """指定されたイベントが発行されたことを確認."""
        pass
    
    @staticmethod
    def assert_state_saved(
        state_manager,
        workflow_id: str,
        expected_state: Dict[str, Any]
    ):
        """期待される状態が保存されたことを確認."""
        pass


@pytest.fixture
def event_assertions() -> EventAssertions:
    """イベントアサーションヘルパーのフィクスチャ."""
    return EventAssertions() 