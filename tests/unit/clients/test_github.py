"""GitHubクライアントのテスト"""

import base64
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from src.clients.github import (
    GitHubClient,
    GitHubError,
    RepositoryNotFoundError,
    FileNotFoundError
)


@pytest.fixture
def github_client():
    """GitHubクライアントのフィクスチャ"""
    return GitHubClient(
        token="test_token",
        owner="test_owner",
        repo="test_repo"
    )


class TestGitHubClient:
    """GitHubクライアントのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, github_client):
        """初期化のテスト"""
        assert github_client.token == "test_token"
        assert github_client.owner == "test_owner"
        assert github_client.repo == "test_repo"
        assert github_client.base_url == "https://api.github.com"
        assert "Authorization" in github_client.headers
        assert github_client.headers["Authorization"] == "token test_token"
        assert github_client.headers["Accept"] == "application/vnd.github.v3+json"
        
    @pytest.mark.asyncio
    async def test_get_repository_success(self, github_client):
        """リポジトリ情報取得成功のテスト"""
        mock_response = {
            "id": 123,
            "name": "test_repo",
            "full_name": "test_owner/test_repo",
            "private": False
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.get_repository()
            
            assert result == mock_response
            mock_request.assert_called_once_with("GET", "/repos/test_owner/test_repo")
            
    @pytest.mark.asyncio
    async def test_get_repository_not_found(self, github_client):
        """リポジトリが見つからない場合のテスト"""
        with patch.object(github_client, '_request', side_effect=Exception("404")) as mock_request:
            with pytest.raises(RepositoryNotFoundError):
                await github_client.get_repository()
                
    @pytest.mark.asyncio
    async def test_get_file_content_success(self, github_client):
        """ファイル内容取得成功のテスト"""
        content = "Hello, World!"
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        mock_response = {
            "name": "test.txt",
            "path": "test.txt",
            "sha": "abc123",
            "content": encoded_content,
            "encoding": "base64"
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.get_file_content("test.txt", "main")
            
            assert result["decoded_content"] == content
            assert result["sha"] == "abc123"
            mock_request.assert_called_once_with(
                "GET",
                "/repos/test_owner/test_repo/contents/test.txt",
                params={"ref": "main"}
            )
            
    @pytest.mark.asyncio
    async def test_get_file_content_not_found(self, github_client):
        """ファイルが見つからない場合のテスト"""
        with patch.object(github_client, '_request', side_effect=Exception("404")):
            with pytest.raises(FileNotFoundError):
                await github_client.get_file_content("nonexistent.txt")
                
    @pytest.mark.asyncio
    async def test_create_file_success(self, github_client):
        """ファイル作成成功のテスト"""
        content = "New file content"
        mock_response = {
            "content": {"sha": "new123"},
            "commit": {"sha": "commit123"}
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.create_or_update_file(
                path="new_file.txt",
                content=content,
                message="Create new file",
                branch="main"
            )
            
            assert result == mock_response
            
            # リクエストの引数を確認
            args, kwargs = mock_request.call_args
            assert args[0] == "PUT"
            assert args[1] == "/repos/test_owner/test_repo/contents/new_file.txt"
            
            # Base64エンコードされたコンテンツを確認
            expected_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            assert kwargs["json"]["content"] == expected_content
            assert kwargs["json"]["message"] == "Create new file"
            assert kwargs["json"]["branch"] == "main"
            assert "sha" not in kwargs["json"]  # 新規作成時はSHAなし
            
    @pytest.mark.asyncio
    async def test_update_file_success(self, github_client):
        """ファイル更新成功のテスト"""
        content = "Updated file content"
        sha = "existing123"
        
        with patch.object(github_client, '_request', return_value={}) as mock_request:
            await github_client.create_or_update_file(
                path="existing_file.txt",
                content=content,
                message="Update file",
                branch="main",
                sha=sha
            )
            
            # リクエストの引数を確認
            args, kwargs = mock_request.call_args
            assert kwargs["json"]["sha"] == sha  # 更新時はSHAあり
            
    @pytest.mark.asyncio
    async def test_delete_file_success(self, github_client):
        """ファイル削除成功のテスト"""
        sha = "delete123"
        mock_response = {"commit": {"sha": "commit456"}}
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.delete_file(
                path="delete_file.txt",
                message="Delete file",
                sha=sha,
                branch="main"
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert args[0] == "DELETE"
            assert kwargs["json"]["sha"] == sha
            assert kwargs["json"]["message"] == "Delete file"
            
    @pytest.mark.asyncio
    async def test_list_directory_contents_success(self, github_client):
        """ディレクトリ内容一覧取得成功のテスト"""
        mock_response = [
            {"name": "file1.txt", "type": "file"},
            {"name": "subdir", "type": "dir"}
        ]
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.list_directory_contents("src", "main")
            
            assert result == mock_response
            mock_request.assert_called_once_with(
                "GET",
                "/repos/test_owner/test_repo/contents/src",
                params={"ref": "main"}
            )
            
    @pytest.mark.asyncio
    async def test_list_directory_contents_single_file(self, github_client):
        """単一ファイルの場合のテスト"""
        mock_response = {"name": "single_file.txt", "type": "file"}
        
        with patch.object(github_client, '_request', return_value=mock_response):
            result = await github_client.list_directory_contents("single_file.txt")
            
            # 単一ファイルもリストに変換される
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0] == mock_response
            
    @pytest.mark.asyncio
    async def test_create_branch_success(self, github_client):
        """ブランチ作成成功のテスト"""
        mock_ref_response = {
            "object": {"sha": "main_sha123"}
        }
        mock_create_response = {
            "ref": "refs/heads/feature-branch",
            "object": {"sha": "main_sha123"}
        }
        
        with patch.object(github_client, '_request') as mock_request:
            mock_request.side_effect = [mock_ref_response, mock_create_response]
            
            result = await github_client.create_branch("feature-branch", "main")
            
            assert result == mock_create_response
            
            # 2回のリクエストが呼ばれることを確認
            assert mock_request.call_count == 2
            
            # 1回目: 元ブランチのSHA取得
            first_call = mock_request.call_args_list[0]
            assert first_call[0][0] == "GET"
            assert "git/refs/heads/main" in first_call[0][1]
            
            # 2回目: 新ブランチ作成
            second_call = mock_request.call_args_list[1]
            assert second_call[0][0] == "POST"
            assert "git/refs" in second_call[0][1]
            assert second_call[1]["json"]["ref"] == "refs/heads/feature-branch"
            assert second_call[1]["json"]["sha"] == "main_sha123"
            
    @pytest.mark.asyncio
    async def test_create_pull_request_success(self, github_client):
        """プルリクエスト作成成功のテスト"""
        mock_response = {
            "id": 1,
            "number": 1,
            "title": "Test PR",
            "state": "open"
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.create_pull_request(
                title="Test PR",
                head="feature-branch",
                base="main",
                body="Test description",
                draft=True
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert "/pulls" in args[1]
            assert kwargs["json"]["title"] == "Test PR"
            assert kwargs["json"]["head"] == "feature-branch"
            assert kwargs["json"]["base"] == "main"
            assert kwargs["json"]["body"] == "Test description"
            assert kwargs["json"]["draft"] is True
            
    @pytest.mark.asyncio
    async def test_create_issue_success(self, github_client):
        """イシュー作成成功のテスト"""
        mock_response = {
            "id": 1,
            "number": 1,
            "title": "Test Issue",
            "state": "open"
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.create_issue(
                title="Test Issue",
                body="Issue description",
                labels=["bug", "enhancement"],
                assignees=["user1", "user2"]
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert kwargs["json"]["title"] == "Test Issue"
            assert kwargs["json"]["body"] == "Issue description"
            assert kwargs["json"]["labels"] == ["bug", "enhancement"]
            assert kwargs["json"]["assignees"] == ["user1", "user2"]
            
    @pytest.mark.asyncio
    async def test_get_commits_success(self, github_client):
        """コミット一覧取得成功のテスト"""
        mock_response = [
            {"sha": "commit1", "commit": {"message": "First commit"}},
            {"sha": "commit2", "commit": {"message": "Second commit"}}
        ]
        
        since_date = datetime(2023, 1, 1)
        until_date = datetime(2023, 12, 31)
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.get_commits(
                sha="main",
                path="src/",
                since=since_date,
                until=until_date,
                per_page=50
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            params = kwargs["params"]
            assert params["sha"] == "main"
            assert params["path"] == "src/"
            assert params["since"] == since_date.isoformat()
            assert params["until"] == until_date.isoformat()
            assert params["per_page"] == 50
            
    @pytest.mark.asyncio
    async def test_get_releases_success(self, github_client):
        """リリース一覧取得成功のテスト"""
        mock_response = [
            {"id": 1, "tag_name": "v1.0.0", "name": "Release 1.0.0"},
            {"id": 2, "tag_name": "v1.1.0", "name": "Release 1.1.0"}
        ]
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.get_releases(per_page=10)
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert "/releases" in args[1]
            assert kwargs["params"]["per_page"] == 10
            
    @pytest.mark.asyncio
    async def test_create_release_success(self, github_client):
        """リリース作成成功のテスト"""
        mock_response = {
            "id": 1,
            "tag_name": "v2.0.0",
            "name": "Release 2.0.0",
            "draft": False
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.create_release(
                tag_name="v2.0.0",
                name="Release 2.0.0",
                body="Release notes",
                draft=False,
                prerelease=True,
                target_commitish="develop"
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            json_data = kwargs["json"]
            assert json_data["tag_name"] == "v2.0.0"
            assert json_data["name"] == "Release 2.0.0"
            assert json_data["body"] == "Release notes"
            assert json_data["draft"] is False
            assert json_data["prerelease"] is True
            assert json_data["target_commitish"] == "develop"
            
    @pytest.mark.asyncio
    async def test_search_code_success(self, github_client):
        """コード検索成功のテスト"""
        mock_response = {
            "total_count": 2,
            "items": [
                {"name": "file1.py", "path": "src/file1.py"},
                {"name": "file2.py", "path": "src/file2.py"}
            ]
        }
        
        with patch.object(github_client, '_request', return_value=mock_response) as mock_request:
            result = await github_client.search_code(
                query="def main",
                sort="updated",
                order="asc",
                per_page=20
            )
            
            assert result == mock_response
            
            args, kwargs = mock_request.call_args
            assert "/search/code" in args[1]
            params = kwargs["params"]
            assert "def main repo:test_owner/test_repo" in params["q"]
            assert params["sort"] == "updated"
            assert params["order"] == "asc"
            assert params["per_page"] == 20
            
    @pytest.mark.asyncio
    async def test_health_check_success(self, github_client):
        """ヘルスチェック成功のテスト"""
        with patch.object(github_client, 'get_repository', return_value={}):
            is_healthy = await github_client.health_check()
            assert is_healthy is True
            
    @pytest.mark.asyncio
    async def test_health_check_failure(self, github_client):
        """ヘルスチェック失敗のテスト"""
        with patch.object(github_client, 'get_repository', side_effect=Exception("Connection failed")):
            is_healthy = await github_client.health_check()
            assert is_healthy is False
            
    @pytest.mark.asyncio
    async def test_stats_tracking(self, github_client):
        """統計情報追跡のテスト"""
        with patch.object(github_client, '_request', return_value={}):
            # ファイル読み取り
            await github_client.get_file_content("test.txt")
            
            # ファイル書き込み
            await github_client.create_or_update_file("test.txt", "content", "message")
            
            # ファイル削除
            await github_client.delete_file("test.txt", "delete", "sha123")
            
            # ブランチ作成
            with patch.object(github_client, '_request') as mock_request:
                mock_request.side_effect = [
                    {"object": {"sha": "sha123"}},  # ref取得
                    {}  # ブランチ作成
                ]
                await github_client.create_branch("feature")
                
            # プルリクエスト作成
            await github_client.create_pull_request("title", "head", "base")
            
            # イシュー作成
            await github_client.create_issue("title")
            
            # リリース作成
            await github_client.create_release("v1.0.0")
            
            assert github_client.stats['file_reads'] == 1
            assert github_client.stats['file_writes'] == 1
            assert github_client.stats['file_deletions'] == 1
            assert github_client.stats['branches_created'] == 1
            assert github_client.stats['pull_requests_created'] == 1
            assert github_client.stats['issues_created'] == 1
            assert github_client.stats['releases_created'] == 1
            
    @pytest.mark.asyncio
    async def test_error_handling(self, github_client):
        """エラーハンドリングのテスト"""
        # 一般的なGitHubエラー
        with patch.object(github_client, '_request', side_effect=Exception("API Error")):
            with pytest.raises(GitHubError):
                await github_client.create_or_update_file("test.txt", "content", "message") 