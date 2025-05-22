import pytest
import os
import io
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート（まだ実装されていない場合はコメントアウト）
# from app.clients.s3 import S3Client
# from app.clients.github import GitHubClient
# from app.workflow.task_manager import TaskManager

class TestStorageIntegration:
    """外部ストレージとの連携テスト"""
    
    @pytest.fixture
    def setup_integration(self, tmp_path):
        """統合テスト用の環境セットアップ"""
        # テスト用の一時ディレクトリを作成
        base_dir = tmp_path / "storage_test"
        base_dir.mkdir()
        
        # テスト用のファイルを作成
        test_file = base_dir / "test.md"
        with open(test_file, "w") as f:
            f.write("# テスト用マークダウン\n\nこれはテスト用のファイルです。")
        
        # 画像用のバイナリデータ
        image_data = b"dummy_image_data"
        test_image = base_dir / "test.png"
        with open(test_image, "wb") as f:
            f.write(image_data)
        
        # テスト環境変数を設定
        os.environ["AWS_ACCESS_KEY_ID"] = "dummy_aws_key_id"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy_aws_secret"
        os.environ["S3_BUCKET_NAME"] = "dummy-bucket"
        os.environ["GITHUB_TOKEN"] = "dummy_github_token"
        
        # テスト後のクリーンアップを設定
        yield {
            "base_dir": base_dir,
            "test_file": test_file,
            "test_image": test_image,
            "image_data": image_data
        }
        
        # 環境変数をクリーンアップ
        for key in ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "S3_BUCKET_NAME", "GITHUB_TOKEN"]:
            if key in os.environ:
                del os.environ[key]
    
    @patch("app.clients.s3.S3Client")
    @patch("app.workflow.task_manager.TaskManager")
    def test_s3_upload_integration(self, mock_task_manager, mock_s3_client, setup_integration):
        """S3アップロードタスク統合テスト"""
        # セットアップ情報を取得
        test_image = setup_integration["test_image"]
        image_data = setup_integration["image_data"]
        
        # モックのセットアップ
        mock_s3_instance = mock_s3_client.return_value
        mock_task_manager_instance = mock_task_manager.return_value
        
        # S3アップロードのモック
        mock_s3_instance.upload_file.return_value = "images/test.png"
        mock_s3_instance.get_public_url.return_value = "https://dummy-bucket.s3.amazonaws.com/images/test.png"
        
        # タスクの作成
        s3_task = {
            "id": "task-s3-001",
            "type": "S3_UPLOAD",
            "status": "PENDING",
            "file_path": str(test_image),
            "s3_key": "images/test.png",
            "content_type": "image/png"
        }
        
        # タスク実行のシミュレーション
        # このテストは、実際のクラスが実装された後に有効化する
        # task_manager = TaskManager()
        # s3_client = S3Client(bucket_name="dummy-bucket")
        # 
        # # ファイルを読み込み
        # with open(s3_task["file_path"], "rb") as f:
        #     file_data = f.read()
        # 
        # # S3にアップロード
        # s3_key = s3_client.upload_file(file_data, s3_task["s3_key"], s3_task["content_type"])
        # 
        # # 公開URLを取得
        # image_url = s3_client.get_public_url(s3_key)
        # 
        # # タスクのメタデータ更新
        # s3_task["result"] = {
        #     "s3_key": s3_key,
        #     "url": image_url
        # }
        # 
        # # タスクを完了としてマーク
        # task_manager.complete_task(s3_task["id"], s3_task["result"])
        
        # ファイルアップロードが呼び出されたことを確認
        # mock_s3_instance.upload_file.assert_called_once()
        # upload_args, upload_kwargs = mock_s3_instance.upload_file.call_args
        # assert len(upload_args) >= 2
        # assert upload_args[1] == s3_task["s3_key"]
        # assert upload_kwargs.get("content_type") == s3_task["content_type"]
        
        # 公開URLが取得されたことを確認
        # mock_s3_instance.get_public_url.assert_called_once_with(s3_task["s3_key"])
        
        # タスクが完了としてマークされたことを確認
        # mock_task_manager_instance.complete_task.assert_called_once()
        # task_args, task_kwargs = mock_task_manager_instance.complete_task.call_args
        # assert task_args[0] == s3_task["id"]
        # assert "s3_key" in task_args[1]
        # assert "url" in task_args[1]
        pass
    
    @patch("app.clients.github.GitHubClient")
    @patch("app.workflow.task_manager.TaskManager")
    def test_github_push_integration(self, mock_task_manager, mock_github_client, setup_integration):
        """GitHub pushタスク統合テスト"""
        # セットアップ情報を取得
        test_file = setup_integration["test_file"]
        
        # モックのセットアップ
        mock_github_instance = mock_github_client.return_value
        mock_task_manager_instance = mock_task_manager.return_value
        
        # GitHubプッシュのモック
        mock_github_instance.push_file.return_value = {
            "commit_url": "https://github.com/test_owner/test_repo/commit/abc123def456",
            "path": "docs/test.md",
            "branch": "main",
            "message": "テスト用コミット"
        }
        
        # タスクの作成
        github_task = {
            "id": "task-github-001",
            "type": "GITHUB_PUSH",
            "status": "PENDING",
            "file_path": str(test_file),
            "repo_path": "docs/test.md",
            "commit_message": "テスト用コミット",
            "branch": "main"
        }
        
        # タスク実行のシミュレーション
        # このテストは、実際のクラスが実装された後に有効化する
        # task_manager = TaskManager()
        # github_client = GitHubClient(token="dummy_token", repo_owner="test_owner", repo_name="test_repo")
        # 
        # # ファイルを読み込み
        # with open(github_task["file_path"], "r") as f:
        #     file_content = f.read()
        # 
        # # GitHubにプッシュ
        # result = github_client.push_file(
        #     github_task["repo_path"], 
        #     file_content, 
        #     github_task["commit_message"], 
        #     branch=github_task["branch"]
        # )
        # 
        # # タスクのメタデータ更新
        # github_task["result"] = {
        #     "commit_url": result["commit_url"],
        #     "path": result["path"],
        #     "branch": result["branch"]
        # }
        # 
        # # タスクを完了としてマーク
        # task_manager.complete_task(github_task["id"], github_task["result"])
        
        # ファイルプッシュが呼び出されたことを確認
        # mock_github_instance.push_file.assert_called_once()
        # push_args, push_kwargs = mock_github_instance.push_file.call_args
        # assert push_args[0] == github_task["repo_path"]
        # assert push_args[2] == github_task["commit_message"]
        # assert push_kwargs.get("branch") == github_task["branch"]
        
        # タスクが完了としてマークされたことを確認
        # mock_task_manager_instance.complete_task.assert_called_once()
        # task_args, task_kwargs = mock_task_manager_instance.complete_task.call_args
        # assert task_args[0] == github_task["id"]
        # assert "commit_url" in task_args[1]
        # assert "path" in task_args[1]
        # assert "branch" in task_args[1]
        pass
    
    @patch("app.clients.github.GitHubClient")
    def test_github_branch_pr_integration(self, mock_github_client, setup_integration):
        """GitHub ブランチとPR作成の統合テスト"""
        # モックのセットアップ
        mock_github_instance = mock_github_client.return_value
        
        # ブランチ作成のモック
        mock_github_instance.create_branch.return_value = {
            "name": "feature/test-branch",
            "base": "main",
            "created": True
        }
        
        # ファイルプッシュのモック
        mock_github_instance.push_file.return_value = {
            "commit_url": "https://github.com/test_owner/test_repo/commit/abc123def456",
            "path": "docs/test.md",
            "branch": "feature/test-branch",
            "message": "テスト用コミット"
        }
        
        # PR作成のモック
        mock_github_instance.create_pr.return_value = {
            "pr_url": "https://github.com/test_owner/test_repo/pull/123",
            "title": "テスト用PR",
            "description": "これはテスト用のPRです。",
            "branch": "feature/test-branch",
            "base": "main"
        }
        
        # 統合テスト（実際はアプリケーションコードで行われるが、ここではモック）
        # このテストは、実際のクラスが実装された後に有効化する
        # github_client = GitHubClient(token="dummy_token", repo_owner="test_owner", repo_name="test_repo")
        # 
        # # 新しいブランチを作成
        # branch_name = "feature/test-branch"
        # branch_result = github_client.create_branch(branch_name)
        # 
        # # ブランチが作成されたことを確認
        # assert branch_result["created"] is True
        # assert branch_result["name"] == branch_name
        # 
        # # ブランチにファイルをプッシュ
        # file_content = "# テスト用マークダウン\n\nこれはテスト用のファイルです。"
        # push_result = github_client.push_file(
        #     "docs/test.md", 
        #     file_content, 
        #     "テスト用コミット", 
        #     branch=branch_name
        # )
        # 
        # # ファイルがプッシュされたことを確認
        # assert push_result["branch"] == branch_name
        # assert "commit_url" in push_result
        # 
        # # ブランチからPRを作成
        # pr_title = "テスト用PR"
        # pr_description = "これはテスト用のPRです。"
        # pr_result = github_client.create_pr(pr_title, pr_description, branch_name)
        # 
        # # PRが作成されたことを確認
        # assert "pr_url" in pr_result
        # assert pr_result["title"] == pr_title
        # assert pr_result["branch"] == branch_name
        
        # 各メソッドが呼び出されたことを確認
        # mock_github_instance.create_branch.assert_called_once_with("feature/test-branch")
        # mock_github_instance.push_file.assert_called_once()
        # mock_github_instance.create_pr.assert_called_once()
        pass
    
    @patch("app.clients.s3.S3Client")
    @patch("app.processors.image.ImageProcessor")
    def test_image_s3_integration(self, mock_image_processor, mock_s3_client, setup_integration):
        """画像処理とS3の統合テスト"""
        # セットアップ情報を取得
        base_dir = setup_integration["base_dir"]
        
        # モックのセットアップ
        mock_processor_instance = mock_image_processor.return_value
        mock_s3_instance = mock_s3_client.return_value
        
        # SVG処理のモック
        svg_content = '<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40" stroke="black" stroke-width="3" fill="red" /></svg>'
        mock_processor_instance.extract_svg_blocks.return_value = [svg_content]
        
        # 画像変換のモック
        dummy_png_data = b"dummy_png_data"
        mock_processor_instance.convert_svg_to_png.return_value = dummy_png_data
        
        # S3アップロードのモック
        mock_s3_instance.upload_file.return_value = "images/image_1.png"
        mock_s3_instance.get_public_url.return_value = "https://dummy-bucket.s3.amazonaws.com/images/image_1.png"
        
        # テスト用のMarkdownファイルを作成
        markdown_file = base_dir / "article_with_svg.md"
        with open(markdown_file, "w") as f:
            f.write(f"""# テスト記事

これはSVGを含むテスト記事です。

```svg
{svg_content}
```
""")
        
        # 統合テスト（実際はアプリケーションコードで行われるが、ここではモック）
        # このテストは、実際のクラスが実装された後に有効化する
        # image_processor = ImageProcessor()
        # s3_client = S3Client(bucket_name="dummy-bucket")
        # 
        # # 記事からSVGを抽出
        # svg_blocks = image_processor.extract_svg_blocks(str(markdown_file))
        # 
        # # 各SVGをPNGに変換してアップロード
        # for i, svg in enumerate(svg_blocks):
        #     # SVGをPNGに変換
        #     png_data = image_processor.convert_svg_to_png(svg)
        #     
        #     # 画像ファイルを保存
        #     images_dir = base_dir / "images"
        #     images_dir.mkdir(exist_ok=True)
        #     image_path = images_dir / f"image_{i+1}.png"
        #     with open(image_path, "wb") as f:
        #         f.write(png_data)
        #     
        #     # S3にアップロード
        #     s3_key = s3_client.upload_file(png_data, f"images/image_{i+1}.png", "image/png")
        #     image_url = s3_client.get_public_url(s3_key)
        #     
        #     # Markdownの画像参照を置換
        #     with open(markdown_file, "r") as f:
        #         content = f.read()
        #     
        #     updated_content = content.replace(f"```svg\n{svg}\n```", f"![image_{i+1}]({image_url})")
        #     
        #     with open(markdown_file, "w") as f:
        #         f.write(updated_content)
        
        # メソッドが呼び出されたことを確認
        # mock_processor_instance.extract_svg_blocks.assert_called_once_with(str(markdown_file))
        # mock_processor_instance.convert_svg_to_png.assert_called_once_with(svg_content)
        # mock_s3_instance.upload_file.assert_called_once()
        # mock_s3_instance.get_public_url.assert_called_once_with("images/image_1.png")
        pass 