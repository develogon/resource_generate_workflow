# リソース生成ワークフロー

## 概要

リソース生成ワークフローは、Markdown形式のテキストコンテンツを入力として、以下の処理を行うCLIツールです：

- コンテンツを章（Chapter）とセクション（Section）に分割
- Claude APIを使用して各セクションの構造を解析
- 記事（Article）、台本（Script）、ツイート（Tweets）などの派生コンテンツを生成
- 画像処理（SVG、DrawIO XML、Mermaid図の変換と最適化）
- OpenAI APIを使用したサムネイル画像の生成
- 生成したリソースをGitHubにコミットしS3にアップロード
- 処理の各段階でチェックポイントを保存し、中断時に再開可能な設計

バッチ処理や自動化パイプラインでの利用に適しています。

## インストール

### 前提条件

- Python 3.10以上
- Node.js（Mermaid図のレンダリング用）
- Draw.io CLI（XML図の変換用）

### インストール手順

```bash
# リポジトリのクローン
git clone https://github.com/develogon/resource_generate_workflow.git
cd resource_generate_workflow

# 依存パッケージのインストール
pip install -r requirements.txt

# Node.jsパッケージのインストール（Mermaid用）
npm install -g @mermaid-js/mermaid-cli
```

## 使い方

### 基本コマンド

```bash
# 新しいワークフローを開始
python -m app.cli start path/to/input.md [--config path/to/config.yaml] [--log-level INFO]

# 中断されたワークフローを再開
python -m app.cli resume [--checkpoint checkpoint_id] [--config path/to/config.yaml] [--log-level INFO]

# ワークフローの状態を確認
python -m app.cli status [--log-level INFO]
```

### オプション

- `--config`: 設定ファイル（YAML/JSON）のパスを指定します。指定がない場合は、デフォルトの場所から設定を読み込みます。
- `--log-level`: ログレベルを指定します（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルトはINFOです。
- `--checkpoint`: 再開するチェックポイントIDを指定します。指定がない場合は最新のチェックポイントから再開します。

## 設定

システムの設定は `app/config.py` モジュールで管理され、以下の3つの方法で読み込まれます：

1. デフォルト設定（`config.default.yaml`）
2. ユーザー設定ファイル（YAML/JSON形式）
3. 環境変数（最優先）

設定ファイルは以下の場所から自動的に検索されます：
- カレントディレクトリの `config.yaml` または `config.yml`
- カレントディレクトリの `config.json`
- ホームディレクトリの `~/.resource-workflow/config.yaml`
- ホームディレクトリの `~/.resource-workflow/config.json`

### 設定ファイル例

```yaml
# 基本設定
workspace_dir: /path/to/workspace
checkpoint_dir: checkpoints
output_dir: output
temp_dir: temp

# API設定
api:
  claude:
    model: claude-3-7-sonnet-20250219
    max_tokens: 200000
    temperature: 0.2
    timeout: 300
    retry_count: 3
    retry_delay: 5
  openai:
    model: gpt-4o-mini
    image_model: dall-e-3
    image_quality: standard
    image_size: 1024x1024
    temperature: 0.7
    timeout: 60
    retry_count: 3
    retry_delay: 5

# GitHub設定
github:
  owner: develogon
  repo: til
  branch: master
  commit_message_prefix: "[自動生成] "

# AWS S3設定
s3:
  bucket: develogon-til
  prefix: resources/
  region: ap-northeast-1
  public_url_base: https://s3.amazonaws.com/develogon-til

# Slack設定
slack:
  webhook_url: https://hooks.slack.com/services/XXXX/YYYY/ZZZZ
  channel: "#notifications"
  username: リソース生成ワークフロー
  icon_emoji: ":robot_face:"

# 処理設定
processing:
  max_parallel_tasks: 4
  checkpoint_interval: 60
  error_retry_count: 3
  error_retry_delay: 10
```

### 環境変数

主要な設定は環境変数でも指定できます：

- `CLAUDE_API_KEY`: Claude APIキー
- `OPENAI_API_KEY`: OpenAI APIキー
- `GITHUB_TOKEN`: GitHub APIトークン
- `GITHUB_OWNER`: GitHubオーナー名
- `GITHUB_REPO`: GitHubリポジトリ名
- `AWS_ACCESS_KEY_ID`: AWS アクセスキーID
- `AWS_SECRET_ACCESS_KEY`: AWS シークレットアクセスキー
- `S3_BUCKET`: S3バケット名
- `SLACK_WEBHOOK_URL`: Slack Webhook URL

## テスト

システムの品質を確保するために、3つのレベルのテストを提供しています：

1. **ユニットテスト**: 個々のコンポーネントの機能をテスト
2. **インテグレーションテスト**: コンポーネント間の連携をテスト
3. **E2Eテスト**: エンドツーエンドの全体フローをテスト

### テスト実行方法

テストは [pytest](https://docs.pytest.org/) フレームワークを使用しています。

```bash
# すべてのテストを実行
pytest

# ユニットテストのみ実行
pytest tests/unit/

# インテグレーションテストのみ実行
pytest tests/integration/

# E2Eテストのみ実行
pytest tests/e2e/

# 特定のモジュールのテストを実行
pytest tests/unit/processors/

# 詳細なテスト結果を表示
pytest -v

# テストカバレッジレポートを生成
pytest --cov=app tests/
```

### テストモックとフィクスチャ

テストでは、外部依存関係（API、ファイルシステムなど）をモック化して、安定した実行環境を提供しています：

- `tests/mocks/`: 外部サービス（Claude API、GitHub API、S3など）のモック実装
- `tests/fixtures/`: テスト用のサンプルデータ（Markdownファイル、画像、API応答など）

### 環境設定

テストを実行する前に、以下の環境変数を設定することができます（オプション）：

```bash
# テスト用の設定ファイルを指定
export TEST_CONFIG_PATH=tests/fixtures/test_config.yaml

# モックではなく実際のAPIを使用するテストを有効化（注意: 実際のAPIが呼び出されます）
export USE_REAL_APIS=1

# 特定のテストをスキップ
export SKIP_SLOW_TESTS=1
```

## ライセンス

Copyright (c) 2023 Develogon 