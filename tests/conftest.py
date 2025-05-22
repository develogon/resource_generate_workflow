import os
import pytest
from unittest.mock import MagicMock, patch

# テスト対象のルートディレクトリパスを取得
@pytest.fixture
def root_dir():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# テストデータディレクトリのパスを取得
@pytest.fixture
def fixtures_dir(root_dir):
    return os.path.join(root_dir, "tests", "fixtures")

# テスト用のMarkdownコンテンツ
@pytest.fixture
def sample_markdown():
    return """# メインタイトル

## チャプター1
これはチャプター1の内容です。

### セクション1.1
セクション1.1の内容です。

### セクション1.2
セクション1.2の内容です。

## チャプター2
これはチャプター2の内容です。

### セクション2.1
セクション2.1の内容です。
"""

# モックClaudeAPIクライアント
@pytest.fixture
def mock_claude_client():
    mock = MagicMock()
    mock.call_api.return_value = {
        "content": [
            {
                "type": "text",
                "text": "# 記事タイトル\n\nこれは生成された記事の内容です。"
            }
        ]
    }
    return mock

# モックOpenAIクライアント
@pytest.fixture
def mock_openai_client():
    mock = MagicMock()
    mock.optimize_template.return_value = "最適化されたYAMLテンプレート"
    mock.generate_image.return_value = b"dummy_image_bytes"
    return mock

# モックGitHubクライアント
@pytest.fixture
def mock_github_client():
    mock = MagicMock()
    mock.push_file.return_value = "https://github.com/example/repo/commit/abc123"
    return mock

# モックS3クライアント
@pytest.fixture
def mock_s3_client():
    mock = MagicMock()
    mock.upload_file.return_value = "dummy_s3_key"
    mock.get_public_url.return_value = "https://example-bucket.s3.amazonaws.com/dummy_s3_key"
    return mock

# モックSlackクライアント
@pytest.fixture
def mock_slack_client():
    mock = MagicMock()
    return mock

# サンプルチェックポイントデータ
@pytest.fixture
def sample_checkpoint_data():
    return {
        "id": "checkpoint-001",
        "timestamp": "2023-01-01T12:00:00",
        "state": {
            "current_chapter": "1",
            "current_section": "2",
            "processing_stage": "ARTICLE_GENERATION"
        },
        "completed_tasks": ["task-001", "task-002"],
        "pending_tasks": ["task-003", "task-004"]
    }

# サンプルタスクデータ
@pytest.fixture
def sample_task_data():
    return {
        "id": "task-001",
        "type": "API_CALL",
        "status": "PENDING",
        "dependencies": [],
        "retry_count": 0,
        "params": {
            "api_type": "claude",
            "prompt": "テストプロンプト"
        }
    }

# サンプル構造化データ
@pytest.fixture
def sample_structure_data():
    """テスト用のサンプル構造データを提供する"""
    return {
        "title": "Pythonによる自動化入門",
        "sections": [
            {
                "title": "Pythonの基本",
                "content": "Pythonの基本的な構文と概念について説明します。"
            },
            {
                "title": "ファイル操作",
                "content": "Pythonでのファイル読み書きと操作方法について説明します。"
            },
            {
                "title": "自動化スクリプト作成",
                "content": "実用的な自動化スクリプトの作成方法を解説します。"
            }
        ],
        "style": "技術解説記事",
        "target_audience": "初心者向け"
    } 