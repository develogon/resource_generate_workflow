import pytest
from unittest.mock import patch, MagicMock

from services.github import GitHubService


class TestGitHubService:
    """GitHub APIサービスのテストクラス"""

    @pytest.fixture
    def mock_config(self):
        """テスト用の設定"""
        return {
            "github": {
                "token": "test_github_token",
                "repo_owner": "test_owner",
                "repo_name": "test_repo",
                "base_branch": "main"
            }
        }

    @pytest.fixture
    def github_service(self, mock_config):
        """GitHub APIサービスのインスタンス"""
        with patch('services.github.Github') as mock_github:
            # モックリポジトリの設定
            mock_repo = MagicMock()
            mock_github.return_value.get_repo.return_value = mock_repo
            
            service = GitHubService(mock_config)
            service._repo = mock_repo  # リポジトリを直接設定
            return service

    def test_init(self, mock_config):
        """初期化のテスト"""
        with patch('services.github.Github') as mock_github:
            # GitHubインスタンスがトークンで初期化されることを確認
            service = GitHubService(mock_config)
            mock_github.assert_called_once_with("test_github_token")
            
            # リポジトリが取得されることを確認
            mock_github.return_value.get_repo.assert_called_once_with("test_owner/test_repo")

    def test_push_file(self, github_service):
        """ファイルプッシュのテスト"""
        # モックの設定
        mock_repo = github_service._repo
        mock_content = MagicMock()
        mock_repo.get_contents.return_value = mock_content
        mock_content.path = "test_path"
        mock_content.sha = "test_sha"
        
        # ファイルプッシュの実行
        result = github_service.push_file(
            path="test_path",
            content="test_content",
            commit_message="テストコミット",
            branch="test_branch"
        )
        
        # リポジトリのupdate_fileメソッドが呼ばれたことを確認
        mock_repo.update_file.assert_called_once_with(
            path="test_path",
            message="テストコミット",
            content="test_content",
            sha="test_sha",
            branch="test_branch"
        )
        
        # 成功したことを確認
        assert result is True

    def test_push_new_file(self, github_service):
        """新規ファイルプッシュのテスト"""
        # モックの設定 - ファイルが存在しない場合
        mock_repo = github_service._repo
        mock_repo.get_contents.side_effect = Exception("Not found")
        
        # ファイルプッシュの実行
        result = github_service.push_file(
            path="new_file.txt",
            content="新規ファイルの内容",
            commit_message="新規ファイル追加",
            branch="test_branch"
        )
        
        # リポジトリのcreate_fileメソッドが呼ばれたことを確認
        mock_repo.create_file.assert_called_once_with(
            path="new_file.txt",
            message="新規ファイル追加",
            content="新規ファイルの内容",
            branch="test_branch"
        )
        
        # 成功したことを確認
        assert result is True

    def test_create_branch(self, github_service):
        """ブランチ作成のテスト"""
        # モックの設定
        mock_repo = github_service._repo
        mock_ref = MagicMock()
        mock_repo.get_git_ref.return_value = mock_ref
        mock_ref.object.sha = "base_commit_sha"
        
        # ブランチ作成の実行
        branch_name = "new-branch"
        result = github_service.create_branch(branch_name)
        
        # 基準ブランチのリファレンスが取得されたことを確認
        mock_repo.get_git_ref.assert_called_once_with("heads/main")
        
        # 新しいブランチが作成されたことを確認
        mock_repo.create_git_ref.assert_called_once_with(
            ref=f"refs/heads/{branch_name}",
            sha="base_commit_sha"
        )
        
        # 成功したことを確認
        assert result is True

    def test_create_commit(self, github_service):
        """コミット作成のテスト"""
        # モックの設定
        mock_repo = github_service._repo
        
        # コミット作成の実行
        files = [
            {"path": "file1.txt", "content": "ファイル1の内容"},
            {"path": "file2.txt", "content": "ファイル2の内容"}
        ]
        result = github_service.create_commit(
            message="テストコミット",
            files=files,
            branch="test_branch"
        )
        
        # 各ファイルに対してcreate_fileが呼ばれたことを確認
        assert mock_repo.create_file.call_count == 2
        
        # 最初のファイルの引数を確認
        first_call_args = mock_repo.create_file.call_args_list[0][1]
        assert first_call_args["path"] == "file1.txt"
        assert first_call_args["content"] == "ファイル1の内容"
        assert first_call_args["message"] == "テストコミット"
        assert first_call_args["branch"] == "test_branch"
        
        # 成功したことを確認
        assert result is True

    @patch('services.github.time.sleep')
    def test_handle_conflict(self, mock_sleep, github_service):
        """コンフリクト処理のテスト"""
        # コンフリクト例外の設定
        conflict_error = Exception("Conflict error")
        
        # エラー発生→成功のシーケンス
        github_service._repo.update_file.side_effect = [
            conflict_error,  # 1回目: コンフリクト
            {"commit": {"sha": "success_sha"}}  # 2回目: 成功
        ]
        
        # コンテンツ取得のモック
        mock_content = MagicMock()
        mock_content.path = "test_path"
        mock_content.sha = "updated_sha"  # 2回目の取得で更新されたSHA
        
        # 1回目のget_contentsでは最初のSHAを返し、2回目では更新されたSHAを返す
        github_service._repo.get_contents.side_effect = [
            mock_content,  # 1回目
            mock_content   # 2回目（コンフリクト後）
        ]
        
        # ファイルプッシュの実行
        result = github_service.push_file(
            path="test_path",
            content="test_content",
            commit_message="テストコミット",
            branch="test_branch"
        )
        
        # sleepが呼ばれたことを確認（リトライ前の待機）
        mock_sleep.assert_called_once()
        
        # update_fileが2回呼ばれたことを確認
        assert github_service._repo.update_file.call_count == 2
        
        # 成功したことを確認
        assert result is True

    def test_verify_push_success(self, github_service):
        """プッシュ成功の検証テスト"""
        # コミット情報のモック
        mock_commit = MagicMock()
        mock_commit.sha = "test_commit_sha"
        
        # コミット履歴のモック
        mock_commits = MagicMock()
        mock_commits.reversed = [mock_commit]
        github_service._repo.get_commits.return_value = mock_commits
        
        # コミットの詳細のモック
        mock_commit_details = MagicMock()
        mock_commit_details.files = [
            {"filename": "test_file.txt", "status": "modified"}
        ]
        github_service._repo.get_commit.return_value = mock_commit_details
        
        # プッシュ検証の実行
        result = github_service.verify_push_success(
            path="test_file.txt",
            branch="test_branch"
        )
        
        # コミット履歴が取得されたことを確認
        github_service._repo.get_commits.assert_called_once_with(sha="test_branch")
        
        # 最新のコミット詳細が取得されたことを確認
        github_service._repo.get_commit.assert_called_once_with("test_commit_sha")
        
        # 検証が成功したことを確認
        assert result is True

    def test_list_files(self, github_service):
        """ファイル一覧取得のテスト"""
        # ディレクトリコンテンツのモック
        mock_dir_content = [
            MagicMock(path="dir/file1.txt", type="file"),
            MagicMock(path="dir/file2.txt", type="file"),
            MagicMock(path="dir/subdir", type="dir")
        ]
        github_service._repo.get_contents.return_value = mock_dir_content
        
        # ファイル一覧取得の実行
        files = github_service.list_files("dir", "test_branch")
        
        # ディレクトリコンテンツが取得されたことを確認
        github_service._repo.get_contents.assert_called_once_with("dir", ref="test_branch")
        
        # 結果の検証
        assert len(files) == 2  # ディレクトリは含まれない
        assert "dir/file1.txt" in files
        assert "dir/file2.txt" in files 