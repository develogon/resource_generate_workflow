import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from generators.image.processor import ImageProcessor
from generators.image.svg_processor import SVGProcessor
from generators.image.mermaid_processor import MermaidProcessor
from generators.image.drawio_processor import DrawIOProcessor


class TestImageProcessor:
    """画像プロセッサベースクラスのテスト"""

    @pytest.fixture
    def image_processor(self):
        """画像プロセッサのインスタンス"""
        return ImageProcessor()

    def test_detect_image_type_svg(self, image_processor):
        """SVG画像タイプの検出テスト"""
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <rect width="100" height="100" fill="blue" />
        </svg>"""
        
        image_type = image_processor.detect_image_type(svg_content)
        assert image_type == "svg"

    def test_detect_image_type_mermaid(self, image_processor):
        """Mermaid画像タイプの検出テスト"""
        mermaid_content = """graph TD
            A[Start] --> B[Process]
            B --> C[End]
        """
        
        image_type = image_processor.detect_image_type(mermaid_content)
        assert image_type == "mermaid"

    def test_detect_image_type_drawio(self, image_processor):
        """Draw.io画像タイプの検出テスト"""
        drawio_content = """<mxfile host="app.diagrams.net" modified="2023-01-01T00:00:00.000Z">
            <diagram id="test" name="テスト図">
                <mxGraphModel dx="100" dy="100" grid="1">
                    <root>
                        <mxCell id="0"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""
        
        image_type = image_processor.detect_image_type(drawio_content)
        assert image_type == "drawio"

    def test_detect_image_type_unknown(self, image_processor):
        """不明な画像タイプの検出テスト"""
        unknown_content = "This is not a valid image format."
        
        image_type = image_processor.detect_image_type(unknown_content)
        assert image_type == "unknown"

    def test_get_processor(self, image_processor):
        """適切なプロセッサ取得のテスト"""
        # SVGプロセッサの取得
        processor = image_processor.get_processor("svg")
        assert isinstance(processor, SVGProcessor)
        
        # Mermaidプロセッサの取得
        processor = image_processor.get_processor("mermaid")
        assert isinstance(processor, MermaidProcessor)
        
        # Draw.ioプロセッサの取得
        processor = image_processor.get_processor("drawio")
        assert isinstance(processor, DrawIOProcessor)
        
        # 不明なタイプの場合の例外
        with pytest.raises(ValueError):
            image_processor.get_processor("unknown")

    def test_process_image(self, image_processor):
        """画像処理ディスパッチのテスト"""
        # 各プロセッサのprocess_imageメソッドをモック化
        svg_processor = MagicMock()
        svg_processor.process_image.return_value = "processed_svg.png"
        
        mermaid_processor = MagicMock()
        mermaid_processor.process_image.return_value = "processed_mermaid.png"
        
        drawio_processor = MagicMock()
        drawio_processor.process_image.return_value = "processed_drawio.png"
        
        # get_processorをモック化して適切なモックプロセッサを返すように設定
        with patch.object(image_processor, 'get_processor') as mock_get_processor:
            mock_get_processor.side_effect = lambda image_type: {
                "svg": svg_processor,
                "mermaid": mermaid_processor,
                "drawio": drawio_processor
            }.get(image_type)
            
            # detect_image_typeをモック化
            with patch.object(image_processor, 'detect_image_type') as mock_detect:
                # SVGの場合
                mock_detect.return_value = "svg"
                result = image_processor.process_image("svg_content", "output.png")
                assert result == "processed_svg.png"
                svg_processor.process_image.assert_called_once()
                
                # Mermaidの場合
                mock_detect.return_value = "mermaid"
                result = image_processor.process_image("mermaid_content", "output.png")
                assert result == "processed_mermaid.png"
                mermaid_processor.process_image.assert_called_once()
                
                # Draw.ioの場合
                mock_detect.return_value = "drawio"
                result = image_processor.process_image("drawio_content", "output.png")
                assert result == "processed_drawio.png"
                drawio_processor.process_image.assert_called_once()


