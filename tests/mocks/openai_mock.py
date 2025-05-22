from unittest.mock import MagicMock
import base64

class OpenAIMock:
    """OpenAI APIのモッククラス"""
    
    def __init__(self, error=False, image_quality="standard"):
        self.mock = MagicMock()
        self.usage_log = []
        
        if error:
            self.mock.optimize_template.side_effect = Exception("テンプレート最適化エラー")
            self.mock.generate_image.side_effect = Exception("画像生成エラー")
        else:
            self.mock.optimize_template.return_value = """
model: dall-e-3
prompt: |
  日本のイラストスタイルで、プログラミングする様子を描いた画像。
  色彩豊かで明るい雰囲気の画像。
size: 1024x1024
quality: standard
style: natural
"""
            # ダミー画像データ（1x1の透明PNG）
            dummy_png_data = base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
            )
            self.mock.generate_image.return_value = dummy_png_data
        
        def log_usage(model, tokens, image_size, quality):
            self.usage_log.append({
                "model": model,
                "tokens": tokens,
                "image_size": image_size,
                "quality": quality
            })
        
        self.mock.log_usage.side_effect = log_usage
    
    def get_mock(self):
        return self.mock
        
    def get_usage_log(self):
        return self.usage_log 