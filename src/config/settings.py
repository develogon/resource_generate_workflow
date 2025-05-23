"""設定管理システム."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, field_validator

from .constants import (
    DEFAULT_API_TIMEOUT,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_CLAUDE_MAX_TOKENS,
    DEFAULT_CLAUDE_MODEL,
    DEFAULT_CLAUDE_RATE_LIMIT,
    DEFAULT_CLAUDE_TEMPERATURE,
    DEFAULT_IMAGE_HEIGHT,
    DEFAULT_IMAGE_WIDTH,
    DEFAULT_LOG_FORMAT,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_CONCURRENT_TASKS,
    DEFAULT_MAX_RETRIES,
    DEFAULT_MAX_WORKERS,
    DEFAULT_METRICS_PATH,
    DEFAULT_OPENAI_MAX_TOKENS,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_OPENAI_TEMPERATURE,
    DEFAULT_PROMETHEUS_PORT,
    DEFAULT_REDIS_TTL,
)


class RedisConfig(BaseModel):
    """Redis設定."""
    
    url: str = "redis://localhost:6379/0"
    ttl: int = DEFAULT_REDIS_TTL
    max_connections: int = 10


class ClaudeConfig(BaseModel):
    """Claude API設定."""
    
    api_key: Optional[str] = None
    base_url: str = "https://api.anthropic.com/v1"
    model: str = DEFAULT_CLAUDE_MODEL
    max_tokens: int = DEFAULT_CLAUDE_MAX_TOKENS
    temperature: float = DEFAULT_CLAUDE_TEMPERATURE
    rate_limit: int = DEFAULT_CLAUDE_RATE_LIMIT


class OpenAIConfig(BaseModel):
    """OpenAI API設定."""
    
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    model: str = DEFAULT_OPENAI_MODEL
    max_tokens: int = DEFAULT_OPENAI_MAX_TOKENS
    temperature: float = DEFAULT_OPENAI_TEMPERATURE


class AWSConfig(BaseModel):
    """AWS設定."""
    
    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    region: str = "us-west-2"
    s3_bucket: Optional[str] = None


class GitHubConfig(BaseModel):
    """GitHub設定."""
    
    token: Optional[str] = None
    repo: Optional[str] = None


class SlackConfig(BaseModel):
    """Slack設定."""
    
    webhook_url: Optional[str] = None
    channel: str = "#alerts"


class WorkerConfig(BaseModel):
    """ワーカー設定."""
    
    max_concurrent_tasks: int = DEFAULT_MAX_CONCURRENT_TASKS
    max_workers: int = DEFAULT_MAX_WORKERS
    batch_size: int = DEFAULT_BATCH_SIZE
    timeout: float = 300.0


class CacheConfig(BaseModel):
    """キャッシュ設定."""
    
    size: int = DEFAULT_CACHE_SIZE
    ttl: int = DEFAULT_CACHE_TTL


class MetricsConfig(BaseModel):
    """メトリクス設定."""
    
    enabled: bool = True
    port: int = DEFAULT_PROMETHEUS_PORT
    path: str = DEFAULT_METRICS_PATH


class ImageConfig(BaseModel):
    """画像処理設定."""
    
    width: int = DEFAULT_IMAGE_WIDTH
    height: int = DEFAULT_IMAGE_HEIGHT
    format: str = "PNG"


class LoggingConfig(BaseModel):
    """ログ設定."""
    
    level: str = DEFAULT_LOG_LEVEL
    format: str = DEFAULT_LOG_FORMAT
    
    @field_validator('level')
    def validate_log_level(cls, v):
        """ログレベルの検証."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


