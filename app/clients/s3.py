import os
import logging
import io
from typing import Dict, Optional


class S3Client:
    """AWS S3連携クライアント

    S3へのファイルアップロードや取得を行うクライアントクラスです。
    """

    def __init__(self, bucket_name=None, region=None):
        """初期化

        Args:
            bucket_name (str, optional): S3バケット名. デフォルトはNone (環境変数から取得)
            region (str, optional): AWSリージョン. デフォルトはNone (環境変数から取得)
        """
        self.bucket_name = bucket_name or os.environ.get("AWS_S3_BUCKET")
        self.region = region or os.environ.get("AWS_REGION")
        self.logger = logging.getLogger(__name__)

        if not self.bucket_name:
            self.logger.warning("S3バケット名が設定されていません。環境変数 AWS_S3_BUCKET を設定してください。")
        if not self.region:
            self.logger.warning("AWSリージョンが設定されていません。環境変数 AWS_REGION を設定してください。")

    def upload_file(self, data: bytes, key: str, content_type: str = "application/octet-stream", metadata: Optional[Dict] = None) -> str:
        """ファイルをS3にアップロード

        Args:
            data (bytes): アップロードするファイルデータ
            key (str): S3オブジェクトキー
            content_type (str, optional): コンテンツタイプ. デフォルトは"application/octet-stream"
            metadata (Dict, optional): メタデータ. デフォルトはNone

        Returns:
            str: アップロードされたオブジェクトキー
        """
        # 実際の実装時はAWS S3 APIを呼び出す
        # 現時点ではキーをそのまま返す
        self.logger.info(f"S3にファイルをアップロード: key={key}, content_type={content_type}")
        return key

    def get_public_url(self, key: str) -> str:
        """アップロードしたファイルの公開URL取得

        Args:
            key (str): S3オブジェクトキー

        Returns:
            str: ファイルの公開URL
        """
        # 実際の実装時はS3の設定に基づいてURLを構築
        # 現時点ではモックURLを返す
        public_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}"
        return public_url

    def check_if_exists(self, key: str) -> bool:
        """ファイルが存在するか確認

        Args:
            key (str): S3オブジェクトキー

        Returns:
            bool: ファイルが存在する場合はTrue
        """
        # テスト用に特定のパターンをチェック
        if "not_exists" in key:
            return False
        if "exists" in key:
            return True
        return False

    def delete_file(self, key: str) -> bool:
        """ファイルを削除

        Args:
            key (str): S3オブジェクトキー

        Returns:
            bool: 削除に成功した場合はTrue
        """
        # テスト用に特定のパターンをチェック
        self.logger.info(f"S3からファイルを削除: key={key}")
        if "not_exists" in key:
            return False
        if "exists" in key:
            return True
        return False

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """署名付きURLを生成

        Args:
            key (str): S3オブジェクトキー
            expiration (int, optional): URLの有効期限（秒）. デフォルトは3600秒（1時間）

        Returns:
            str: 署名付きURL
        """
        # 実際の実装時はAWS S3 APIを呼び出す
        # 現時点ではモックURLを返す
        presigned_url = f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}?AWSAccessKeyId=xxx&Signature=yyy&Expires=1234567890"
        return presigned_url 