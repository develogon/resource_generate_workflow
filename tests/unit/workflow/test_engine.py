import pytest
import os
from unittest.mock import patch, MagicMock

# テスト対象のモジュールをインポート
from app.workflow.engine import WorkflowEngine
from app.workflow.task_manager import TaskManager, TaskType

class TestWorkflowEngine:
    """ワークフローエンジンのテストクラス"""
    
    @pytest.fixture
    def workflow_engine(self, tmp_path):
        """テスト用のワークフローエンジンインスタンスを作成"""
        config = {
            "checkpoint_dir": str(tmp_path / "checkpoints"),
        }
        engine = WorkflowEngine(config)
        return engine
    
    def test_workflow_initialization(self, workflow_engine):
        """ワークフローエンジンの初期化をテスト"""
        # ワークフローエンジンが正しく初期化されていることを確認
        assert workflow_engine is not None
        assert workflow_engine.task_manager is not None
        assert workflow_engine.checkpoint_manager is not None
        
        # 設定が反映されていることを確認
        assert "checkpoint_dir" in workflow_engine.config
    
    @patch('os.path.exists')
    def test_start_workflow(self, mock_exists, workflow_engine, tmp_path):
        """ワークフローの開始処理をテスト"""
        # モックの設定
        mock_exists.return_value = True
        
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # execute_task_loopをモックに置き換え
        workflow_engine.execute_task_loop = MagicMock(return_value=True)
        
        # ワークフローを開始
        input_path = str(tmp_path / "input.md")
        result = workflow_engine.start(input_path)
        
        # 結果の確認
        assert result is True
        mock_task_manager.register_task.assert_called()
        mock_checkpoint_manager.save_checkpoint.assert_called_with("INITIAL", {
            "input_path": input_path,
            "stage": "INITIALIZED"
        })
        workflow_engine.execute_task_loop.assert_called_once()
    
    @patch('app.workflow.checkpoint.CheckpointManager.load_checkpoint')
    @patch('app.workflow.checkpoint.CheckpointManager.restore_from_checkpoint')
    def test_resume_workflow(self, mock_restore, mock_load, workflow_engine):
        """ワークフローの再開処理をテスト"""
        # モックの設定
        mock_load.return_value = {
            "id": "checkpoint-001",
            "state": {"current_task": "task-003"}
        }
        mock_restore.return_value = True
        
        # execute_task_loopをモックに置き換え
        workflow_engine.execute_task_loop = MagicMock(return_value=True)
        
        # ワークフローを再開
        result = workflow_engine.resume("checkpoint-001")
        
        # 結果の確認
        assert result is True
        mock_load.assert_called_once_with("checkpoint-001")
        mock_restore.assert_called_once()
        workflow_engine.execute_task_loop.assert_called_once()
    
    @patch('app.workflow.task_manager.TaskManager.get_next_executable_task')
    @patch('app.workflow.task_manager.TaskManager.mark_as_completed')
    def test_execute_task_loop(self, mock_mark_completed, mock_get_task, workflow_engine):
        """タスク実行ループをテスト"""
        # モックの設定
        mock_get_task.side_effect = [
            {"id": "task-001", "type": "FILE_OPERATION", "params": {"operation": "READ"}},
            {"id": "task-002", "type": "API_CALL", "params": {"api": "TEST"}},
            None  # タスクがなくなったらNoneを返す
        ]
        
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # タスク実行メソッドをモックに置き換え
        workflow_engine._execute_task = MagicMock(return_value={"success": True})
        
        # タスク実行ループを実行
        result = workflow_engine.execute_task_loop()
        
        # 結果の確認
        assert result is True
        assert mock_get_task.call_count == 3
        assert mock_mark_completed.call_count == 2
        assert workflow_engine._execute_task.call_count == 2
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2
    
    def test_handle_error(self, workflow_engine):
        """エラー処理をテスト"""
        # チェックポイント管理システムのモック
        mock_checkpoint_manager = MagicMock()
        workflow_engine.checkpoint_manager = mock_checkpoint_manager
        
        # エラーハンドリングを実行
        error = Exception("テストエラー")
        context = {"task_id": "task-003"}
        result = workflow_engine.handle_error(error, context)
        
        # 結果の確認
        assert result is False
        mock_checkpoint_manager.save_checkpoint.assert_called_with("ERROR", {
            "error": str(error),
            "context": context
        })
        
    def test_register_initial_tasks(self, workflow_engine):
        """初期タスク登録処理をテスト"""
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # 初期タスク登録を実行
        input_path = "/path/to/input.md"
        workflow_engine._register_initial_tasks(input_path)
        
        # 結果の確認
        mock_task_manager.register_task.assert_called_once()
        # 引数の確認
        call_args = mock_task_manager.register_task.call_args[0][0]
        assert call_args["type"] == TaskType.FILE_OPERATION
        assert call_args["params"]["operation"] == "SPLIT_CHAPTERS"
        assert call_args["params"]["input_path"] == input_path
    
    def test_register_next_tasks_chapter_split(self, workflow_engine):
        """チャプター分割後のタスク登録処理をテスト"""
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # テスト用の結果データ
        task_result = {
            "success": True,
            "chapters": [
                {"title": "Chapter 1", "content": "Content 1"},
                {"title": "Chapter 2", "content": "Content 2"}
            ],
            "input_path": "/path/to/input.md"
        }
        
        # 次のタスク登録を実行
        workflow_engine._register_next_tasks(task_result)
        
        # 結果の確認
        assert mock_task_manager.register_task.call_count == 2
        # 各チャプターに対するタスク登録を確認
        for i, call in enumerate(mock_task_manager.register_task.call_args_list):
            args = call[0][0]
            assert args["type"] == TaskType.FILE_OPERATION
            assert args["params"]["operation"] == "SPLIT_SECTIONS"
            assert args["params"]["chapter_title"] == task_result["chapters"][i]["title"]
            assert args["params"]["chapter_content"] == task_result["chapters"][i]["content"]
            assert args["params"]["chapter_index"] == i + 1
    
    def test_register_next_tasks_section_split(self, workflow_engine):
        """セクション分割後のタスク登録処理をテスト"""
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # テスト用の結果データ
        task_result = {
            "success": True,
            "sections": [
                {"title": "Section 1", "content": "Content 1"},
                {"title": "Section 2", "content": "Content 2"}
            ]
        }
        
        # 次のタスク登録を実行
        workflow_engine._register_next_tasks(task_result)
        
        # 結果の確認
        assert mock_task_manager.register_task.call_count == 2
        # 各セクションに対するタスク登録を確認
        for i, call in enumerate(mock_task_manager.register_task.call_args_list):
            args = call[0][0]
            assert args["type"] == TaskType.API_CALL
            assert args["params"]["api"] == "CLAUDE"
            assert args["params"]["operation"] == "ANALYZE_STRUCTURE"
            assert args["params"]["section_title"] == task_result["sections"][i]["title"]
            assert args["params"]["section_content"] == task_result["sections"][i]["content"]
            assert args["params"]["section_index"] == i + 1
    
    @patch('app.processors.content.ContentProcessor')
    def test_execute_task_file_operation(self, mock_content_processor_class, workflow_engine):
        """ファイル操作タスクの実行をテスト"""
        # モックの設定
        mock_content_processor = MagicMock()
        mock_content_processor_class.return_value = mock_content_processor
        mock_content_processor.split_chapters.return_value = [
            {"title": "Chapter 1", "content": "Content 1"},
            {"title": "Chapter 2", "content": "Content 2"}
        ]
        
        # ファイルの読み込みをモック
        m_open = MagicMock()
        m_file = MagicMock()
        m_file.read.return_value = "File content"
        m_open.return_value.__enter__.return_value = m_file
        
        # タスク実行
        with patch("builtins.open", m_open):
            task = {
                "type": "FILE_OPERATION", 
                "params": {
                    "operation": "SPLIT_CHAPTERS",
                    "input_path": "/path/to/input.md"
                }
            }
            result = workflow_engine._execute_task(task)
        
        # 結果の確認
        assert result["success"] is True
        assert len(result["chapters"]) == 2
        assert result["input_path"] == "/path/to/input.md"
        mock_content_processor.split_chapters.assert_called_once_with("File content")
    
    def test_all_sections_processed(self, workflow_engine):
        """全セクション処理完了確認をテスト"""
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # モックタスクリストを設定
        mock_task_manager.get_all_tasks.return_value = [
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "SPLIT_SECTIONS", "chapter_index": 1},
                "result": {"sections": [{"title": "Section 1"}, {"title": "Section 2"}]}
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_SECTION_CONTENTS", "chapter_index": 1},
                "status": "COMPLETED"
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_SECTION_CONTENTS", "chapter_index": 1},
                "status": "COMPLETED"
            }
        ]
        
        # 全セクション処理完了確認を実行
        result = workflow_engine._all_sections_processed(1)
        
        # 結果の確認
        assert result is True
        
        # 処理完了数が少ない場合
        mock_task_manager.get_all_tasks.return_value = [
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "SPLIT_SECTIONS", "chapter_index": 1},
                "result": {"sections": [{"title": "Section 1"}, {"title": "Section 2"}]}
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_SECTION_CONTENTS", "chapter_index": 1},
                "status": "COMPLETED"
            }
        ]
        
        result = workflow_engine._all_sections_processed(1)
        assert result is False
    
    def test_all_chapters_processed(self, workflow_engine):
        """全チャプター処理完了確認をテスト"""
        # タスク管理システムのモック
        mock_task_manager = MagicMock()
        workflow_engine.task_manager = mock_task_manager
        
        # モックタスクリストを設定
        mock_task_manager.get_all_tasks.return_value = [
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "SPLIT_CHAPTERS"},
                "result": {"chapters": [{"title": "Chapter 1"}, {"title": "Chapter 2"}]}
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_CHAPTER_CONTENTS"},
                "status": "COMPLETED"
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_CHAPTER_CONTENTS"},
                "status": "COMPLETED"
            }
        ]
        
        # 全チャプター処理完了確認を実行
        result = workflow_engine._all_chapters_processed()
        
        # 結果の確認
        assert result is True
        
        # 処理完了数が少ない場合
        mock_task_manager.get_all_tasks.return_value = [
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "SPLIT_CHAPTERS"},
                "result": {"chapters": [{"title": "Chapter 1"}, {"title": "Chapter 2"}]}
            },
            {
                "type": TaskType.FILE_OPERATION,
                "params": {"operation": "COMBINE_CHAPTER_CONTENTS"},
                "status": "COMPLETED"
            }
        ]
        
        result = workflow_engine._all_chapters_processed()
        assert result is False 