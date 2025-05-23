"""MediaWorker のテスト."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import base64

from src.workers.media import MediaWorker, ImageType, ProcessedImage, ImageProcessingRequest
from src.workers.base import Event, EventType
from src.config import Config


@pytest.fixture
def config():
    """テスト用設定."""
    config = Config()
    config.workers.max_concurrent_tasks = 2
    config.max_retries = 3
    config.image.width = 800
    config.image.height = 600
    config.aws.s3_bucket = "test-bucket"
    return config


@pytest.fixture
def media_worker(config):
    """テスト用メディアワーカー."""
    return MediaWorker(config, "media-test-1")


@pytest.fixture
def event_bus():
    """テスト用イベントバス."""
    bus = Mock()
    bus.subscribe = AsyncMock()
    bus.publish = AsyncMock()
    return bus


@pytest.fixture
def state_manager():
    """テスト用状態管理."""
    manager = Mock()
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def metrics():
    """テスト用メトリクス."""
    metrics = Mock()
    metrics.record_processing_time = Mock()
    metrics.record_error = Mock()
    return metrics


@pytest.fixture
def content_generated_event():
    """コンテンツ生成済みイベント."""
    return Event(
        event_type=EventType.CONTENT_GENERATED,
        workflow_id="test-workflow-1",
        data={
            "content": {
                "type": "article",
                "title": "テスト記事",
                "content": """これはテスト記事です。

```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```

<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="red" />
</svg>

![diagram](example.drawio.png)

テキストが続きます。""",
                "format": "markdown"
            },
            "paragraph": {
                "index": 0,
                "content": "テストパラグラフ"
            },
            "section": {
                "title": "テストセクション"
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def thumbnail_generated_event():
    """サムネイル生成済みイベント."""
    return Event(
        event_type=EventType.THUMBNAIL_GENERATED,
        workflow_id="test-workflow-1",
        data={
            "thumbnail": {
                "title": "第1章 テスト",
                "style": "modern",
                "color_scheme": "blue",
                "dimensions": {
                    "width": 1200,
                    "height": 630
                },
                "format": "png"
            },
            "chapter": {
                "title": "第1章 テスト",
                "level": 1
            },
            "metadata": {
                "title": "第1章 テスト"
            }
        },
        trace_id="trace-123"
    )


@pytest.fixture
def metadata_generated_event():
    """メタデータ生成済みイベント."""
    return Event(
        event_type=EventType.METADATA_GENERATED,
        workflow_id="test-workflow-1",
        data={
            "metadata": {
                "title": "テストメタデータ"
            }
        },
        trace_id="trace-123"
    )


class TestMediaWorker:
    """MediaWorker のテスト."""
    
    def test_init(self, media_worker, config):
        """初期化のテスト."""
        assert media_worker.config == config
        assert media_worker.worker_id == "media-test-1"
        assert media_worker.semaphore._value == config.workers.max_concurrent_tasks
        assert media_worker.running is False
        assert media_worker.s3_client is None
        assert media_worker.converter_pool is None
        
    def test_get_subscriptions(self, media_worker):
        """購読イベントタイプのテスト."""
        subscriptions = media_worker.get_subscriptions()
        expected_subscriptions = {
            EventType.CONTENT_GENERATED,
            EventType.THUMBNAIL_GENERATED,
            EventType.METADATA_GENERATED
        }
        assert subscriptions == expected_subscriptions
        
    @pytest.mark.asyncio
    async def test_start(self, media_worker, event_bus, state_manager, metrics):
        """ワーカー起動のテスト."""
        await media_worker.start(event_bus, state_manager, metrics)
        
        assert media_worker.running is True
        assert media_worker.event_bus == event_bus
        assert media_worker.state_manager == state_manager
        assert media_worker.metrics == metrics
        
        # 購読が正しく行われたかチェック
        assert event_bus.subscribe.call_count == 3
        
    @pytest.mark.asyncio
    async def test_process_content_generated(self, media_worker, content_generated_event, event_bus):
        """コンテンツ生成イベント処理のテスト."""
        media_worker.event_bus = event_bus
        
        await media_worker.process(content_generated_event)
        
        # 画像処理完了イベントが発行されたかチェック
        assert event_bus.publish.call_count == 1
        
        # 発行されたイベントの確認
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.type == EventType.IMAGE_PROCESSED
        assert 'original_content' in published_event.data
        assert 'processed_images' in published_event.data
        
    @pytest.mark.asyncio
    async def test_process_thumbnail_generated(self, media_worker, thumbnail_generated_event, event_bus):
        """サムネイル生成イベント処理のテスト."""
        media_worker.event_bus = event_bus
        
        await media_worker.process(thumbnail_generated_event)
        
        # サムネイル処理完了イベントが発行されたかチェック
        assert event_bus.publish.call_count == 1
        
        # 発行されたイベントの確認
        published_event = event_bus.publish.call_args[0][0]
        assert published_event.type == EventType.IMAGE_PROCESSED
        assert 'thumbnail' in published_event.data
        
    @pytest.mark.asyncio
    async def test_process_metadata_generated(self, media_worker, metadata_generated_event):
        """メタデータ生成イベント処理のテスト."""
        # エラーが発生しないことを確認
        await media_worker.process(metadata_generated_event)
        
    @pytest.mark.asyncio
    async def test_process_unknown_event(self, media_worker):
        """未知のイベントタイプ処理のテスト."""
        unknown_event = Event(
            event_type="unknown.event",
            workflow_id="test-workflow-1",
            data={}
        )
        
        # エラーが発生しないことを確認
        await media_worker.process(unknown_event)
        
    @pytest.mark.asyncio
    async def test_handle_content_generated_no_content(self, media_worker):
        """コンテンツデータなしのコンテンツ生成イベント処理のテスト."""
        event = Event(
            event_type=EventType.CONTENT_GENERATED,
            workflow_id="test-workflow-1",
            data={}  # content データなし
        )
        
        with pytest.raises(ValueError, match="No content data provided"):
            await media_worker._handle_content_generated(event)
            
    @pytest.mark.asyncio
    async def test_handle_thumbnail_generated_no_thumbnail(self, media_worker, event_bus):
        """サムネイルデータなしのサムネイル生成イベント処理のテスト."""
        media_worker.event_bus = event_bus
        
        event = Event(
            event_type=EventType.THUMBNAIL_GENERATED,
            workflow_id="test-workflow-1",
            data={}  # thumbnail データなし
        )
        
        # エラーは発生せず、警告ログが出力される
        await media_worker._handle_thumbnail_generated(event)
        assert event_bus.publish.call_count == 0
        
    def test_extract_images_from_content(self, media_worker):
        """コンテンツからの画像抽出のテスト."""
        content = """これはテストコンテンツです。

