"""システム定数定義."""

from enum import Enum

# デフォルト値
DEFAULT_MAX_CONCURRENT_TASKS = 10
DEFAULT_MAX_WORKERS = 5
DEFAULT_BATCH_SIZE = 50
DEFAULT_API_TIMEOUT = 30.0
DEFAULT_CACHE_SIZE = 1000
DEFAULT_CACHE_TTL = 3600
DEFAULT_REDIS_TTL = 3600
DEFAULT_MAX_RETRIES = 3

# API設定
DEFAULT_CLAUDE_MODEL = "claude-3-sonnet-20240229"
DEFAULT_CLAUDE_RATE_LIMIT = 10
DEFAULT_CLAUDE_MAX_TOKENS = 2000
DEFAULT_CLAUDE_TEMPERATURE = 0.7

DEFAULT_OPENAI_MODEL = "gpt-4"
DEFAULT_OPENAI_MAX_TOKENS = 2000
DEFAULT_OPENAI_TEMPERATURE = 0.7

# パス設定
DEFAULT_DATA_DIR = "data"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_CACHE_DIR = ".cache"
DEFAULT_LOG_DIR = "logs"

# ログ設定
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# メトリクス設定
DEFAULT_PROMETHEUS_PORT = 8000
DEFAULT_METRICS_PATH = "/metrics"

# 画像処理設定
DEFAULT_IMAGE_WIDTH = 800
DEFAULT_IMAGE_HEIGHT = 600
DEFAULT_IMAGE_FORMAT = "PNG"

# ファイル拡張子
MARKDOWN_EXTENSIONS = [".md", ".markdown"]
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".svg"]
CODE_EXTENSIONS = [".py", ".js", ".ts", ".go", ".java", ".cpp", ".c"]


class EventType(Enum):
    """イベントタイプ定数."""
    
    # ワークフローイベント
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    
    # 解析イベント
    CHAPTER_PARSED = "chapter.parsed"
    SECTION_PARSED = "section.parsed"
    PARAGRAPH_PARSED = "paragraph.parsed"
    STRUCTURE_ANALYZED = "structure.analyzed"
    
    # 生成イベント
    CONTENT_GENERATED = "content.generated"
    IMAGE_PROCESSED = "image.processed"
    THUMBNAIL_GENERATED = "thumbnail.generated"
    
    # 集約イベント
    SECTION_AGGREGATED = "section.aggregated"
    CHAPTER_AGGREGATED = "chapter.aggregated"
    METADATA_GENERATED = "metadata.generated"


class TaskType(Enum):
    """タスクタイプ定数."""
    
    PARSE_CHAPTER = "parse_chapter"
    PARSE_SECTION = "parse_section"
    PARSE_PARAGRAPH = "parse_paragraph"
    ANALYZE_STRUCTURE = "analyze_structure"
    GENERATE_CONTENT = "generate_content"
    GENERATE_ARTICLE = "generate_article"
    GENERATE_SCRIPT = "generate_script"
    GENERATE_TWEET = "generate_tweet"
    GENERATE_DESCRIPTION = "generate_description"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    PROCESS_IMAGE = "process_image"
    UPLOAD_S3 = "upload_s3"
    AGGREGATE_SECTION = "aggregate_section"
    AGGREGATE_CHAPTER = "aggregate_chapter"
    GENERATE_METADATA = "generate_metadata"


class ContentType(Enum):
    """コンテンツタイプ定数."""
    
    ARTICLE = "article"
    SCRIPT = "script"
    SCRIPT_JSON = "script_json"
    TWEET = "tweet"
    DESCRIPTION = "description"
    THUMBNAIL = "thumbnail"
    IMAGE = "image"


class ImageType(Enum):
    """画像タイプ定数."""
    
    SVG = "svg"
    DRAWIO = "drawio"
    MERMAID = "mermaid"
    PNG = "png"
    JPEG = "jpeg" 