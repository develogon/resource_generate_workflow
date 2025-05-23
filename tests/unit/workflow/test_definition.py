"""ワークフロー定義システムのテスト."""

import tempfile
from pathlib import Path

import pytest

from src.config.constants import TaskType
from src.workflow.definition import (
    DependencyResolution,
    WorkflowDefinition,
    WorkflowLoader,
    WorkflowStep,
    WorkflowStepType,
)


class TestWorkflowStep:
    """WorkflowStepのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        step = WorkflowStep(
            id="step1",
            name="テストステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        assert step.id == "step1"
        assert step.name == "テストステップ"
        assert step.type == WorkflowStepType.PARSE
        assert step.task_type == TaskType.PARSE_CHAPTER
        assert step.dependencies == []
        assert step.timeout == 300
        assert step.enabled is True
        assert "max_attempts" in step.retry_policy
    
    def test_auto_id_generation(self):
        """自動ID生成のテスト."""
        step = WorkflowStep(
            id="",
            name="テスト",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        assert step.id != ""
        assert len(step.id) == 36  # UUID形式
    
    def test_dependency_check(self):
        """依存関係チェックのテスト."""
        step = WorkflowStep(
            id="step1",
            name="テスト",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            dependencies=["step0"]
        )
        
        assert step.has_dependency("step0")
        assert not step.has_dependency("step2")
    
    def test_can_execute(self):
        """実行可能チェックのテスト."""
        step = WorkflowStep(
            id="step1",
            name="テスト",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            dependencies=["step0"]
        )
        
        # 依存関係が完了していない場合
        assert not step.can_execute(set())
        
        # 依存関係が完了している場合
        assert step.can_execute({"step0"})
        
        # ステップが無効化されている場合
        step.enabled = False
        assert not step.can_execute({"step0"})
    
    def test_condition_evaluation(self):
        """条件評価のテスト."""
        step = WorkflowStep(
            id="step1",
            name="テスト",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            conditions={
                "input_format": "markdown",
                "file_size": {"operator": "lt", "value": 1000000}
            }
        )
        
        # 条件を満たす場合
        context = {
            "input_format": "markdown",
            "file_size": 500000
        }
        assert step.evaluate_conditions(context)
        
        # 条件を満たさない場合
        context = {
            "input_format": "text",
            "file_size": 500000
        }
        assert not step.evaluate_conditions(context)
        
        # サイズ条件を満たさない場合
        context = {
            "input_format": "markdown",
            "file_size": 2000000
        }
        assert not step.evaluate_conditions(context)
    
    def test_dict_conversion(self):
        """辞書変換のテスト."""
        step = WorkflowStep(
            id="step1",
            name="テストステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            dependencies=["step0"],
            timeout=600
        )
        
        data = step.to_dict()
        
        assert data["id"] == "step1"
        assert data["name"] == "テストステップ"
        assert data["type"] == "parse"
        assert data["task_type"] == "parse_chapter"
        assert data["dependencies"] == ["step0"]
        assert data["timeout"] == 600
        
        # 辞書から復元
        restored_step = WorkflowStep.from_dict(data)
        assert restored_step.id == step.id
        assert restored_step.name == step.name
        assert restored_step.type == step.type
        assert restored_step.task_type == step.task_type


class TestWorkflowDefinition:
    """WorkflowDefinitionのテスト."""
    
    def test_initialization(self):
        """初期化のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テストワークフロー",
            description="テスト用のワークフロー"
        )
        
        assert workflow.id == "workflow1"
        assert workflow.name == "テストワークフロー"
        assert workflow.description == "テスト用のワークフロー"
        assert workflow.version == "1.0.0"
        assert workflow.steps == []
        assert workflow.resolution_strategy == DependencyResolution.SEQUENTIAL
    
    def test_auto_id_generation(self):
        """自動ID生成のテスト."""
        workflow = WorkflowDefinition(
            id="",
            name="テスト",
            description="テスト"
        )
        
        assert workflow.id != ""
        assert len(workflow.id) == 36
    
    def test_add_step(self):
        """ステップ追加のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step1)
        assert len(workflow.steps) == 1
        assert workflow.get_step("step1") == step1
        
        # 重複ID追加でエラー
        step1_dup = WorkflowStep(
            id="step1",
            name="重複ステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        with pytest.raises(ValueError, match="already exists"):
            workflow.add_step(step1_dup)
    
    def test_remove_step(self):
        """ステップ削除のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        # 依存関係があるステップの削除でエラー
        with pytest.raises(ValueError, match="it has dependencies"):
            workflow.remove_step("step1")
        
        # 依存関係がないステップの削除は成功
        assert workflow.remove_step("step2")
        assert len(workflow.steps) == 1
        
        # 今度はstep1を削除できる
        assert workflow.remove_step("step1")
        assert len(workflow.steps) == 0
        
        # 存在しないステップの削除
        assert not workflow.remove_step("nonexistent")
    
    def test_get_executable_steps(self):
        """実行可能ステップ取得のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        step3 = WorkflowStep(
            id="step3",
            name="ステップ3",
            type=WorkflowStepType.SAVE,
            task_type=TaskType.UPLOAD_S3
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        workflow.add_step(step3)
        
        # 初期状態：step1とstep3が実行可能
        executable = workflow.get_executable_steps(set())
        executable_ids = {step.id for step in executable}
        assert executable_ids == {"step1", "step3"}
        
        # step1完了後：step2が実行可能
        executable = workflow.get_executable_steps({"step1"})
        executable_ids = {step.id for step in executable}
        assert executable_ids == {"step2", "step3"}
    
    def test_validate_dependencies(self):
        """依存関係検証のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1", "nonexistent"]  # 存在しない依存関係
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        result = workflow.validate_dependencies()
        
        assert not result["valid"]
        assert len(result["errors"]) == 1
        assert "nonexistent" in result["errors"][0]
    
    def test_circular_dependency_detection(self):
        """循環依存検出のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            dependencies=["step3"]
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        step3 = WorkflowStep(
            id="step3",
            name="ステップ3",
            type=WorkflowStepType.SAVE,
            task_type=TaskType.UPLOAD_S3,
            dependencies=["step2"]
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        workflow.add_step(step3)
        
        result = workflow.validate_dependencies()
        
        assert not result["valid"]
        assert any("Circular dependency" in error for error in result["errors"])
    
    def test_execution_order(self):
        """実行順序取得のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            dependencies=["step1"]
        )
        
        step3 = WorkflowStep(
            id="step3",
            name="ステップ3",
            type=WorkflowStepType.SAVE,
            task_type=TaskType.UPLOAD_S3
        )
        
        step4 = WorkflowStep(
            id="step4",
            name="ステップ4",
            type=WorkflowStepType.VALIDATE,
            task_type=TaskType.GENERATE_METADATA,
            dependencies=["step2", "step3"]
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        workflow.add_step(step3)
        workflow.add_step(step4)
        
        execution_order = workflow.get_execution_order()
        
        # step1とstep3が最初のバッチ
        assert set(execution_order[0]) == {"step1", "step3"}
        # step2が2番目のバッチ
        assert execution_order[1] == ["step2"]
        # step4が最後のバッチ
        assert execution_order[2] == ["step4"]
    
    def test_duration_estimation(self):
        """実行時間推定のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テスト",
            description="テスト",
            resolution_strategy=DependencyResolution.SEQUENTIAL
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER,
            timeout=100
        )
        
        step2 = WorkflowStep(
            id="step2",
            name="ステップ2",
            type=WorkflowStepType.GENERATE,
            task_type=TaskType.GENERATE_ARTICLE,
            timeout=200
        )
        
        workflow.add_step(step1)
        workflow.add_step(step2)
        
        # 順次実行の場合は合計時間
        assert workflow.estimate_duration() == 300
    
    def test_dict_conversion(self):
        """辞書変換のテスト."""
        workflow = WorkflowDefinition(
            id="workflow1",
            name="テストワークフロー",
            description="テスト用"
        )
        
        step1 = WorkflowStep(
            id="step1",
            name="ステップ1",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step1)
        
        data = workflow.to_dict()
        
        assert data["id"] == "workflow1"
        assert data["name"] == "テストワークフロー"
        assert len(data["steps"]) == 1
        
        # 辞書から復元
        restored_workflow = WorkflowDefinition.from_dict(data)
        assert restored_workflow.id == workflow.id
        assert restored_workflow.name == workflow.name
        assert len(restored_workflow.steps) == 1


class TestWorkflowLoader:
    """WorkflowLoaderのテスト."""
    
    def test_load_from_string(self):
        """文字列からの読み込みテスト."""
        yaml_content = """
id: test-workflow
name: テストワークフロー
description: テスト用のワークフロー
version: 1.0.0
steps:
  - id: step1
    name: Markdownパース
    type: parse
    task_type: parse_chapter
    timeout: 300
  - id: step2
    name: 記事生成
    type: generate
    task_type: generate_article
    dependencies:
      - step1
    timeout: 600
resolution_strategy: sequential
max_parallel_tasks: 3
"""
        
        loader = WorkflowLoader()
        workflow = loader.load_from_string(yaml_content)
        
        assert workflow.id == "test-workflow"
        assert workflow.name == "テストワークフロー"
        assert len(workflow.steps) == 2
        assert workflow.max_parallel_tasks == 3
        
        step1 = workflow.get_step("step1")
        assert step1.name == "Markdownパース"
        assert step1.type == WorkflowStepType.PARSE
        assert step1.task_type == TaskType.PARSE_CHAPTER
        
        step2 = workflow.get_step("step2")
        assert step2.dependencies == ["step1"]
    
    def test_load_from_file(self):
        """ファイルからの読み込みテスト."""
        yaml_content = """
id: file-workflow
name: ファイルワークフロー
description: ファイルから読み込んだワークフロー
steps:
  - id: step1
    name: テストステップ
    type: parse
    task_type: parse_chapter
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader()
            workflow = loader.load_from_file(temp_path)
            
            assert workflow.id == "file-workflow"
            assert workflow.name == "ファイルワークフロー"
            assert len(workflow.steps) == 1
        finally:
            temp_path.unlink()
    
    def test_save_to_file(self):
        """ファイルへの保存テスト."""
        workflow = WorkflowDefinition(
            id="save-test",
            name="保存テスト",
            description="保存テスト用"
        )
        
        step = WorkflowStep(
            id="step1",
            name="テストステップ",
            type=WorkflowStepType.PARSE,
            task_type=TaskType.PARSE_CHAPTER
        )
        
        workflow.add_step(step)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader()
            loader.save_to_file(workflow, temp_path)
            
            # 保存されたファイルを読み込んで検証
            loaded_workflow = loader.load_from_file(temp_path)
            
            assert loaded_workflow.id == workflow.id
            assert loaded_workflow.name == workflow.name
            assert len(loaded_workflow.steps) == 1
        finally:
            temp_path.unlink()
    
    def test_validate_workflow_file(self):
        """ワークフローファイル検証のテスト."""
        yaml_content = """
id: validation-test
name: バリデーションテスト
description: バリデーション用
steps:
  - id: step1
    name: ステップ1
    type: parse
    task_type: parse_chapter
  - id: step2
    name: ステップ2
    type: generate
    task_type: generate_article
    dependencies:
      - step1
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader()
            result = loader.validate_workflow_file(temp_path)
            
            assert result["valid"]
            assert len(result["errors"]) == 0
            assert result["workflow_summary"]["name"] == "バリデーションテスト"
            assert result["workflow_summary"]["steps"] == 2
        finally:
            temp_path.unlink()
    
    def test_validate_invalid_workflow_file(self):
        """無効なワークフローファイルの検証テスト."""
        yaml_content = """
id: invalid-workflow
name: 無効なワークフロー
description: 無効な依存関係を持つワークフロー
steps:
  - id: step1
    name: ステップ1
    type: parse
    task_type: parse_chapter
    dependencies:
      - nonexistent_step  # 存在しない依存関係
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            temp_path = Path(f.name)
        
        try:
            loader = WorkflowLoader()
            result = loader.validate_workflow_file(temp_path)
            
            assert not result["valid"]
            assert len(result["errors"]) > 0
            assert "nonexistent_step" in result["errors"][0]
        finally:
            temp_path.unlink()