@dataclass
class Config:
    """アプリケーション設定."""
    
    # 環境設定
    environment: str = "development"
    debug: bool = False
    
    # API設定
    api_timeout: float = DEFAULT_API_TIMEOUT
    max_retries: int = DEFAULT_MAX_RETRIES
    
    # 外部サービス設定
    redis: RedisConfig = field(default_factory=RedisConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    aws: AWSConfig = field(default_factory=AWSConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    
    # システム設定
    workers: WorkerConfig = field(default_factory=WorkerConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # パス設定
    data_dir: Path = field(default_factory=lambda: Path("data"))
    output_dir: Path = field(default_factory=lambda: Path("output"))
    cache_dir: Path = field(default_factory=lambda: Path(".cache"))
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    
    @classmethod
    def from_env(cls) -> Config:
        """環境変数から設定を読み込み."""
        config = cls()
        
        # 環境設定
        config.environment = os.getenv("ENVIRONMENT", "development")
        config.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # API設定
        config.api_timeout = float(os.getenv("API_TIMEOUT", DEFAULT_API_TIMEOUT))
        config.max_retries = int(os.getenv("MAX_RETRIES", DEFAULT_MAX_RETRIES))
        
        # Redis設定
        config.redis = RedisConfig(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            ttl=int(os.getenv("REDIS_TTL", DEFAULT_REDIS_TTL)),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
        )
        
        # Claude設定
        config.claude = ClaudeConfig(
            api_key=os.getenv("CLAUDE_API_KEY"),
            base_url=os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com/v1"),
            model=os.getenv("CLAUDE_MODEL", DEFAULT_CLAUDE_MODEL),
            max_tokens=int(os.getenv("CLAUDE_MAX_TOKENS", DEFAULT_CLAUDE_MAX_TOKENS)),
            temperature=float(os.getenv("CLAUDE_TEMPERATURE", DEFAULT_CLAUDE_TEMPERATURE)),
            rate_limit=int(os.getenv("CLAUDE_RATE_LIMIT", DEFAULT_CLAUDE_RATE_LIMIT))
        )
        
        # OpenAI設定
        config.openai = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", DEFAULT_OPENAI_MAX_TOKENS)),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", DEFAULT_OPENAI_TEMPERATURE))
        )
        
        # AWS設定
        config.aws = AWSConfig(
            access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region=os.getenv("AWS_REGION", "us-west-2"),
            s3_bucket=os.getenv("S3_BUCKET")
        )
        
        # GitHub設定
        config.github = GitHubConfig(
            token=os.getenv("GITHUB_TOKEN"),
            repo=os.getenv("GITHUB_REPO")
        )
        
        # Slack設定
        config.slack = SlackConfig(
            webhook_url=os.getenv("SLACK_WEBHOOK_URL"),
            channel=os.getenv("SLACK_CHANNEL", "#alerts")
        )
        
        # ワーカー設定
        config.workers = WorkerConfig(
            max_concurrent_tasks=int(os.getenv("MAX_CONCURRENT_TASKS", DEFAULT_MAX_CONCURRENT_TASKS)),
            max_workers=int(os.getenv("MAX_WORKERS", DEFAULT_MAX_WORKERS)),
            batch_size=int(os.getenv("BATCH_SIZE", DEFAULT_BATCH_SIZE)),
            timeout=float(os.getenv("WORKER_TIMEOUT", "300.0"))
        )
        
        # キャッシュ設定
        config.cache = CacheConfig(
            size=int(os.getenv("CACHE_SIZE", DEFAULT_CACHE_SIZE)),
            ttl=int(os.getenv("CACHE_TTL", DEFAULT_CACHE_TTL))
        )
        
        # メトリクス設定
        config.metrics = MetricsConfig(
            enabled=os.getenv("METRICS_ENABLED", "true").lower() == "true",
            port=int(os.getenv("PROMETHEUS_PORT", DEFAULT_PROMETHEUS_PORT)),
            path=os.getenv("METRICS_PATH", DEFAULT_METRICS_PATH)
        )
        
        # ログ設定
        config.logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL),
            format=os.getenv("LOG_FORMAT", DEFAULT_LOG_FORMAT)
        )
        
        return config
    
    @classmethod
    def from_file(cls, config_path: Path) -> Config:
        """設定ファイルから設定を読み込み."""
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        return cls._from_dict(data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> Config:
        """辞書から設定を作成."""
        config = cls()
        
        # 環境設定
        config.environment = data.get("environment", "development")
        config.debug = data.get("debug", False)
        
        # API設定
        api_config = data.get("api", {})
        config.api_timeout = api_config.get("timeout", DEFAULT_API_TIMEOUT)
        config.max_retries = api_config.get("max_retries", DEFAULT_MAX_RETRIES)
        
        # Redis設定
        redis_data = data.get("redis", {})
        config.redis = RedisConfig(**redis_data)
        
        # Claude設定
        claude_data = data.get("claude", {})
        config.claude = ClaudeConfig(**claude_data)
        
        # OpenAI設定
        openai_data = data.get("openai", {})
        config.openai = OpenAIConfig(**openai_data)
        
        # AWS設定
        aws_data = data.get("aws", {})
        config.aws = AWSConfig(**aws_data)
        
        # GitHub設定
        github_data = data.get("github", {})
        config.github = GitHubConfig(**github_data)
        
        # Slack設定
        slack_data = data.get("slack", {})
        config.slack = SlackConfig(**slack_data)
        
        # ワーカー設定
        workers_data = data.get("workers", {})
        config.workers = WorkerConfig(**workers_data)
        
        # キャッシュ設定
        cache_data = data.get("cache", {})
        config.cache = CacheConfig(**cache_data)
        
        # メトリクス設定
        metrics_data = data.get("metrics", {})
        config.metrics = MetricsConfig(**metrics_data)
        
        # 画像設定
        image_data = data.get("image", {})
        config.image = ImageConfig(**image_data)
        
        # ログ設定
        logging_data = data.get("logging", {})
        config.logging = LoggingConfig(**logging_data)
        
        return config
    
    def create_directories(self) -> None:
        """必要なディレクトリを作成."""
        directories = [
            self.data_dir,
            self.output_dir,
            self.cache_dir,
            self.log_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> None:
        """設定の検証."""
        # 必須設定のチェック
        if not self.claude.api_key and not self.openai.api_key:
            raise ValueError("At least one of Claude or OpenAI API key must be provided")
        
        # パス設定の検証
        if not self.data_dir.is_absolute():
            self.data_dir = Path.cwd() / self.data_dir
        if not self.output_dir.is_absolute():
            self.output_dir = Path.cwd() / self.output_dir
        if not self.cache_dir.is_absolute():
            self.cache_dir = Path.cwd() / self.cache_dir
        if not self.log_dir.is_absolute():
            self.log_dir = Path.cwd() / self.log_dir 