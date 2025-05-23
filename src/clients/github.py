"""GitHub APIクライアント実装"""

import base64
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from urllib.parse import urljoin

from .base import BaseClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class GitHubError(Exception):
    """GitHub API操作エラー"""
    pass


class RepositoryNotFoundError(GitHubError):
    """リポジトリが見つからないエラー"""
    pass


class FileNotFoundError(GitHubError):
    """ファイルが見つからないエラー"""
    pass


class GitHubClient(BaseClient):
    """GitHub APIクライアント"""
    
    def __init__(
        self,
        token: str,
        owner: str,
        repo: str,
        base_url: str = "https://api.github.com",
        **kwargs
    ):
        super().__init__(base_url=base_url, **kwargs)
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ResourceGenerateWorkflow/1.0"
        })
        
    async def get_repository(self) -> Dict[str, Any]:
        """リポジトリ情報を取得"""
        try:
            response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}"
            )
            
            logger.info(f"リポジトリ情報を取得しました: {self.owner}/{self.repo}")
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise RepositoryNotFoundError(f"リポジトリが見つかりません: {self.owner}/{self.repo}")
            raise GitHubError(f"リポジトリ情報の取得に失敗しました: {e}")
            
    async def get_file_content(
        self,
        path: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """ファイル内容を取得
        
        Args:
            path: ファイルパス
            ref: ブランチ名またはコミットSHA
            
        Returns:
            ファイル情報（content, sha, encoding等）
        """
        try:
            response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/contents/{path}",
                params={"ref": ref}
            )
            
            # Base64デコード
            if response.get("encoding") == "base64":
                content = base64.b64decode(response["content"]).decode("utf-8")
                response["decoded_content"] = content
                
            logger.info(f"ファイル内容を取得しました: {path}")
            self.stats['file_reads'] = self.stats.get('file_reads', 0) + 1
            
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"ファイルが見つかりません: {path}")
            raise GitHubError(f"ファイル内容の取得に失敗しました: {e}")
            
    async def create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None
    ) -> Dict[str, Any]:
        """ファイルを作成または更新
        
        Args:
            path: ファイルパス
            content: ファイル内容
            message: コミットメッセージ
            branch: ブランチ名
            sha: 更新時の既存ファイルのSHA（更新時必須）
            
        Returns:
            作成/更新されたファイル情報
        """
        # Base64エンコード
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        
        data = {
            "message": message,
            "content": encoded_content,
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
            
        try:
            response = await self._request(
                "PUT",
                f"/repos/{self.owner}/{self.repo}/contents/{path}",
                json=data
            )
            
            action = "更新" if sha else "作成"
            logger.info(f"ファイルを{action}しました: {path}")
            self.stats['file_writes'] = self.stats.get('file_writes', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"ファイルの作成/更新に失敗しました: {e}")
            
    async def delete_file(
        self,
        path: str,
        message: str,
        sha: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """ファイルを削除
        
        Args:
            path: ファイルパス
            message: コミットメッセージ
            sha: 削除するファイルのSHA
            branch: ブランチ名
            
        Returns:
            削除結果
        """
        data = {
            "message": message,
            "sha": sha,
            "branch": branch
        }
        
        try:
            response = await self._request(
                "DELETE",
                f"/repos/{self.owner}/{self.repo}/contents/{path}",
                json=data
            )
            
            logger.info(f"ファイルを削除しました: {path}")
            self.stats['file_deletions'] = self.stats.get('file_deletions', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"ファイルの削除に失敗しました: {e}")
            
    async def list_directory_contents(
        self,
        path: str = "",
        ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """ディレクトリ内容を一覧取得
        
        Args:
            path: ディレクトリパス（空文字でルート）
            ref: ブランチ名またはコミットSHA
            
        Returns:
            ファイル/ディレクトリ一覧
        """
        try:
            response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/contents/{path}",
                params={"ref": ref}
            )
            
            # レスポンスがリストでない場合（単一ファイル）はリストに変換
            if not isinstance(response, list):
                response = [response]
                
            logger.info(f"ディレクトリ内容を取得しました: {path} ({len(response)}件)")
            
            return response
            
        except Exception as e:
            if "404" in str(e):
                raise FileNotFoundError(f"ディレクトリが見つかりません: {path}")
            raise GitHubError(f"ディレクトリ内容の取得に失敗しました: {e}")
            
    async def create_branch(
        self,
        branch_name: str,
        from_branch: str = "main"
    ) -> Dict[str, Any]:
        """新しいブランチを作成
        
        Args:
            branch_name: 新しいブランチ名
            from_branch: 元となるブランチ名
            
        Returns:
            作成されたブランチ情報
        """
        try:
            # 元ブランチの最新コミットSHAを取得
            ref_response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/git/refs/heads/{from_branch}"
            )
            
            sha = ref_response["object"]["sha"]
            
            # 新しいブランチを作成
            data = {
                "ref": f"refs/heads/{branch_name}",
                "sha": sha
            }
            
            response = await self._request(
                "POST",
                f"/repos/{self.owner}/{self.repo}/git/refs",
                json=data
            )
            
            logger.info(f"ブランチを作成しました: {branch_name}")
            self.stats['branches_created'] = self.stats.get('branches_created', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"ブランチの作成に失敗しました: {e}")
            
    async def create_pull_request(
        self,
        title: str,
        head: str,
        base: str = "main",
        body: Optional[str] = None,
        draft: bool = False
    ) -> Dict[str, Any]:
        """プルリクエストを作成
        
        Args:
            title: プルリクエストのタイトル
            head: マージ元ブランチ
            base: マージ先ブランチ
            body: プルリクエストの説明
            draft: ドラフトプルリクエストかどうか
            
        Returns:
            作成されたプルリクエスト情報
        """
        data = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft
        }
        
        if body:
            data["body"] = body
            
        try:
            response = await self._request(
                "POST",
                f"/repos/{self.owner}/{self.repo}/pulls",
                json=data
            )
            
            logger.info(f"プルリクエストを作成しました: {title}")
            self.stats['pull_requests_created'] = self.stats.get('pull_requests_created', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"プルリクエストの作成に失敗しました: {e}")
            
    async def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """イシューを作成
        
        Args:
            title: イシューのタイトル
            body: イシューの説明
            labels: ラベル一覧
            assignees: アサイニー一覧
            
        Returns:
            作成されたイシュー情報
        """
        data = {
            "title": title
        }
        
        if body:
            data["body"] = body
        if labels:
            data["labels"] = labels
        if assignees:
            data["assignees"] = assignees
            
        try:
            response = await self._request(
                "POST",
                f"/repos/{self.owner}/{self.repo}/issues",
                json=data
            )
            
            logger.info(f"イシューを作成しました: {title}")
            self.stats['issues_created'] = self.stats.get('issues_created', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"イシューの作成に失敗しました: {e}")
            
    async def get_commits(
        self,
        sha: Optional[str] = None,
        path: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """コミット一覧を取得
        
        Args:
            sha: 特定のSHAから開始
            path: 特定のパスのコミットのみ
            since: この日時以降のコミット
            until: この日時以前のコミット
            per_page: ページあたりの件数
            
        Returns:
            コミット一覧
        """
        params = {"per_page": per_page}
        
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        if since:
            params["since"] = since.isoformat()
        if until:
            params["until"] = until.isoformat()
            
        try:
            response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/commits",
                params=params
            )
            
            logger.info(f"コミット一覧を取得しました: {len(response)}件")
            
            return response
            
        except Exception as e:
            raise GitHubError(f"コミット一覧の取得に失敗しました: {e}")
            
    async def get_releases(
        self,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """リリース一覧を取得"""
        try:
            response = await self._request(
                "GET",
                f"/repos/{self.owner}/{self.repo}/releases",
                params={"per_page": per_page}
            )
            
            logger.info(f"リリース一覧を取得しました: {len(response)}件")
            
            return response
            
        except Exception as e:
            raise GitHubError(f"リリース一覧の取得に失敗しました: {e}")
            
    async def create_release(
        self,
        tag_name: str,
        name: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
        prerelease: bool = False,
        target_commitish: str = "main"
    ) -> Dict[str, Any]:
        """リリースを作成
        
        Args:
            tag_name: タグ名
            name: リリース名
            body: リリースノート
            draft: ドラフトリリースかどうか
            prerelease: プレリリースかどうか
            target_commitish: リリース対象のブランチまたはコミット
            
        Returns:
            作成されたリリース情報
        """
        data = {
            "tag_name": tag_name,
            "target_commitish": target_commitish,
            "draft": draft,
            "prerelease": prerelease
        }
        
        if name:
            data["name"] = name
        if body:
            data["body"] = body
            
        try:
            response = await self._request(
                "POST",
                f"/repos/{self.owner}/{self.repo}/releases",
                json=data
            )
            
            logger.info(f"リリースを作成しました: {tag_name}")
            self.stats['releases_created'] = self.stats.get('releases_created', 0) + 1
            
            return response
            
        except Exception as e:
            raise GitHubError(f"リリースの作成に失敗しました: {e}")
            
    async def search_code(
        self,
        query: str,
        sort: str = "indexed",
        order: str = "desc",
        per_page: int = 30
    ) -> Dict[str, Any]:
        """コード検索
        
        Args:
            query: 検索クエリ
            sort: ソート方法（indexed, created, updated）
            order: ソート順（asc, desc）
            per_page: ページあたりの件数
            
        Returns:
            検索結果
        """
        # リポジトリ指定を追加
        full_query = f"{query} repo:{self.owner}/{self.repo}"
        
        params = {
            "q": full_query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }
        
        try:
            response = await self._request(
                "GET",
                "/search/code",
                params=params
            )
            
            logger.info(f"コード検索を実行しました: {query} ({response['total_count']}件)")
            
            return response
            
        except Exception as e:
            raise GitHubError(f"コード検索に失敗しました: {e}")
            
    async def health_check(self) -> bool:
        """GitHub API接続のヘルスチェック"""
        try:
            await self.get_repository()
            return True
        except Exception as e:
            logger.error(f"GitHubヘルスチェックに失敗しました: {e}")
            return False 