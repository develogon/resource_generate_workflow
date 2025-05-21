"""
APIクライアント基底クラスモジュール。
外部APIと通信するための共通ロジックを提供する。
Adapter パターンを使用して、外部APIインターフェースを統一する。
"""
import functools
import time
import requests
from typing import Dict, Any, Optional, Callable, Union

from utils.exceptions import APIException


class APIClient:
    """
    外部APIとの通信を管理する基底クラス。
    Adapter パターンで外部インターフェースを統一。
    
    派生クラスでは最低限以下のプロパティを設定する必要がある:
    - base_url: API基底URL
    - headers: 認証ヘッダーなど
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        APIClientを初期化する。
        
        Args:
            config (Dict[str, Any]): 設定情報（APIキーなど）
        """
        self.config = config
        self.base_url = ""  # 派生クラスでオーバーライド
        self.headers = {}   # 派生クラスでオーバーライド
        self.timeout = 30   # デフォルトタイムアウト値（秒）
    
    def request(
        self, 
        endpoint: str, 
        method: str = "GET", 
        payload: Optional[Dict[str, Any]] = None, 
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        API通信を実行する。
        
        Args:
            endpoint (str): APIエンドポイント (例: "/messages")
            method (str, optional): HTTPメソッド. デフォルトは "GET"
            payload (Dict[str, Any], optional): リクエストボディ. デフォルトは None
            timeout (int, optional): タイムアウト秒数. デフォルトは None (self.timeoutを使用)
        
        Returns:
            Dict[str, Any]: レスポンスデータ
            
        Raises:
            APIException: API呼び出しに失敗した場合
        """
        url = f"{self.base_url}{endpoint}"
        timeout_value = timeout if timeout is not None else self.timeout
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=payload,
                timeout=timeout_value
            )
            
            return self.handle_response(response)
            
        except Exception as e:
            return self.handle_error(e)
    
    def handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        API応答を処理する。
        
        Args:
            response (requests.Response): API応答
        
        Returns:
            Dict[str, Any]: 処理されたレスポンスデータ
            
        Raises:
            APIException: エラーレスポンスの場合
        """
        if 200 <= response.status_code < 300:
            return response.json()
        else:
            try:
                error_data = response.json()
                error_message = error_data.get("error", {}).get("message", f"API error: {response.status_code}")
                error_code = error_data.get("error", {}).get("code", "unknown_error")
                
                raise APIException(
                    f"API error: {error_message}",
                    service_name=self.__class__.__name__,
                    status_code=response.status_code,
                    error_code=error_code,
                )
            except ValueError:
                # JSONでないレスポンス
                raise APIException(
                    f"API returned non-JSON error response: {response.status_code}",
                    service_name=self.__class__.__name__,
                    status_code=response.status_code
                )
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        API通信中のエラーを処理する。
        
        Args:
            error (Exception): 発生した例外
        
        Raises:
            APIException: 処理されたAPI例外
        """
        if isinstance(error, APIException):
            raise error
        
        raise APIException(
            f"API通信エラー: {str(error)}",
            service_name=self.__class__.__name__,
            inner_exception=error
        )
    
    def retry_request(self, max_attempts: int = 3) -> Callable:
        """
        API呼び出しのリトライを行うデコレータ。
        
        Args:
            max_attempts (int, optional): 最大試行回数. デフォルトは 3
        
        Returns:
            Callable: デコレータ関数
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        
                        # 最大試行回数に達した場合は例外を発生
                        if attempt == max_attempts:
                            raise e
                        
                        # 試行間隔を計算 (指数バックオフ)
                        sleep_time = 2 ** (attempt - 1)
                        time.sleep(sleep_time)
                
                # 通常ここには到達しないが、念のため
                raise last_exception or Exception("リトライ処理中に不明なエラーが発生しました")
            
            return wrapper
        
        return decorator 