import pytest
from unittest.mock import patch, MagicMock

from services.notifier import NotifierService
from tests.fixtures.sample_api_responses import SAMPLE_SLACK_RESPONSE


class TestNotifierService:
    """Slack通知サービスのテスト"""

    @pytest.fixture
    def mock_config(self):
        """テスト用の設定"""
        return {
            "slack": {
                "token": "test_slack_token",
                "channel": "test-channel",
                "username": "test-bot",
                "icon_emoji": ":robot_face:"
            }
        }

    @pytest.fixture
    def notifier_service(self, mock_config):
        """通知サービスのインスタンス"""
        with patch('slack_sdk.WebClient') as mock_slack_client:
            service = NotifierService(mock_config)
            # Slackクライアントを直接設定
            service._slack_client = MagicMock()
            service._slack_client.chat_postMessage.return_value = SAMPLE_SLACK_RESPONSE
            return service

    def test_init(self, mock_config):
        """初期化のテスト"""
        with patch('slack_sdk.WebClient') as mock_slack_client:
            service = NotifierService(mock_config)
            
            # WebClientが正しい引数で呼ばれたことを確認
            mock_slack_client.assert_called_once_with(token="test_slack_token")
            
            # 設定値が正しく保存されていることを確認
            assert service._channel == "test-channel"
            assert service._username == "test-bot"
            assert service._icon_emoji == ":robot_face:"

    def test_send_message(self, notifier_service):
        """基本メッセージ送信のテスト"""
        # メッセージ送信
        result = notifier_service.send_message("テストメッセージ")
        
        # Slackクライアントの呼び出しを確認
        notifier_service._slack_client.chat_postMessage.assert_called_once_with(
            channel="test-channel",
            text="テストメッセージ",
            username="test-bot",
            icon_emoji=":robot_face:"
        )
        
        # 結果の検証
        assert result["ok"] is True
        assert result["channel"] == "C1234567890"

    def test_send_success(self, notifier_service):
        """成功通知のテスト"""
        # 成功通知送信
        result = notifier_service.send_success("テスト処理が完了しました")
        
        # Slackクライアントの呼び出しを確認
        notifier_service._slack_client.chat_postMessage.assert_called_once()
        
        # 呼び出し引数の検証
        call_args = notifier_service._slack_client.chat_postMessage.call_args[1]
        assert call_args["channel"] == "test-channel"
        assert "テスト処理が完了しました" in call_args["text"]
        assert ":white_check_mark:" in call_args["text"]
        
        # 結果の検証
        assert result["ok"] is True

    def test_send_error(self, notifier_service):
        """エラー通知のテスト"""
        # エラー通知送信
        result = notifier_service.send_error("テストエラーが発生しました")
        
        # Slackクライアントの呼び出しを確認
        notifier_service._slack_client.chat_postMessage.assert_called_once()
        
        # 呼び出し引数の検証
        call_args = notifier_service._slack_client.chat_postMessage.call_args[1]
        assert call_args["channel"] == "test-channel"
        assert "テストエラーが発生しました" in call_args["text"]
        assert ":x:" in call_args["text"]
        
        # 結果の検証
        assert result["ok"] is True

    def test_send_progress(self, notifier_service):
        """進捗通知のテスト"""
        # 進捗通知送信
        result = notifier_service.send_progress("テスト処理中...", 50)
        
        # Slackクライアントの呼び出しを確認
        notifier_service._slack_client.chat_postMessage.assert_called_once()
        
        # 呼び出し引数の検証
        call_args = notifier_service._slack_client.chat_postMessage.call_args[1]
        assert call_args["channel"] == "test-channel"
        assert "テスト処理中..." in call_args["text"]
        assert "50%" in call_args["text"]
        
        # 結果の検証
        assert result["ok"] is True

    def test_send_checkpoint_notification(self, notifier_service):
        """チェックポイント通知のテスト"""
        # チェックポイント通知送信
        result = notifier_service.send_checkpoint_notification("checkpoint_123")
        
        # Slackクライアントの呼び出しを確認
        notifier_service._slack_client.chat_postMessage.assert_called_once()
        
        # 呼び出し引数の検証
        call_args = notifier_service._slack_client.chat_postMessage.call_args[1]
        assert call_args["channel"] == "test-channel"
        assert "チェックポイント" in call_args["text"]
        assert "checkpoint_123" in call_args["text"]
        
        # 結果の検証
        assert result["ok"] is True

    def test_handle_slack_error(self, notifier_service):
        """Slackエラー処理のテスト"""
        # エラーを発生させるようにモック
        notifier_service._slack_client.chat_postMessage.side_effect = Exception("Slack API error")
        
        # エラーがキャッチされることを確認
        result = notifier_service.send_message("テストメッセージ")
        
        # 結果がNoneであることを確認
        assert result is None 