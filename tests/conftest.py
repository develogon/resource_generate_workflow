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
    return {
        "title": "1.1 プログラミングの基本概念",
        "learning_objectives": [
            "変数とデータ型の基本を理解する",
            "条件分岐の仕組みと使い方を習得する",
            "ループ構造による繰り返し処理を理解する",
            "関数の定義と呼び出し方を習得する"
        ],
        "paragraphs": [
            {
                "type": "heading",
                "content": "プログラミングの基本概念について",
                "level": 2,
                "metadata": {
                    "order": 1,
                    "purpose": "introduction",
                    "original_text": "プログラミングを学ぶ上で最初に理解すべき基本的な概念について説明します。これらの概念は全てのプログラミング言語に共通する重要な基礎です。"
                }
            },
            {
                "type": "text",
                "content": "プログラミングを学ぶ上で最初に理解すべき基本的な概念について説明します。これらの概念は全てのプログラミング言語に共通する重要な基礎です。",
                "metadata": {
                    "order": 2,
                    "purpose": "explanation"
                }
            },
            {
                "type": "heading",
                "content": "変数とデータ型",
                "level": 3,
                "metadata": {
                    "order": 3,
                    "purpose": "section_title"
                }
            },
            {
                "type": "text",
                "content": "変数はプログラミングの基本的な要素で、データを一時的に格納するための名前付きのメモリ領域です。",
                "metadata": {
                    "order": 4,
                    "purpose": "explanation"
                }
            },
            {
                "type": "list",
                "items": [
                    "整数型: 1, 2, 3などの整数値を格納",
                    "浮動小数点型: 3.14, 0.5などの小数値を格納",
                    "文字列型: 「こんにちは」などのテキストを格納",
                    "ブール型: TrueまたはFalseの真偽値を格納"
                ],
                "metadata": {
                    "order": 5,
                    "purpose": "enumeration"
                }
            },
            {
                "type": "code",
                "language": "python",
                "content": "# Pythonでの変数の例\nage = 25               # 整数型\nheight = 175.5         # 浮動小数点型\nname = \"山田太郎\"      # 文字列型\nis_student = True      # ブール型",
                "metadata": {
                    "order": 6,
                    "purpose": "example"
                }
            }
        ]
    } 