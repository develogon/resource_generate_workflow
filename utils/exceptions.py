class AppException(Exception):
    """アプリケーション全体で使用される基本例外クラス"""
    
    def __init__(self, message, error_code=None, inner_exception=None):
        """
        Parameters
        ----------
        message : str
            エラーメッセージ
        error_code : str, optional
            エラーコード
        inner_exception : Exception, optional
            内部例外
        """
        self.message = message
        self.error_code = error_code
        self.inner_exception = inner_exception
        
        # エラーコードがある場合はメッセージに追加
        if error_code:
            formatted_message = f"{error_code}: {message}"
        else:
            formatted_message = message
        
        # 内部例外がある場合はメッセージに追加
        if inner_exception:
            formatted_message += f" (原因: {str(inner_exception)})"
        
        super().__init__(formatted_message)


class APIException(AppException):
    """外部APIとの通信時に発生する例外"""
    
    def __init__(self, message, service_name, status_code=None, error_code=None, inner_exception=None):
        """
        Parameters
        ----------
        message : str
            エラーメッセージ
        service_name : str
            API サービス名
        status_code : int, optional
            HTTP ステータスコード
        error_code : str, optional
            エラーコード
        inner_exception : Exception, optional
            内部例外
        """
        self.service_name = service_name
        self.status_code = status_code
        
        # ステータスコードがある場合はメッセージに追加
        detailed_message = f"{service_name} APIエラー: {message}"
        if status_code:
            detailed_message += f" (ステータスコード: {status_code})"
        
        super().__init__(detailed_message, error_code, inner_exception)


class ProcessingException(AppException):
    """コンテンツ処理中に発生する例外"""
    
    def __init__(self, message, step=None, recovery_hint=None, error_code=None, inner_exception=None):
        """
        Parameters
        ----------
        message : str
            エラーメッセージ
        step : str, optional
            処理ステップ名
        recovery_hint : str, optional
            回復のためのヒント
        error_code : str, optional
            エラーコード
        inner_exception : Exception, optional
            内部例外
        """
        self.step = step
        self.recovery_hint = recovery_hint
        
        # 処理ステップとリカバリーヒントがある場合はメッセージに追加
        detailed_message = message
        if step:
            detailed_message = f"[{step}] {detailed_message}"
        if recovery_hint:
            detailed_message += f" (リカバリー: {recovery_hint})"
        
        super().__init__(detailed_message, error_code, inner_exception) 