```mermaid
graph TD
    A --> B
```

<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" />
</svg>

![diagram](test.drawio.png)

終了です。"""
        
        images = media_worker._extract_images_from_content(content)
        
        assert len(images) == 3
        
        # Mermaid図
        mermaid_image = next(img for img in images if img['type'] == 'mermaid')
        assert 'graph TD' in mermaid_image['content']
        
        # SVG画像
        svg_image = next(img for img in images if img['type'] == 'svg')
        assert '<svg' in svg_image['content']
        
        # DrawIO図
        drawio_image = next(img for img in images if img['type'] == 'drawio')
        assert 'test.drawio.png' in drawio_image['content']
        
    def test_extract_svg_images(self, media_worker):
        """SVG画像抽出のテスト."""
        content = """テキストです。
<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="red" />
</svg>
もっとテキスト。
<svg viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" />
</svg>
終了。"""
        
        svg_images = media_worker._extract_svg_images(content)
        
        assert len(svg_images) == 2
        assert 'circle' in svg_images[0]['content']
        assert 'rect' in svg_images[1]['content']
        for svg in svg_images:
            assert svg['type'] == 'svg'
            assert 'reference' in svg
            
    def test_extract_mermaid_diagrams(self, media_worker):
        """Mermaid図抽出のテスト."""
        content = """テキストです。
```mermaid
graph TD
    A[開始] --> B[処理]
    B --> C[終了]
```
もっとテキスト。
```mermaid
sequenceDiagram
    Alice->>Bob: Hello
    Bob-->>Alice: Hi
```
終了。"""
        
        mermaid_images = media_worker._extract_mermaid_diagrams(content)
        
        assert len(mermaid_images) == 2
        assert 'graph TD' in mermaid_images[0]['content']
        assert 'sequenceDiagram' in mermaid_images[1]['content']
        for mermaid in mermaid_images:
            assert mermaid['type'] == 'mermaid'
            assert 'reference' in mermaid
            
    def test_extract_drawio_diagrams(self, media_worker):
        """DrawIO図抽出のテスト."""
        content = """テキストです。
