import os
import sys
import pytest
from unittest.mock import MagicMock

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_claude_service():
    """
    Claude APIサービスのモック
    """
    mock = MagicMock()
    # デフォルトの戻り値を設定
    mock.generate_content.return_value = {
        "content": "# テスト返答\n\nこれはClaudeのモック返答です。\n\n```yaml\nkey: value\n```"
    }
    return mock

@pytest.fixture
def mock_github_service():
    """
    GitHub APIサービスのモック
    """
    mock = MagicMock()
    mock.push_file.return_value = True
    return mock

@pytest.fixture
def mock_storage_service():
    """
    ストレージサービス(S3)のモック
    """
    mock = MagicMock()
    mock.upload_file.return_value = "https://example.com/test-image.png"
    return mock

@pytest.fixture
def mock_notifier_service():
    """
    通知サービス(Slack)のモック
    """
    mock = MagicMock()
    return mock

@pytest.fixture
def sample_markdown_content():
    """
    テスト用のマークダウンコンテンツ
    """
    return """# テストタイトル

## 第1章 はじめに

### 1.1 基礎知識

このテキストは基礎知識についての説明です。

```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```

### 1.2 応用知識

このテキストは応用知識についての説明です。

## 第2章 実践

### 2.1 実装例

以下は実装例です。

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
```
"""

@pytest.fixture
def sample_yaml_content():
    """
    テスト用のYAMLコンテンツ (section_structure.ymlの構造に準拠)
    """
    return """
title: "テストタイトル"
chapters:
  - id: "01"
    title: "第1章 はじめに"
    sections:
      - id: "01"
        title: "基礎知識"
        learning_objectives:
          - "テスト目標1を理解する"
          - "テスト目標2を習得する"
        paragraphs:
          - type: "introduction_with_foreshadowing"
            order: 1
            content_focus: "基礎知識の紹介"
            original_text: |
              このテキストは基礎知識についての説明です。
            content_sequence:
              - type: "explanation"
                order: 1
                config:
                  style: "introduction"
                  key_points:
                    - "テストポイント1"
                    - "テストポイント2"
                  preserve_elements:
                    - "このテキスト"という表現
              - type: "image"
                order: 2
                config:
                  type: "concept_overview"
                  description: "基礎知識の概要図"
                  slide_structure:
                    - "概要ポイント1"
                    - "概要ポイント2"
          - type: "basic_example"
            order: 2
            content_focus: "応用知識の説明"
            original_text: |
              さらに詳しい説明...
            content_sequence:
              - type: "code"
                order: 1
                config:
                  pattern: "example_code"
                  language: "go"
                  examples:
                    - content: "fmt.Println(\"Hello, World!\")"
                      description: "サンプルコード"
"""

@pytest.fixture
def temp_dir(tmpdir):
    """
    テスト用の一時ディレクトリ
    """
    return tmpdir 