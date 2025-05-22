from unittest.mock import MagicMock

class SlackMock:
    """Slack APIのモッククラス"""
    
    def __init__(self, error=False):
        self.mock = MagicMock()
        self.sent_messages = []
        
        if error:
            self.mock.send_notification.side_effect = Exception("Slack通知エラー")
            self.mock.send_error_alert.side_effect = Exception("Slackエラー通知エラー")
        else:
            def store_message(message, attachments=None):
                self.sent_messages.append({
                    "message": message,
                    "attachments": attachments
                })
                return {"ok": True, "ts": "1234567890.123456"}
            
            self.mock.send_notification.side_effect = store_message
            self.mock.send_error_alert.side_effect = lambda error, context: store_message(
                f"エラー: {error}", [{"title": "コンテキスト", "text": str(context)}]
            )
    
    def get_mock(self):
        return self.mock
        
    def get_sent_messages(self):
        return self.sent_messages 