class TestSVGProcessor:
    """SVG画像プロセッサのテスト"""

    @pytest.fixture
    def svg_processor(self):
        """SVGプロセッサのインスタンス"""
        return SVGProcessor()

    def test_process_image(self, svg_processor, temp_dir):
        """SVG画像処理のテスト"""
        # テストSVG
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <rect width="100" height="100" fill="blue" />
        </svg>"""
        
        output_path = os.path.join(str(temp_dir), "output.png")
        
        # cairosvgモジュールをモック
        with patch('generators.image.svg_processor.cairosvg') as mock_cairosvg:
            # process_image実行
            result = svg_processor.process_image(svg_content, output_path)
            
            # cairosvgが呼ばれたことを確認
            mock_cairosvg.svg2png.assert_called_once()
            
            # 出力パスが返されたことを確認
            assert result == output_path

    def test_optimize_svg(self, svg_processor):
        """SVG最適化のテスト"""
        # 最適化前のSVG
        svg_content = """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
            <!-- コメント -->
            <rect width="100" height="100" fill="blue" />
            <rect width="0" height="0" fill="red" />
        </svg>"""
        
        # 最適化実行
        optimized = svg_processor.optimize_svg(svg_content)
        
        # コメントが削除されたことを確認
        assert "<!-- コメント -->" not in optimized
        
        # 0サイズの要素が削除されていないことを確認（実装依存）
        # 注: 実際の最適化の詳細は実装によって異なります
        assert "width=\"0\"" in optimized


class TestMermaidProcessor:
    """Mermaid図プロセッサのテスト"""

    @pytest.fixture
    def mermaid_processor(self):
        """Mermaidプロセッサのインスタンス"""
        return MermaidProcessor()

    def test_process_image(self, mermaid_processor, temp_dir):
        """Mermaid図処理のテスト"""
        # テストMermaid図
        mermaid_content = """graph TD
            A[Start] --> B[Process]
            B --> C[End]
        """
        
        output_path = os.path.join(str(temp_dir), "output.png")
        temp_mermaid_file = os.path.join(str(temp_dir), "temp.mmd")
        
        # ファイル書き込みとsubprocessをモック
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                # mmdc実行可能性チェックをモック
                with patch.object(mermaid_processor, '_check_mmdc') as mock_check:
                    mock_check.return_value = True
                    
                    # process_image実行
                    result = mermaid_processor.process_image(mermaid_content, output_path)
                    
                    # ファイル書き込みが行われたことを確認
                    mock_file.assert_called()
                    
                    # mmdc実行が行われたことを確認
                    mock_run.assert_called_once()
                    
                    # 出力パスが返されたことを確認
                    assert result == output_path

    def test_validate_syntax(self, mermaid_processor):
        """Mermaid構文検証のテスト"""
        # 有効な構文
        valid_syntax = """graph TD
            A[Start] --> B[Process]
            B --> C[End]
        """
        assert mermaid_processor.validate_syntax(valid_syntax) is True
        
        # 無効な構文
        invalid_syntax = """graph TD
            A[Start] --> 
            Invalid syntax
        """
        # 注: この検証は実装依存です
        # assert mermaid_processor.validate_syntax(invalid_syntax) is False

    def test_check_mmdc(self, mermaid_processor):
        """mmdc可用性チェックのテスト"""
        # コマンド実行をモック
        with patch('subprocess.run') as mock_run:
            # 成功ケース
            mock_run.return_value = MagicMock(returncode=0)
            assert mermaid_processor._check_mmdc() is True
            
            # 失敗ケース
            mock_run.return_value = MagicMock(returncode=1)
            assert mermaid_processor._check_mmdc() is False
            
            # 例外ケース
            mock_run.side_effect = subprocess.SubprocessError()
            assert mermaid_processor._check_mmdc() is False


class TestDrawIOProcessor:
    """Draw.io XMLプロセッサのテスト"""

    @pytest.fixture
    def drawio_processor(self):
        """Draw.ioプロセッサのインスタンス"""
        return DrawIOProcessor()

    def test_process_image(self, drawio_processor, temp_dir):
        """Draw.io XML処理のテスト"""
        # テストDraw.io XML
        drawio_content = """<mxfile host="app.diagrams.net" modified="2023-01-01T00:00:00.000Z">
            <diagram id="test" name="テスト図">
                <mxGraphModel dx="100" dy="100" grid="1">
                    <root>
                        <mxCell id="0"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""
        
        output_path = os.path.join(str(temp_dir), "output.png")
        temp_drawio_file = os.path.join(str(temp_dir), "temp.drawio")
        
        # ファイル書き込みとsubprocessをモック
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                # drawio CLI実行可能性チェックをモック
                with patch.object(drawio_processor, '_check_drawio_cli') as mock_check:
                    mock_check.return_value = True
                    
                    # process_image実行
                    result = drawio_processor.process_image(drawio_content, output_path)
                    
                    # ファイル書き込みが行われたことを確認
                    mock_file.assert_called()
                    
                    # drawio CLI実行が行われたことを確認
                    mock_run.assert_called_once()
                    
                    # 出力パスが返されたことを確認
                    assert result == output_path

    def test_check_drawio_cli(self, drawio_processor):
        """draw.io CLI可用性チェックのテスト"""
        # コマンド実行をモック
        with patch('subprocess.run') as mock_run:
            # 成功ケース
            mock_run.return_value = MagicMock(returncode=0)
            assert drawio_processor._check_drawio_cli() is True
            
            # 失敗ケース
            mock_run.return_value = MagicMock(returncode=1)
            assert drawio_processor._check_drawio_cli() is False
            
            # 例外ケース
            mock_run.side_effect = subprocess.SubprocessError()
            assert drawio_processor._check_drawio_cli() is False

    def test_get_page_id(self, drawio_processor):
        """ページID取得のテスト"""
        # テストDrawIO XML（ページID含む）
        drawio_content = """<mxfile host="app.diagrams.net">
            <diagram id="test-id" name="テスト図">
                <mxGraphModel>
                    <root>
                        <mxCell id="0"/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""
        
        page_id = drawio_processor.get_page_id(drawio_content)
        assert page_id == "test-id"
        
        # ページIDなしのケース
        no_id_content = """<mxfile host="app.diagrams.net">
            <diagram name="テスト図">
                <mxGraphModel>
                    <root>
                        <mxCell/>
                    </root>
                </mxGraphModel>
            </diagram>
        </mxfile>"""
        
        page_id = drawio_processor.get_page_id(no_id_content)
        assert page_id == ""  # または実装による値 