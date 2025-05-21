import pytest
from unittest.mock import patch, MagicMock

from core.processor import ContentProcessor


class TestContentProcessor:
    """コンテンツプロセッサのテストクラス"""

    @pytest.fixture
    def mock_services(self):
        """モックサービス群"""
        mock_claude_service = MagicMock()
        mock_github_service = MagicMock()
        mock_storage_service = MagicMock()
        mock_notifier_service = MagicMock()
        mock_file_manager = MagicMock()
        mock_state_manager = MagicMock()
        
        return {
            "claude_service": mock_claude_service,
            "github_service": mock_github_service,
            "storage_service": mock_storage_service,
            "notifier_service": mock_notifier_service,
            "file_manager": mock_file_manager,
            "state_manager": mock_state_manager
        }

    @pytest.fixture
    def content_processor(self, mock_services):
        """コンテンツプロセッサのインスタンス"""
        content = "# テスト原稿\n\n## 第1章\n\n内容"
        args = MagicMock(title="テストタイトル", lang="go")
        
        processor = ContentProcessor(
            content=content,
            args=args,
            file_manager=mock_services["file_manager"],
            claude_service=mock_services["claude_service"],
            github_service=mock_services["github_service"],
            storage_service=mock_services["storage_service"],
            state_manager=mock_services["state_manager"],
            notifier=mock_services["notifier_service"]
        )
        return processor

    def test_process(self, content_processor, mock_services):
        """処理実行のテスト"""
        # モックメソッドの戻り値設定
        mock_services["claude_service"].generate_content.return_value = {
            "content": "# テスト応答\n\nテスト内容"
        }
        
        # 実際のメソッドをモック
        with patch.object(content_processor, 'pre_process') as mock_pre_process:
            with patch.object(content_processor, 'execute') as mock_execute:
                with patch.object(content_processor, 'post_process') as mock_post_process:
                    # process実行
                    content_processor.process()
                    
                    # 各メソッドが呼ばれたことを確認
                    mock_pre_process.assert_called_once()
                    mock_execute.assert_called_once()
                    mock_post_process.assert_called_once()

    def test_pre_process(self, content_processor, mock_services):
        """前処理のテスト"""
        # ディレクトリ構造作成の戻り値設定
        mock_services["file_manager"].create_directory_structure.return_value = [
            "/path/to/dir1",
            "/path/to/dir2"
        ]
        
        # 前処理実行
        content_processor.pre_process()
        
        # ディレクトリ構造が作成されたことを確認
        mock_services["file_manager"].create_directory_structure.assert_called_once()
        
        # 状態が保存されたことを確認
        mock_services["state_manager"].save_state.assert_called_once()

    def test_execute(self, content_processor, mock_services):
        """主処理のテスト"""
        # 章・セクションの抽出結果設定
        mock_services["file_manager"].read_content.return_value = "# テスト原稿\n\n## 第1章\n\n内容"
        
        # executablesを設定
        content_processor.executables = [
            {"function": MagicMock(), "args": {}, "name": "テスト処理1"},
            {"function": MagicMock(), "args": {}, "name": "テスト処理2"}
        ]
        
        # 実行
        content_processor.execute()
        
        # 各実行可能アイテムの関数が呼ばれたことを確認
        content_processor.executables[0]["function"].assert_called_once()
        content_processor.executables[1]["function"].assert_called_once()
        
        # 進捗が更新されたことを確認
        assert content_processor.progress_percentage == 100.0
        
        # 通知が送信されたことを確認
        mock_services["notifier_service"].send_progress.assert_called()

    def test_post_process(self, content_processor, mock_services):
        """後処理のテスト"""
        # 後処理実行
        content_processor.post_process()
        
        # 完了通知が送信されたことを確認
        mock_services["notifier_service"].send_success.assert_called_once()

    def test_handle_error(self, content_processor, mock_services):
        """エラー処理のテスト"""
        # テスト用のエラー
        test_error = ValueError("テストエラー")
        
        # エラー処理実行
        content_processor.handle_error(test_error)
        
        # チェックポイントが保存されたことを確認
        mock_services["state_manager"].save_state.assert_called_once()
        
        # エラー通知が送信されたことを確認
        mock_services["notifier_service"].send_error.assert_called_once()

    def test_save_checkpoint(self, content_processor, mock_services):
        """チェックポイント保存のテスト"""
        # チェックポイント保存実行
        checkpoint_id = content_processor.save_checkpoint("テストステップ")
        
        # 状態が保存されたことを確認
        mock_services["state_manager"].save_state.assert_called_once()
        
        # チェックポイント通知が送信されたことを確認
        mock_services["notifier_service"].send_checkpoint_notification.assert_called_once()
        
        # checkpoint_idが返されたことを確認
        assert checkpoint_id is not None

    def test_process_with_exception(self, content_processor, mock_services):
        """例外発生時の処理テスト"""
        # pre_processで例外が発生するようにモック
        with patch.object(content_processor, 'pre_process') as mock_pre_process:
            mock_pre_process.side_effect = ValueError("テスト例外")
            
            # エラーハンドラをモック
            with patch.object(content_processor, 'handle_error') as mock_handle_error:
                # 処理実行
                content_processor.process()
                
                # エラーハンドラが呼ばれたことを確認
                mock_handle_error.assert_called_once()
                args, _ = mock_handle_error.call_args
                assert isinstance(args[0], ValueError)
                assert str(args[0]) == "テスト例外"

    def test_setup_process_from_state(self, mock_services):
        """状態からの処理設定テスト"""
        # テスト状態データ
        state = {
            "step": "test_step",
            "data": {
                "title": "テストタイトル",
                "lang": "go",
                "progress_percentage": 50.0,
                "executables": [
                    {"name": "処理1", "completed": True},
                    {"name": "処理2", "completed": False}
                ]
            }
        }
        
        # 状態からプロセッサを作成
        processor = ContentProcessor.from_state(
            state=state,
            file_manager=mock_services["file_manager"],
            claude_service=mock_services["claude_service"],
            github_service=mock_services["github_service"],
            storage_service=mock_services["storage_service"],
            state_manager=mock_services["state_manager"],
            notifier=mock_services["notifier_service"]
        )
        
        # 状態が正しく復元されたことを確認
        assert processor.args.title == "テストタイトル"
        assert processor.args.lang == "go"
        assert processor.progress_percentage == 50.0
        
        # executablesの一部が完了状態であることを確認
        assert len(processor.executables) == 2
        assert processor.executables[0].get("completed") is True
        assert processor.executables[1].get("completed") is False

    def test_chunk_processing(self, content_processor):
        """チャンク処理のテスト"""
        # テスト項目リスト
        items = [f"item{i}" for i in range(10)]
        
        # プロセッサ関数のモック
        processor_func = MagicMock()
        
        # チャンク処理実行
        result = content_processor.chunk_processor(
            items=items,
            processor_func=processor_func,
            chunk_size=3  # 3つずつ処理
        )
        
        # プロセッサ関数の呼び出し回数確認
        assert processor_func.call_count == 4  # 3,3,3,1の4回
        
        # 呼び出し引数の検証
        calls = processor_func.call_args_list
        assert len(calls[0][0][0]) == 3  # 1回目: 3項目
        assert len(calls[1][0][0]) == 3  # 2回目: 3項目
        assert len(calls[2][0][0]) == 3  # 3回目: 3項目
        assert len(calls[3][0][0]) == 1  # 4回目: 1項目 