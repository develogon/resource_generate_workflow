from unittest.mock import MagicMock

class ClaudeMock:
    """Claude APIのモッククラス"""
    
    def __init__(self, response_type="text", error=False):
        self.mock = MagicMock()
        
        if error:
            self.mock.call_api.side_effect = Exception("API呼び出しエラー")
        else:
            if response_type == "text":
                self.mock.call_api.return_value = {
                    "content": [
                        {
                            "type": "text",
                            "text": "# 生成されたコンテンツ\n\nこれはClaudeによって生成されたテスト用のコンテンツです。"
                        }
                    ]
                }
            elif response_type == "yaml":
                self.mock.call_api.return_value = {
                    "content": [
                        {
                            "type": "text",
                            "text": """```yaml
title: テストタイトル
sections:
  - title: セクション1
    paragraphs:
      - type: text
        content: これはテスト用のパラグラフです。
```"""
                        }
                    ]
                }
            elif response_type == "json":
                self.mock.call_api.return_value = {
                    "content": [
                        {
                            "type": "text",
                            "text": """```json
{
  "title": "テストタイトル",
  "sections": [
    {
      "title": "セクション1",
      "content": "これはテスト用のコンテンツです。"
    }
  ]
}
```"""
                        }
                    ]
                }
            elif response_type == "csv":
                self.mock.call_api.return_value = {
                    "content": [
                        {
                            "type": "text",
                            "text": """```csv
content,hashtags,image_url
テスト投稿内容1,#テスト #サンプル,
テスト投稿内容2,#テスト #プログラミング,https://example.com/image.jpg
```"""
                        }
                    ]
                }
        
        self.mock.extract_content.return_value = "抽出されたコンテンツ"
        
    def get_mock(self):
        return self.mock 