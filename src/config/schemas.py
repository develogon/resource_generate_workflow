"""設定スキーマ定義."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class Environment(str, Enum):
    """環境タイプ."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class WorkerType(str, Enum):
    """ワーカータイプ."""
    PARSER = "parser"
    AI = "ai"
    MEDIA = "media"
    AGGREGATOR = "aggregator"


class WorkerConfigSchema(BaseModel):
    """ワーカー設定スキーマ."""
    max_concurrent_tasks: int = Field(default=10, ge=1, le=100)
    counts: Dict[WorkerType, int] = Field(default_factory=lambda: {
        WorkerType.PARSER: 2,
        WorkerType.AI: 3,
        WorkerType.MEDIA: 2,
        WorkerType.AGGREGATOR: 1
    })
    
    @validator('counts')
    def validate_counts(cls, v):
        """ワーカー数の検証."""
        for worker_type, count in v.items():
            if count < 0:
                raise ValueError(f"Worker count for {worker_type} must be non-negative")
            if count > 20:
                raise ValueError(f"Worker count for {worker_type} exceeds maximum (20)")
        return v


class APIConfigSchema(BaseModel):
    """API設定スキーマ."""
    claude_api_key: Optional[str] = None
    claude_base_url: str = "https://api.anthropic.com/v1"
    claude_model: str = "claude-3-sonnet-20240229"
    claude_rate_limit: int = Field(default=60, ge=1, le=1000)
    
    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"
    openai_rate_limit: int = Field(default=60, ge=1, le=1000)
    
    timeout: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    @validator('claude_api_key', 'openai_api_key')
    def validate_api_keys(cls, v):
        """API キーの検証."""
        if v and len(v) < 10:
            raise ValueError("API key is too short")
        return v


class StorageConfigSchema(BaseModel):
    """ストレージ設定スキーマ."""
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = Field(default="us-east-1", pattern=r'^[a-z0-9-]+$')
    s3_bucket: Optional[str] = Field(None, pattern=r'^[a-z0-9.-]+$')
    
    data_dir: str = "./data"
    output_dir: str = "./output"
    cache_dir: str = "./cache"
    log_dir: str = "./logs"
    
    @validator('s3_bucket')
    def validate_s3_bucket(cls, v):
        """S3バケット名の検証."""
        if v and (len(v) < 3 or len(v) > 63):
            raise ValueError("S3 bucket name must be between 3 and 63 characters")
        return v


class RedisConfigSchema(BaseModel):
    """Redis設定スキーマ."""
    url: str = Field(default="redis://localhost:6379", pattern=r'^redis://.*')
    state_ttl: int = Field(default=86400, ge=60, le=604800)  # 1分〜7日
    checkpoint_ttl: int = Field(default=604800, ge=3600, le=2592000)  # 1時間〜30日
    task_ttl: int = Field(default=604800, ge=3600, le=2592000)  # 1時間〜30日


class MetricsConfigSchema(BaseModel):
    """メトリクス設定スキーマ."""
    enabled: bool = True
    prometheus_port: int = Field(default=8000, ge=1024, le=65535)
    collection_interval: int = Field(default=60, ge=10, le=3600)  # 10秒〜1時間


class LoggingConfigSchema(BaseModel):
    """ログ設定スキーマ."""
    level: str = Field(default="INFO", pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_max_size: int = Field(default=10485760, ge=1048576)  # 1MB以上
    file_backup_count: int = Field(default=5, ge=1, le=20)


class ConfigSchema(BaseModel):
    """アプリケーション設定スキーマ."""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    workers: WorkerConfigSchema = Field(default_factory=WorkerConfigSchema)
    api: APIConfigSchema = Field(default_factory=APIConfigSchema)
    storage: StorageConfigSchema = Field(default_factory=StorageConfigSchema)
    redis: RedisConfigSchema = Field(default_factory=RedisConfigSchema)
    metrics: MetricsConfigSchema = Field(default_factory=MetricsConfigSchema)
    logging: LoggingConfigSchema = Field(default_factory=LoggingConfigSchema)
    
    max_concurrent_tasks: int = Field(default=10, ge=1, le=100)
    
    @validator('environment')
    def validate_environment(cls, v):
        """環境設定の検証."""
        return v
    
    @validator('max_concurrent_tasks')
    def validate_max_concurrent_tasks(cls, v, values):
        """最大並行タスク数の検証."""
        if 'workers' in values:
            worker_max = values['workers'].max_concurrent_tasks
            if v > worker_max * 2:
                raise ValueError(
                    f"max_concurrent_tasks ({v}) should not exceed "
                    f"2x worker max_concurrent_tasks ({worker_max})"
                )
        return v
    
    def validate_production_requirements(self) -> List[str]:
        """本番環境要件の検証."""
        errors = []
        
        if self.environment == Environment.PRODUCTION:
            if not self.api.claude_api_key and not self.api.openai_api_key:
                errors.append("At least one API key is required in production")
            
            if self.debug:
                errors.append("Debug mode should be disabled in production")
            
            if not self.storage.s3_bucket:
                errors.append("S3 bucket is required in production")
            
            if self.redis.url == "redis://localhost:6379":
                errors.append("Production Redis URL should not be localhost")
        
        return errors
    
    class Config:
        """Pydantic設定."""
        use_enum_values = True
        validate_assignment = True
        extra = "forbid"  # 未定義フィールドを禁止 