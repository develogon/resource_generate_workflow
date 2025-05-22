from unittest.mock import MagicMock

class S3Mock:
    """AWS S3 APIのモッククラス"""
    
    def __init__(self, error=False):
        self.mock = MagicMock()
        
        if error:
            self.mock.upload_file.side_effect = Exception("S3アップロードエラー")
            self.mock.get_public_url.side_effect = Exception("S3 URL取得エラー")
        else:
            self.mock.upload_file.return_value = "generated/images/test-image-123.png"
            self.mock.get_public_url.return_value = "https://example-bucket.s3.amazonaws.com/generated/images/test-image-123.png"
    
    def get_mock(self):
        return self.mock 