"""
リソース生成ワークフローの全体設定

このモジュールは、アプリケーション全体の設定を定義します。
環境変数やデフォルト値を管理し、アプリケーション全体で一貫した設定を提供します。
"""

import os
from pathlib import Path

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(__file__).parent.parent.absolute()

# 出力ディレクトリの設定
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(ROOT_DIR, "output"))

# テンプレートディレクトリの設定
TEMPLATE_DIR = os.path.join(ROOT_DIR, "templates")
PROMPT_TEMPLATE_DIR = os.path.join(TEMPLATE_DIR, "prompts")

# 画像処理の設定
IMAGE_PROCESSING = {
    "max_width": 1920,
    "max_height": 1080,
    "default_format": "png",
    "quality": 90,
    "temp_dir": os.path.join(ROOT_DIR, "temp"),
}

# Claude APIの設定
CLAUDE_API = {
    "model": "claude-3-7-sonnet-20250219",
    "max_tokens": 100000,
    "temperature": 0.3,
    "timeout": 300,  # APIリクエストのタイムアウト (秒)
    "max_retries": 3,  # 最大リトライ回数
    "backoff_factor": 2,  # リトライ間隔の倍率
}

# GitHub設定
GITHUB = {
    "default_branch": "master",
    "commit_prefix": "[Auto] ",
    "batch_size": 10,  # 一度にプッシュするファイル数
}

# S3ストレージ設定
S3_STORAGE = {
    "bucket_name": os.environ.get("S3_BUCKET_NAME", "resource-images"),
    "region": os.environ.get("AWS_REGION", "ap-northeast-1"),
    "base_url": os.environ.get("S3_BASE_URL", "https://resource-images.s3.ap-northeast-1.amazonaws.com"),
    "expiration": 7 * 24 * 60 * 60,  # URLの有効期限 (秒)
}

# Slack通知設定
SLACK = {
    "enabled": os.environ.get("SLACK_ENABLED", "False").lower() in ("true", "1", "yes"),
    "channel": os.environ.get("SLACK_CHANNEL", "#log-resource-generator-workflow"),
    "username": os.environ.get("SLACK_USERNAME", "Resource Bot"),
    "icon_emoji": os.environ.get("SLACK_ICON_EMOJI", ":book:"),
}

# ログ設定
LOGGING = {
    "level": os.environ.get("LOG_LEVEL", "INFO"),
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.path.join(ROOT_DIR, "logs", "app.log"),
    "max_size": 10 * 1024 * 1024,  # 最大ログファイルサイズ (10MB)
    "backup_count": 5,  # 保持するバックアップ数
}

# 状態管理設定
STATE_MANAGEMENT = {
    "checkpoint_dir": os.path.join(ROOT_DIR, "checkpoints"),
    "retention_days": 7,  # チェックポイント保持期間 (日)
    "auto_checkpoint": True,  # エラー時に自動チェックポイント生成するか
}

# 並列処理設定
PARALLEL_PROCESSING = {
    "max_workers": os.cpu_count() or 4,  # 最大ワーカー数 (デフォルトはCPUコア数)
    "chunk_size": 5,  # チャンク分割サイズ
}

# 生成するコンテンツタイプの設定
CONTENT_TYPES = {
    "article": {
        "enabled": True,
        "filename": "article.md",
        "template": "article.md",
    },
    "script": {
        "enabled": True,
        "filename": "script.md",
        "template": "script.md",
    },
    "json_script": {
        "enabled": True,
        "filename": "script.json",
        "template": "script_json.md",
    },
    "tweets": {
        "enabled": True,
        "filename": "tweets.csv",
        "template": "tweets.md",
    },
    "description": {
        "enabled": True,
        "filename": "description.md",
        "template": "description.md",
    },
} 