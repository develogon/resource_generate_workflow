from unittest.mock import MagicMock

class GitHubMock:
    """GitHub APIのモッククラス"""
    
    def __init__(self, error=False):
        self.mock = MagicMock()
        
        if error:
            self.mock.push_file.side_effect = Exception("GitHubプッシュエラー")
            self.mock.create_pr.side_effect = Exception("GitHubプルリクエスト作成エラー")
        else:
            self.mock.push_file.return_value = {
                "commit_url": "https://github.com/example/repo/commit/abc123",
                "file_url": "https://github.com/example/repo/blob/main/path/to/file.md"
            }
            self.mock.create_pr.return_value = {
                "pr_url": "https://github.com/example/repo/pull/1",
                "pr_number": 1
            }
    
    def get_mock(self):
        return self.mock 