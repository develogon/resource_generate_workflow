"""
S3ストレージ操作を担当するサービスモジュール。
boto3を使用してAWS S3への画像ファイルのアップロード、URL取得などを行う。
"""
import os
import boto3
from typing import Dict, Any, List, Optional, Union

from utils.exceptions import APIException
from services.client import APIClient


class StorageService(APIClient):
    """
    S3ストレージ操作を担当するサービスクラス。
    APIClientを継承し、S3固有の機能を実装する。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        StorageServiceを初期化する。
        
        Args:
            config (Dict[str, Any]): 設定情報
                - storage.aws_access_key_id: AWS Access Key ID
                - storage.aws_secret_access_key: AWS Secret Access Key
                - storage.region: AWS Region
                - storage.bucket_name: S3バケット名
                - storage.base_url: S3基底URL
        """
        super().__init__(config)
        
        # 設定から必要なパラメータを取得
        storage_config = config.get("storage", {})
        self._aws_access_key_id = storage_config.get("aws_access_key_id")
        self._aws_secret_access_key = storage_config.get("aws_secret_access_key")
        self._region = storage_config.get("region")
        self._bucket_name = storage_config.get("bucket_name")
        self._base_url = storage_config.get("base_url")
        
        # S3クライアント初期化
        self._s3_client = boto3.client(
            's3',
            aws_access_key_id=self._aws_access_key_id,
            aws_secret_access_key=self._aws_secret_access_key,
            region_name=self._region
        )
    
    def upload_file(self, file_path: str, remote_path: str) -> str:
        """
        ファイルをS3にアップロードする。
        
        Args:
            file_path (str): アップロードするファイルのローカルパス
            remote_path (str): S3上での保存パス (例: "images/example.png")
        
        Returns:
            str: アップロードされたファイルのURL
            
        Raises:
            APIException: アップロードに失敗した場合
        """
        try:
            # S3にファイルをアップロード
            self._s3_client.upload_file(
                file_path,
                self._bucket_name,
                remote_path
            )
            
            # アップロードされたファイルのURLを生成
            url = f"{self._base_url}/{remote_path}"
            
            return url
        
        except Exception as e:
            raise APIException(
                f"S3 ファイルアップロードエラー: {str(e)}",
                service_name="StorageService",
                inner_exception=e
            )
    
    def get_url(self, remote_path: str, expire: Optional[int] = None) -> str:
        """
        S3上のファイルのURLを取得する。
        
        Args:
            remote_path (str): S3上のファイルパス
            expire (int, optional): URLの有効期限（秒）. デフォルトはNone（永続的なURL）
        
        Returns:
            str: ファイルのURL
        """
        # 有効期限付きURLが要求された場合
        if expire is not None:
            try:
                url = self._s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self._bucket_name,
                        'Key': remote_path
                    },
                    ExpiresIn=expire
                )
                return url
            
            except Exception as e:
                raise APIException(
                    f"S3 署名付きURL生成エラー: {str(e)}",
                    service_name="StorageService",
                    inner_exception=e
                )
        
        # 通常の永続的なURL
        return f"{self._base_url}/{remote_path}"
    
    def delete_file(self, remote_path: str) -> bool:
        """
        S3上のファイルを削除する。
        
        Args:
            remote_path (str): S3上のファイルパス
        
        Returns:
            bool: 削除に成功した場合はTrue
            
        Raises:
            APIException: 削除に失敗した場合
        """
        try:
            # S3上のファイルを削除
            self._s3_client.delete_object(
                Bucket=self._bucket_name,
                Key=remote_path
            )
            
            return True
        
        except Exception as e:
            raise APIException(
                f"S3 ファイル削除エラー: {str(e)}",
                service_name="StorageService",
                inner_exception=e
            )
    
    def check_upload_status(self, remote_path: str) -> bool:
        """
        S3上のファイルの存在を確認する。
        
        Args:
            remote_path (str): S3上のファイルパス
        
        Returns:
            bool: ファイルが存在する場合はTrue、そうでない場合はFalse
        """
        try:
            # ファイルのメタデータを取得
            self._s3_client.head_object(
                Bucket=self._bucket_name,
                Key=remote_path
            )
            
            return True
        
        except Exception:
            # ファイルが存在しない場合
            return False
    
    def upload_multiple_files(self, file_paths: List[str], remote_dir: str) -> List[str]:
        """
        複数のファイルをS3にアップロードする。
        
        Args:
            file_paths (List[str]): アップロードするファイルのローカルパスのリスト
            remote_dir (str): S3上での保存ディレクトリ (例: "images/")
        
        Returns:
            List[str]: アップロードされたファイルのURLのリスト
            
        Raises:
            APIException: アップロードに失敗した場合
        """
        uploaded_urls = []
        
        try:
            for file_path in file_paths:
                # ファイル名を取得
                filename = os.path.basename(file_path)
                
                # S3上のパスを生成
                remote_path = f"{remote_dir}{filename}"
                
                # ファイルをアップロード
                url = self.upload_file(file_path, remote_path)
                
                # アップロードされたURLをリストに追加
                uploaded_urls.append(url)
            
            return uploaded_urls
        
        except Exception as e:
            raise APIException(
                f"S3 複数ファイルアップロードエラー: {str(e)}",
                service_name="StorageService",
                inner_exception=e
            ) 