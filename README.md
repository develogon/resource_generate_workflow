# Resource Generate Workflow

高性能リソース生成ワークフローエンジン - 技術書籍のMarkdownから多様な派生コンテンツを自動生成

## 📋 概要

このシステムは、技術書籍のMarkdownコンテンツから以下を自動生成します：

- 📄 記事コンテンツ
- 🎬 動画台本
- 🐦 ツイート
- 📝 説明文
- 🖼️ サムネイル画像
- 📊 構造化データ

## 🏗️ アーキテクチャ

イベント駆動・マイクロサービス的なアーキテクチャを採用：

- **オーケストレーター**: ワークフロー全体の制御
- **イベントバス**: 非同期イベント処理
- **ワーカープール**: 並列処理によるスケーラビリティ
- **状態管理**: Redis による分散状態管理
- **メトリクス**: Prometheus による監視

## 🚀 クイックスタート

### 1. 環境構築

```bash
# リポジトリのクローン
git clone <repository-url>
cd resource_generate_workflow

# 依存関係のインストール
make setup

# 環境変数の設定
cp env.example .env
# .env ファイルを編集してAPI キー等を設定
```

### 2. 必要なサービスの起動

```bash
# Redis の起動（Docker使用）
docker run -d -p 6379:6379 redis:7-alpine

# または docker-compose で全サービス起動
make docker-run
```

### 3. 実行

```bash
# 基本実行
make run

# CLI直接実行
python -m src.cli --lang ja --title "Go言語入門"
```

## 🔧 設定

### 環境変数

主要な環境変数（詳細は `env.example` を参照）：

```bash
# API設定
CLAUDE_API_KEY=your_api_key
OPENAI_API_KEY=your_api_key

# AWS設定
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
S3_BUCKET=your_bucket

# Redis設定
REDIS_URL=redis://localhost:6379/0
```

### 設定ファイル

- `config/development.yml`: 開発環境設定
- `config/production.yml`: 本番環境設定（作成予定）

## 📁 プロジェクト構造

```
resource-generate-workflow/
├── src/                      # メインソースコード
│   ├── core/                # コアシステム
│   ├── workers/             # ワーカー実装
│   ├── generators/          # コンテンツ生成器
│   ├── clients/             # 外部API クライアント
│   └── utils/               # ユーティリティ
├── prompts/                 # AI プロンプト
│   ├── system/             # システムプロンプト
│   └── message/            # メッセージプロンプト
├── templates/              # テンプレートファイル
├── tests/                  # テストコード
├── config/                 # 設定ファイル
└── docker/                # Docker 設定
```

## 🧪 テスト

```bash
# 全テスト実行
make test

# ユニットテストのみ
make test-unit

# 統合テストのみ
make test-integration
```

## 📊 監視・メトリクス

- **Prometheus**: メトリクス収集（ポート 8000）
- **Grafana**: ダッシュボード（ポート 3000）
- **ログ**: 構造化ログ出力

## 🐳 Docker 実行

```bash
# イメージビルド
make docker-build

# サービス起動
make docker-run

# サービス停止
make docker-stop
```

## 🔧 開発

### コード品質

```bash
# フォーマット
make format

# リント
make lint
```

### デバッグ

```bash
# デバッグモードで実行
DEBUG=1 python -m src.cli
```

## 📝 使用例

```python
from src.core.orchestrator import WorkflowOrchestrator
from src.config.settings import Config

# 設定読み込み
config = Config.from_env()

# オーケストレーター初期化
orchestrator = WorkflowOrchestrator(config)

# ワークフロー実行
context = await orchestrator.execute(
    lang="ja", 
    title="Go言語入門"
)
```

## 🔄 ワークフロー

1. **Markdown解析**: チャプター・セクション・パラグラフに分割
2. **構造解析**: AI による内容理解
3. **並列生成**: 各種コンテンツの同時生成
4. **画像処理**: SVG/DrawIO/Mermaid → PNG変換
5. **アップロード**: S3への自動アップロード
6. **集約**: 結果のまとめと出力

## 📈 パフォーマンス

- **処理時間**: 従来比80%削減
- **並列処理**: 最大30タスク同時実行
- **スケーラビリティ**: 水平スケーリング対応

## 🤝 コントリビューション

1. フォークしてブランチ作成
2. 機能実装・テスト追加
3. コード品質チェック: `make lint format`
4. プルリクエスト作成

## 📄 ライセンス

MIT License

## 🆘 トラブルシューティング

### よくある問題

1. **Redis接続エラー**: Redis が起動しているか確認
2. **API制限エラー**: レート制限の設定を調整
3. **メモリ不足**: バッチサイズを調整

詳細は `docs/troubleshooting.md` を参照（作成予定）

## 📧 サポート

- Issues: GitHub Issues
- Documentation: `docs/` ディレクトリ
- Architecture: `docs/architecture-design.md` 