![図1](diagram1.drawio.png)
もっとテキスト。
![複雑な図](complex_diagram.drawio.svg)
![図](simple.drawio)
終了。"""
        
        drawio_images = media_worker._extract_drawio_diagrams(content)
        
        assert len(drawio_images) == 3
        assert 'diagram1.drawio.png' in drawio_images[0]['content']
        assert 'complex_diagram.drawio.svg' in drawio_images[1]['content']
        assert 'simple.drawio' in drawio_images[2]['content']
        for drawio in drawio_images:
            assert drawio['type'] == 'drawio'
            assert 'reference' in drawio
            
    @pytest.mark.asyncio
    async def test_convert_image(self, media_worker):
        """画像変換のテスト."""
        # SVG変換
        svg_result = await media_worker._convert_image(ImageType.SVG, "<svg></svg>")
        assert svg_result is not None
        assert isinstance(svg_result, bytes)
        
        # Mermaid変換
        mermaid_result = await media_worker._convert_image(ImageType.MERMAID, "graph TD; A-->B")
        assert mermaid_result is not None
        assert isinstance(mermaid_result, bytes)
        
        # DrawIO変換
        drawio_result = await media_worker._convert_image(ImageType.DRAWIO, "test.drawio")
        assert drawio_result is not None
        assert isinstance(drawio_result, bytes)
        
        # サポートされていないタイプ
        unsupported_result = await media_worker._convert_image(ImageType.JPG, "test")
        assert unsupported_result is None
        
    @pytest.mark.asyncio
    async def test_convert_svg_to_png(self, media_worker):
        """SVGからPNGへの変換のテスト."""
        svg_content = '<svg width="100" height="100"><circle cx="50" cy="50" r="40" /></svg>'
        
        result = await media_worker._convert_svg_to_png(svg_content)
        
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        
    @pytest.mark.asyncio
    async def test_convert_mermaid_to_png(self, media_worker):
        """MermaidからPNGへの変換のテスト."""
        mermaid_content = "graph TD\n    A[開始] --> B[処理]\n    B --> C[終了]"
        
        result = await media_worker._convert_mermaid_to_png(mermaid_content)
        
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        
    @pytest.mark.asyncio
    async def test_convert_drawio_to_png(self, media_worker):
        """DrawIOからPNGへの変換のテスト."""
        drawio_url = "https://example.com/diagram.drawio"
        
        result = await media_worker._convert_drawio_to_png(drawio_url)
        
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        
    @pytest.mark.asyncio
    async def test_upload_to_s3(self, media_worker):
        """S3アップロードのテスト."""
        image_data = b"fake_image_data"
        workflow_id = "test-workflow"
        filename = "test_image.png"
        
        s3_url = await media_worker._upload_to_s3(image_data, workflow_id, filename)
        
        assert s3_url is not None
        assert "test-bucket" in s3_url
        assert workflow_id in s3_url
        assert filename in s3_url
        assert s3_url.startswith("https://")
        
    @pytest.mark.asyncio
    async def test_process_content_images(self, media_worker):
        """コンテンツ画像処理のテスト."""
        content_data = {
            "type": "article",
            "content": """テスト記事です。

```mermaid
graph TD
    A --> B
```

<svg width="100" height="100">
  <circle cx="50" cy="50" r="40" />
</svg>

