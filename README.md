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

## システムアーキテクチャ

システムは以下の主要コンポーネントで構成されています：

1. **ワークフローエンジン**: システム全体を制御し、実行フローを管理
2. **タスク管理システム**: 非同期タスクの登録、実行、進捗管理
3. **コンテンツプロセッサ**: 入力コンテンツの解析と変換
4. **ジェネレータシステム**: AIを活用したコンテンツ生成
5. **チェックポイント管理**: 処理状態の保存と復元
6. **画像プロセッサ**: 画像の抽出、変換、最適化

詳細なアーキテクチャについては、`docs/architecture-design.md`を参照してください。

## ディレクトリ構造

```
resource-generate-workflow/
├── app/
│   ├── __init__.py
│   ├── cli.py                 # CLIエントリーポイント
│   ├── config.py              # 設定管理
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── engine.py          # ワークフローエンジン
│   │   ├── task_manager.py    # タスク管理
│   │   └── checkpoint.py      # チェックポイント管理
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── content.py         # コンテンツ処理
│   │   ├── chapter.py         # チャプター処理
│   │   ├── section.py         # セクション処理
│   │   ├── paragraph.py       # パラグラフ処理
│   │   └── image.py           # 画像処理
│   ├── generators/
│   │   ├── __init__.py
│   │   ├── base.py            # 基底ジェネレータクラス
│   │   ├── article.py         # 記事生成器
│   │   ├── script.py          # 台本生成器
│   │   ├── script_json.py     # 台本JSON生成器
│   │   ├── tweet.py           # ツイート生成器
│   │   ├── description.py     # 説明文生成器
│   │   └── thumbnail.py       # サムネイル生成器
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── claude.py          # Claude API連携
│   │   ├── openai.py          # OpenAI API連携
│   │   ├── github.py          # GitHub API連携
│   │   ├── s3.py              # AWS S3連携
│   │   └── slack.py           # Slack通知連携
│   └── utils/
│       ├── __init__.py
│       ├── markdown.py        # Markdown処理ユーティリティ
│       ├── file.py            # ファイル操作ユーティリティ
│       └── logger.py          # ロギングユーティリティ
├── tests/                     # テストコード
├── docs/                      # ドキュメント
├── prompts/                   # Claude用プロンプトテンプレート
├── templates/                 # 出力テンプレート
└── examples/                  # 使用例
```

## 出力結果の構造

処理の各段階で以下のようなディレクトリ構造が生成されます：

```
title/
├── chapter1/
│   ├── text.md
│   ├── section1/
│   │   ├── text.md
│   │   ├── section_structure.yaml
│   │   ├── article.md
│   │   ├── script.md
│   │   ├── script.json
│   │   ├── tweets.csv
│   │   └── images/
│   ├── section2/
│   │   └── ...
│   ├── article.md
│   ├── script.md
│   ├── script.json
│   ├── tweets.csv
│   └── images/
├── chapter2/
│   └── ...
├── text.md
├── article.md
├── script.md
├── tweets.csv
├── structure.md
├── description.md
└── images/
└── thumbnail/
    └── ...
```

## エラー処理と回復メカニズム

システムは以下のエラー処理戦略を採用しています：

1. **一時的な障害**: 再試行ポリシーに基づいて自動再試行
2. **永続的な障害**: エラーログ記録、Slack通知、処理の安全な停止
3. **部分的な障害**: 影響を受けるタスクのみをスキップし、残りのタスクは継続実行

チェックポイントシステムにより、以下の再開機能を提供します：

1. 最新のチェックポイントから自動再開
2. 特定のチェックポイントを指定して再開
3. 失敗したタスクのみを再実行

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