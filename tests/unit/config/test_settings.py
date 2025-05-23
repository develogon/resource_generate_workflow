"""設定管理システムのテスト."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config.constants import DEFAULT_CLAUDE_MODEL, DEFAULT_OPENAI_MODEL
from src.config.settings import (
    AWSConfig,
    CacheConfig,
    ClaudeConfig,
    Config,
    LoggingConfig,
    MetricsConfig,
    OpenAIConfig,
    RedisConfig,
    WorkerConfig,
)


class TestRedisConfig:
    """RedisConfigのテスト."""
    
    def test_default_values(self):
        """デフォルト値のテスト."""
        config = RedisConfig()
        
        assert config.url == "redis://localhost:6379/0"
        assert config.ttl == 3600
        assert config.max_connections == 10
    
    def test_custom_values(self):
        """カスタム値のテスト."""
        config = RedisConfig(
            url="redis://remote:6379/1",
            ttl=7200,
            max_connections=20
        )
        
        assert config.url == "redis://remote:6379/1"
        assert config.ttl == 7200
        assert config.max_connections == 20


class TestClaudeConfig:
    """ClaudeConfigのテスト."""
    
    def test_default_values(self):
        """デフォルト値のテスト."""
        config = ClaudeConfig()
        
        assert config.api_key is None
        assert config.base_url == "https://api.anthropic.com/v1"
        assert config.model == DEFAULT_CLAUDE_MODEL
        assert config.max_tokens == 4000
        assert config.temperature == 0.7
        assert config.rate_limit == 50
    
    def test_custom_values(self):
        """カスタム値のテスト."""
        config = ClaudeConfig(
            api_key="test_key",
            model="claude-3-haiku",
            max_tokens=2000,
            temperature=0.5,
            rate_limit=30
        )
        
        assert config.api_key == "test_key"
        assert config.model == "claude-3-haiku"
        assert config.max_tokens == 2000
        assert config.temperature == 0.5
        assert config.rate_limit == 30


class TestOpenAIConfig:
    """OpenAIConfigのテスト."""
    
    def test_default_values(self):
        """デフォルト値のテスト."""
        config = OpenAIConfig()
        
        assert config.api_key is None
        assert config.base_url == "https://api.openai.com/v1"
        assert config.model == DEFAULT_OPENAI_MODEL
        assert config.max_tokens == 4000
        assert config.temperature == 0.7


class TestLoggingConfig:
    """LoggingConfigのテスト."""
    
    def test_default_values(self):
        """デフォルト値のテスト."""
        config = LoggingConfig()
        
        assert config.level == "INFO"
        assert "%(asctime)s" in config.format
    
    def test_log_level_validation(self):
        """ログレベルのバリデーション."""
        # 有効なレベル
        config = LoggingConfig(level="debug")
        assert config.level == "DEBUG"
        
        config = LoggingConfig(level="WARNING")
        assert config.level == "WARNING"
        
        # 無効なレベル
        with pytest.raises(ValueError, match="Invalid log level"):
            LoggingConfig(level="INVALID")


class TestConfig:
    """Configのテスト."""
    
    def test_default_initialization(self):
        """デフォルト値での初期化テスト."""
        config = Config()
        
        assert config.environment == "development"
        assert config.debug is False
        assert config.api_timeout == 30.0
        assert config.max_retries == 3
        
        # サブ設定のテスト
        assert isinstance(config.redis, RedisConfig)
        assert isinstance(config.claude, ClaudeConfig)
        assert isinstance(config.openai, OpenAIConfig)
        assert isinstance(config.workers, WorkerConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.metrics, MetricsConfig)
        assert isinstance(config.logging, LoggingConfig)
        
        # パス設定のテスト
        assert config.data_dir == Path("data")
        assert config.output_dir == Path("output")
        assert config.cache_dir == Path(".cache")
        assert config.log_dir == Path("logs")
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "true",
        "API_TIMEOUT": "60.0",
        "MAX_RETRIES": "5",
        "REDIS_URL": "redis://prod:6379/0",
        "CLAUDE_API_KEY": "test_claude_key",
        "OPENAI_API_KEY": "test_openai_key",
        "AWS_REGION": "eu-west-1",
        "MAX_CONCURRENT_TASKS": "20",
        "CACHE_SIZE": "2000",
        "METRICS_ENABLED": "false",
        "LOG_LEVEL": "DEBUG"
    })
    def test_from_env(self):
        """環境変数からの設定読み込みテスト."""
        config = Config.from_env()
        
        assert config.environment == "production"
        assert config.debug is True
        assert config.api_timeout == 60.0
        assert config.max_retries == 5
        
        assert config.redis.url == "redis://prod:6379/0"
        assert config.claude.api_key == "test_claude_key"
        assert config.openai.api_key == "test_openai_key"
        assert config.aws.region == "eu-west-1"
        assert config.workers.max_concurrent_tasks == 20
        assert config.cache.size == 2000
        assert config.metrics.enabled is False
        assert config.logging.level == "DEBUG"
    
    def test_from_file(self):
        """設定ファイルからの読み込みテスト."""
        config_data = {
            "environment": "test",
            "debug": True,
            "api": {
                "timeout": 45.0,
                "max_retries": 4
            },
            "redis": {
                "url": "redis://test:6379/1",
                "ttl": 7200
            },
            "claude": {
                "api_key": "file_claude_key",
                "model": "claude-3-haiku",
                "max_tokens": 2000
            },
            "workers": {
                "max_concurrent_tasks": 15,
                "batch_size": 30
            },
            "logging": {
                "level": "WARNING"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)
        
        try:
            config = Config.from_file(config_path)
            
            assert config.environment == "test"
            assert config.debug is True
            assert config.api_timeout == 45.0
            assert config.max_retries == 4
            assert config.redis.url == "redis://test:6379/1"
            assert config.redis.ttl == 7200
            assert config.claude.api_key == "file_claude_key"
            assert config.claude.model == "claude-3-haiku"
            assert config.claude.max_tokens == 2000
            assert config.workers.max_concurrent_tasks == 15
            assert config.workers.batch_size == 30
            assert config.logging.level == "WARNING"
        finally:
            config_path.unlink()
    
    def test_from_file_not_found(self):
        """存在しないファイルからの読み込みテスト."""
        with pytest.raises(FileNotFoundError):
            Config.from_file(Path("non_existent_file.yml"))
    
    def test_create_directories(self):
        """ディレクトリ作成のテスト."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            
            config = Config()
            config.data_dir = base_path / "test_data"
            config.output_dir = base_path / "test_output"
            config.cache_dir = base_path / "test_cache"
            config.log_dir = base_path / "test_logs"
            
            # ディレクトリが存在しないことを確認
            assert not config.data_dir.exists()
            assert not config.output_dir.exists()
            assert not config.cache_dir.exists()
            assert not config.log_dir.exists()
            
            # ディレクトリを作成
            config.create_directories()
            
            # ディレクトリが作成されたことを確認
            assert config.data_dir.exists()
            assert config.output_dir.exists()
            assert config.cache_dir.exists()
            assert config.log_dir.exists()
    
    def test_validate_no_api_keys(self):
        """APIキーが設定されていない場合のバリデーション."""
        config = Config()
        
        with pytest.raises(ValueError, match="At least one of Claude or OpenAI API key must be provided"):
            config.validate()
    
    def test_validate_with_claude_key(self):
        """ClaudeのAPIキーのみ設定されている場合のバリデーション."""
        config = Config()
        config.claude.api_key = "test_claude_key"
        
        # 例外が発生しないことを確認
        config.validate()
    
    def test_validate_with_openai_key(self):
        """OpenAIのAPIキーのみ設定されている場合のバリデーション."""
        config = Config()
        config.openai.api_key = "test_openai_key"
        
        # 例外が発生しないことを確認
        config.validate()
    
    def test_validate_path_conversion(self):
        """相対パスから絶対パスへの変換テスト."""
        config = Config()
        config.claude.api_key = "test_key"  # バリデーションを通すため
        
        # 相対パスを設定
        config.data_dir = Path("relative_data")
        config.output_dir = Path("relative_output")
        
        config.validate()
        
        # 絶対パスに変換されていることを確認
        assert config.data_dir.is_absolute()
        assert config.output_dir.is_absolute()
        assert config.data_dir.name == "relative_data"
        assert config.output_dir.name == "relative_output" 