終了です。"""
        }
        
        updated_content, processed_images = await media_worker._process_content_images(
            content_data, "test-workflow"
        )
        
        assert processed_images is not None
        assert len(processed_images) == 2  # Mermaid + SVG
        
        assert updated_content is not None
        assert "s3.amazonaws.com" in updated_content['content']
        
        # 処理済み画像の確認
        for img in processed_images:
            assert isinstance(img, ProcessedImage)
            assert img.format == "png"
            assert img.metadata is not None
            assert 's3_url' in img.metadata
            
    @pytest.mark.asyncio
    async def test_process_content_images_no_images(self, media_worker):
        """画像のないコンテンツ処理のテスト."""
        content_data = {
            "type": "article",
            "content": "これは普通のテキストです。画像はありません。"
        }
        
        updated_content, processed_images = await media_worker._process_content_images(
            content_data, "test-workflow"
        )
        
        assert updated_content is None
        assert processed_images == []
        
    @pytest.mark.asyncio
    async def test_process_single_image(self, media_worker):
        """単一画像処理のテスト."""
        image_info = {
            'type': 'svg',
            'content': '<svg width="100" height="100"><circle cx="50" cy="50" r="40" /></svg>',
            'reference': '<svg>...</svg>'
        }
        
        result = await media_worker._process_single_image(image_info, "test-workflow", 0)
        
        assert result is not None
        assert isinstance(result, ProcessedImage)
        assert result.original_type == ImageType.SVG
        assert result.format == "png"
        assert result.metadata is not None
        assert 's3_url' in result.metadata
        
    @pytest.mark.asyncio
    async def test_generate_thumbnail_image(self, media_worker):
        """サムネイル画像生成のテスト."""
        thumbnail_data = {
            "title": "第1章 テスト",
            "style": "modern",
            "color_scheme": "blue",
            "dimensions": {
                "width": 1200,
                "height": 630
            }
        }
        
        result = await media_worker._generate_thumbnail_image(thumbnail_data, "test-workflow")
        
        assert result is not None
        assert isinstance(result, ProcessedImage)
        assert result.original_type == ImageType.PNG
        assert result.width == 1200
        assert result.height == 630
        assert result.metadata is not None
        assert result.metadata['title'] == "第1章 テスト"
        
    @pytest.mark.asyncio
    async def test_create_thumbnail_placeholder(self, media_worker):
        """サムネイルプレースホルダー作成のテスト."""
        title = "テストタイトル"
        style = "modern"
        color_scheme = "blue"
        dimensions = {"width": 800, "height": 600}
        
        result = await media_worker._create_thumbnail_placeholder(
            title, style, color_scheme, dimensions
        )
        
        assert result is not None
        assert isinstance(result, bytes)
        assert len(result) > 0
        
    def test_get_supported_image_types(self, media_worker):
        """サポート画像タイプ取得のテスト."""
        supported_types = media_worker.get_supported_image_types()
        
        assert isinstance(supported_types, list)
        assert ImageType.SVG in supported_types
        assert ImageType.MERMAID in supported_types
        assert ImageType.DRAWIO in supported_types
        
    def test_get_processing_stats(self, media_worker):
        """処理統計取得のテスト."""
        stats = media_worker.get_processing_stats()
        
        assert isinstance(stats, dict)
        assert 'images_processed' in stats
        assert 'total_size_processed' in stats
        assert 'average_processing_time' in stats
        assert 'supported_formats' in stats
        assert isinstance(stats['supported_formats'], list)
        
    @pytest.mark.asyncio
    async def test_image_processing_error_handling(self, media_worker):
        """画像処理エラーハンドリングのテスト."""
        # 不正な画像タイプでエラーをシミュレート
        image_info = {
            'type': 'invalid',  # 不正なタイプ
            'content': 'test',
            'reference': 'test'
        }
        
        # エラーが発生してもNoneが返される
        result = await media_worker._process_single_image(image_info, "test-workflow", 0)
        assert result is None
        
    def test_image_type_enum(self):
        """ImageType列挙型のテスト."""
        assert ImageType.SVG.value == "svg"
        assert ImageType.MERMAID.value == "mermaid"
        assert ImageType.DRAWIO.value == "drawio"
        assert ImageType.PNG.value == "png"
        assert ImageType.JPG.value == "jpg"
        assert ImageType.WEBP.value == "webp"
        
    def test_image_processing_request(self):
        """ImageProcessingRequestデータ構造のテスト."""
        request = ImageProcessingRequest(
            image_type=ImageType.SVG,
            content="<svg></svg>",
            options={"quality": 100},
            output_format="png"
        )
        
        assert request.image_type == ImageType.SVG
        assert request.content == "<svg></svg>"
        assert request.options["quality"] == 100
        assert request.output_format == "png"
        
    def test_processed_image(self):
        """ProcessedImageデータ構造のテスト."""
        processed = ProcessedImage(
            original_type=ImageType.SVG,
            processed_data=b"image_data",
            format="png",
            width=800,
            height=600,
            file_size=1024,
            metadata={"s3_url": "https://example.com/image.png"}
        )
        
        assert processed.original_type == ImageType.SVG
        assert processed.processed_data == b"image_data"
        assert processed.format == "png"
        assert processed.width == 800
        assert processed.height == 600
        assert processed.file_size == 1024
        assert processed.metadata["s3_url"] == "https://example.com/image.png" 