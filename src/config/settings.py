"""設定管理システム."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class WorkerConfig:
    """ワーカー設定."""
    max_concurrent_tasks: int = 10
    counts: Dict[str, int] = field(default_factory=lambda: {
        "parser": 2,
        "ai": 3,
        "media": 2,
        "aggregator": 1
    })


@dataclass
class APIConfig:
    """API設定."""
    claude_api_key: Optional[str] = None
    claude_base_url: str = "https://api.anthropic.com/v1"
    claude_model: str = "claude-3-sonnet-20240229"
    claude_rate_limit: int = 60  # requests per minute
    
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class StorageConfig:
    """ストレージ設定."""
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket: Optional[str] = None
    
    # ローカルストレージ
    data_dir: str = "./data"
    output_dir: str = "./output"
    cache_dir: str = "./cache"
    log_dir: str = "./logs"


@dataclass
class RedisConfig:
    """Redis設定."""
    url: str = "redis://localhost:6379"
    state_ttl: int = 86400  # 24時間
    checkpoint_ttl: int = 604800  # 7日間
    task_ttl: int = 604800  # 7日間


@dataclass
class Config:
    """アプリケーション設定."""
    # 環境設定
    environment: str = "development"
    debug: bool = False
    
    # ワーカー設定
    workers: WorkerConfig = field(default_factory=WorkerConfig)
    
    # API設定
    api: APIConfig = field(default_factory=APIConfig)
    
    # ストレージ設定
    storage: StorageConfig = field(default_factory=StorageConfig)
    
    # Redis設定
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # メトリクス設定
    metrics_enabled: bool = True
    prometheus_port: int = 8000
    
    # その他の設定
    max_concurrent_tasks: int = 10
    
    @property
    def redis_url(self) -> str:
        """Redis URL の取得."""
        return self.redis.url
        
    @property
    def worker_counts(self) -> Dict[str, int]:
        """ワーカー数設定の取得."""
        return self.workers.counts
        
    @classmethod
    def from_env(cls) -> 'Config':
        """環境変数から設定を読み込み."""
        config = cls()
        
        # 環境変数の読み込み
        config.environment = os.getenv("ENVIRONMENT", "development")
        config.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # API設定
        config.api.claude_api_key = os.getenv("CLAUDE_API_KEY")
        config.api.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # ストレージ設定
        config.storage.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        config.storage.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        config.storage.aws_region = os.getenv("AWS_REGION", "us-east-1")
        config.storage.s3_bucket = os.getenv("S3_BUCKET")
        
        # Redis設定
        config.redis.url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # パス設定
        config.storage.data_dir = os.getenv("DATA_DIR", "./data")
        config.storage.output_dir = os.getenv("OUTPUT_DIR", "./output")
        config.storage.cache_dir = os.getenv("CACHE_DIR", "./cache")
        config.storage.log_dir = os.getenv("LOG_DIR", "./logs")
        
        # ワーカー設定
        max_concurrent = os.getenv("MAX_CONCURRENT_TASKS")
        if max_concurrent:
            config.max_concurrent_tasks = int(max_concurrent)
            config.workers.max_concurrent_tasks = int(max_concurrent)
        
        return config
        
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """設定ファイルから設定を読み込み."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        with open(config_file, 'r', encoding='utf-8') as f:
            if config_file.suffix in ['.yaml', '.yml']:
                config_data = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {config_file.suffix}")
        
        return cls.from_dict(config_data)
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """辞書から設定を読み込み."""
        config = cls()
        
        # 基本設定
        config.environment = data.get("environment", "development")
        config.debug = data.get("debug", False)
        config.max_concurrent_tasks = data.get("max_concurrent_tasks", 10)
        
        # ワーカー設定
        if "workers" in data:
            worker_data = data["workers"]
            config.workers.max_concurrent_tasks = worker_data.get("max_concurrent_tasks", 10)
            if "counts" in worker_data:
                config.workers.counts.update(worker_data["counts"])
                
        # API設定
        if "api" in data:
            api_data = data["api"]
            for key, value in api_data.items():
                if hasattr(config.api, key):
                    setattr(config.api, key, value)
                    
        # ストレージ設定
        if "storage" in data:
            storage_data = data["storage"]
            for key, value in storage_data.items():
                if hasattr(config.storage, key):
                    setattr(config.storage, key, value)
                    
        # Redis設定
        if "redis" in data:
            redis_data = data["redis"]
            for key, value in redis_data.items():
                if hasattr(config.redis, key):
                    setattr(config.redis, key, value)
                    
        return config
        
    def to_dict(self) -> Dict[str, Any]:
        """設定を辞書に変換."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "workers": {
                "max_concurrent_tasks": self.workers.max_concurrent_tasks,
                "counts": self.workers.counts
            },
            "api": {
                "claude_api_key": "***" if self.api.claude_api_key else None,
                "claude_base_url": self.api.claude_base_url,
                "claude_model": self.api.claude_model,
                "claude_rate_limit": self.api.claude_rate_limit,
                "openai_api_key": "***" if self.api.openai_api_key else None,
                "openai_base_url": self.api.openai_base_url,
                "openai_model": self.api.openai_model,
                "timeout": self.api.timeout,
                "max_retries": self.api.max_retries
            },
            "storage": {
                "aws_access_key_id": "***" if self.storage.aws_access_key_id else None,
                "aws_secret_access_key": "***" if self.storage.aws_secret_access_key else None,
                "aws_region": self.storage.aws_region,
                "s3_bucket": self.storage.s3_bucket,
                "data_dir": self.storage.data_dir,
                "output_dir": self.storage.output_dir,
                "cache_dir": self.storage.cache_dir,
                "log_dir": self.storage.log_dir
            },
            "redis": {
                "url": self.redis.url,
                "state_ttl": self.redis.state_ttl,
                "checkpoint_ttl": self.redis.checkpoint_ttl,
                "task_ttl": self.redis.task_ttl
            },
            "metrics_enabled": self.metrics_enabled,
            "prometheus_port": self.prometheus_port
        }
        
    def validate(self) -> List[str]:
        """設定の検証."""
        errors = []
        
        # 必須設定のチェック
        if self.environment == "production":
            if not self.api.claude_api_key and not self.api.openai_api_key:
                errors.append("API key is required in production")
                
        # パスの存在チェック
        for path_attr in ["data_dir", "output_dir", "cache_dir", "log_dir"]:
            path = getattr(self.storage, path_attr)
            if not Path(path).exists():
                try:
                    Path(path).mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    errors.append(f"Cannot create directory {path}: {e}")
                    
        return errors
        
    def setup_directories(self):
        """必要なディレクトリを作成."""
        directories = [
            self.storage.data_dir,
            self.storage.output_dir,
            self.storage.cache_dir,
            self.storage.log_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)


def load_config(config_path: Optional[str] = None) -> Config:
    """設定の読み込み."""
    if config_path:
        # 指定されたファイルから読み込み
        return Config.from_file(config_path)
    else:
        # 環境変数から読み込み
        config = Config.from_env()
        
        # 環境別設定ファイルがあれば読み込み
        env_config_path = f"config/{config.environment}.yml"
        if Path(env_config_path).exists():
            file_config = Config.from_file(env_config_path)
            # 環境変数の設定で上書き
            for attr in ["api", "storage", "redis"]:
                file_attr = getattr(file_config, attr)
                env_attr = getattr(config, attr)
                for key, value in env_attr.__dict__.items():
                    if value is not None:
                        setattr(file_attr, key, value)
                setattr(config, attr, file_attr)
        
        return config 