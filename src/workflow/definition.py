"""ワークフロー定義システム."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml

from ..config.constants import TaskType
from ..models.task import Task
from ..parsers.yaml import YAMLParser


class WorkflowStepType(Enum):
    """ワークフローステップのタイプ."""
    
    PARSE = "parse"
    GENERATE = "generate"
    TRANSFORM = "transform"
    VALIDATE = "validate"
    SAVE = "save"
    NOTIFY = "notify"


class DependencyResolution(Enum):
    """依存関係解決の方法."""
    
    PARALLEL = "parallel"  # 並列実行可能
    SEQUENTIAL = "sequential"  # 順次実行
    CONDITIONAL = "conditional"  # 条件付き実行


@dataclass
class WorkflowStep:
    """ワークフローのステップ定義."""
    
    id: str
    name: str
    type: WorkflowStepType
    task_type: TaskType
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    timeout: int = 300  # デフォルト5分
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理."""
        if not self.id:
            self.id = str(uuid.uuid4())
        
        # デフォルトリトライポリシー
        if not self.retry_policy:
            self.retry_policy = {
                "max_attempts": 3,
                "backoff_multiplier": 2,
                "initial_delay": 1
            }
    
    def has_dependency(self, step_id: str) -> bool:
        """指定されたステップに依存しているかチェック."""
        return step_id in self.dependencies
    
    def can_execute(self, completed_steps: Set[str]) -> bool:
        """実行可能かチェック."""
        if not self.enabled:
            return False
        
        # 全ての依存関係が完了しているかチェック
        return all(dep in completed_steps for dep in self.dependencies)
    
    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """条件を評価."""
        if not self.conditions:
            return True
        
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
            
            actual_value = context[key]
            
            # 簡単な条件評価
            if isinstance(expected_value, dict):
                operator = expected_value.get("operator", "eq")
                value = expected_value.get("value")
                
                if operator == "eq" and actual_value != value:
                    return False
                elif operator == "ne" and actual_value == value:
                    return False
                elif operator == "gt" and actual_value <= value:
                    return False
                elif operator == "gte" and actual_value < value:
                    return False
                elif operator == "lt" and actual_value >= value:
                    return False
                elif operator == "lte" and actual_value > value:
                    return False
                elif operator == "in" and actual_value not in value:
                    return False
                elif operator == "not_in" and actual_value in value:
                    return False
            else:
                if actual_value != expected_value:
                    return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "task_type": self.task_type.value,
            "dependencies": self.dependencies,
            "parameters": self.parameters,
            "conditions": self.conditions,
            "retry_policy": self.retry_policy,
            "timeout": self.timeout,
            "enabled": self.enabled,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowStep:
        """辞書から作成."""
        return cls(
            id=data.get("id", ""),
            name=data["name"],
            type=WorkflowStepType(data["type"]),
            task_type=TaskType(data["task_type"]),
            dependencies=data.get("dependencies", []),
            parameters=data.get("parameters", {}),
            conditions=data.get("conditions", {}),
            retry_policy=data.get("retry_policy", {}),
            timeout=data.get("timeout", 300),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {})
        )


@dataclass
class WorkflowDefinition:
    """ワークフロー定義."""
    
    id: str
    name: str
    description: str
    version: str = "1.0.0"
    steps: List[WorkflowStep] = field(default_factory=list)
    global_parameters: Dict[str, Any] = field(default_factory=dict)
    global_conditions: Dict[str, Any] = field(default_factory=dict)
    resolution_strategy: DependencyResolution = DependencyResolution.SEQUENTIAL
    max_parallel_tasks: int = 5
    total_timeout: int = 3600  # 1時間
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初期化後の処理."""
        if not self.id:
            self.id = str(uuid.uuid4())
    
    def add_step(self, step: WorkflowStep) -> None:
        """ステップを追加."""
        # 重複IDチェック
        if any(s.id == step.id for s in self.steps):
            raise ValueError(f"Step with ID '{step.id}' already exists")
        
        self.steps.append(step)
    
    def remove_step(self, step_id: str) -> bool:
        """ステップを削除."""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                # 依存関係をチェック
                dependent_steps = [s for s in self.steps if step_id in s.dependencies]
                if dependent_steps:
                    raise ValueError(
                        f"Cannot remove step '{step_id}': "
                        f"it has dependencies from {[s.id for s in dependent_steps]}"
                    )
                
                del self.steps[i]
                return True
        return False
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """ステップを取得."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_executable_steps(self, completed_steps: Set[str]) -> List[WorkflowStep]:
        """実行可能なステップを取得."""
        executable = []
        
        for step in self.steps:
            if step.id not in completed_steps and step.can_execute(completed_steps):
                executable.append(step)
        
        return executable
    
    def validate_dependencies(self) -> Dict[str, Any]:
        """依存関係を検証."""
        errors = []
        warnings = []
        
        step_ids = {step.id for step in self.steps}
        
        # 存在しない依存関係をチェック
        for step in self.steps:
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(f"Step '{step.id}' depends on non-existent step '{dep}'")
        
        # 循環依存をチェック
        def has_cycle(step_id: str, visited: Set[str], path: Set[str]) -> bool:
            if step_id in path:
                return True
            if step_id in visited:
                return False
            
            visited.add(step_id)
            path.add(step_id)
            
            step = self.get_step(step_id)
            if step:
                for dep in step.dependencies:
                    if has_cycle(dep, visited, path):
                        return True
            
            path.remove(step_id)
            return False
        
        visited = set()
        for step in self.steps:
            if step.id not in visited:
                if has_cycle(step.id, visited, set()):
                    errors.append(f"Circular dependency detected involving step '{step.id}'")
        
        # ステップが多すぎる場合の警告
        if len(self.steps) > 50:
            warnings.append(f"Workflow has {len(self.steps)} steps, which might affect performance")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_execution_order(self) -> List[List[str]]:
        """実行順序を取得（並列実行可能なステップをグループ化）."""
        completed = set()
        execution_order = []
        
        while len(completed) < len(self.steps):
            # 現在実行可能なステップを取得
            executable = self.get_executable_steps(completed)
            
            if not executable:
                # デッドロック状態
                remaining = [s.id for s in self.steps if s.id not in completed]
                raise RuntimeError(f"Deadlock detected. Remaining steps: {remaining}")
            
            # 実行可能なステップをバッチとして追加
            batch = [step.id for step in executable]
            execution_order.append(batch)
            
            # 完了として記録
            completed.update(batch)
        
        return execution_order
    
    def estimate_duration(self) -> int:
        """推定実行時間を計算."""
        if self.resolution_strategy == DependencyResolution.SEQUENTIAL:
            return sum(step.timeout for step in self.steps)
        else:
            # 並列実行の場合は最長パスを計算
            return self._calculate_critical_path()
    
    def _calculate_critical_path(self) -> int:
        """クリティカルパスの長さを計算."""
        # 簡易実装：各ステップの最大時間を累積
        max_duration = 0
        
        try:
            execution_order = self.get_execution_order()
            for batch in execution_order:
                batch_duration = max(
                    self.get_step(step_id).timeout 
                    for step_id in batch 
                    if self.get_step(step_id)
                )
                max_duration += batch_duration
        except RuntimeError:
            # 循環依存がある場合はタイムアウト値を返す
            return self.total_timeout
        
        return max_duration
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [step.to_dict() for step in self.steps],
            "global_parameters": self.global_parameters,
            "global_conditions": self.global_conditions,
            "resolution_strategy": self.resolution_strategy.value,
            "max_parallel_tasks": self.max_parallel_tasks,
            "total_timeout": self.total_timeout,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowDefinition:
        """辞書から作成."""
        steps = [WorkflowStep.from_dict(step_data) for step_data in data.get("steps", [])]
        
        return cls(
            id=data.get("id", ""),
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            steps=steps,
            global_parameters=data.get("global_parameters", {}),
            global_conditions=data.get("global_conditions", {}),
            resolution_strategy=DependencyResolution(
                data.get("resolution_strategy", DependencyResolution.SEQUENTIAL.value)
            ),
            max_parallel_tasks=data.get("max_parallel_tasks", 5),
            total_timeout=data.get("total_timeout", 3600),
            metadata=data.get("metadata", {})
        )


class WorkflowLoader:
    """ワークフロー定義の読み込み."""
    
    def __init__(self):
        """初期化."""
        self.yaml_parser = YAMLParser()
    
    def load_from_file(self, file_path: Union[str, Path]) -> WorkflowDefinition:
        """ファイルからワークフロー定義を読み込み."""
        data = self.yaml_parser.parse_file(file_path)
        return WorkflowDefinition.from_dict(data)
    
    def load_from_string(self, yaml_content: str) -> WorkflowDefinition:
        """YAML文字列からワークフロー定義を読み込み."""
        data = self.yaml_parser.parse(yaml_content)
        return WorkflowDefinition.from_dict(data)
    
    def save_to_file(self, workflow: WorkflowDefinition, file_path: Union[str, Path]) -> None:
        """ワークフロー定義をファイルに保存."""
        data = workflow.to_dict()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data, 
                f, 
                allow_unicode=True, 
                default_flow_style=False,
                indent=2
            )
    
    def validate_workflow_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """ワークフローファイルを検証."""
        try:
            workflow = self.load_from_file(file_path)
            validation_result = workflow.validate_dependencies()
            
            return {
                "valid": validation_result["valid"],
                "errors": validation_result["errors"],
                "warnings": validation_result["warnings"],
                "workflow_summary": {
                    "name": workflow.name,
                    "steps": len(workflow.steps),
                    "estimated_duration": workflow.estimate_duration()
                }
            }
            
        except Exception as e:
            return {
                "valid": False,
                "errors": [f"Failed to load workflow: {str(e)}"],
                "warnings": [],
                "workflow_summary": None
            } 