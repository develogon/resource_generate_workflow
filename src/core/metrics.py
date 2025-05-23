"""
メトリクス収集システム - MetricsCollector

このモジュールはワークフローのパフォーマンス監視を担当します：
- メトリクス収集と集計
- パフォーマンス監視
- アラート機能
- 統計情報の提供
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Prometheusクライアントの可用性をチェック
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # モック実装
    class MockMetric:
        def inc(self, amount=1):
            pass
        def dec(self, amount=1):
            pass
        def set(self, value):
            pass
        def observe(self, value):
            pass
        def labels(self, **labels):
            return MockMetric()
    
    Counter = MockMetric
    Histogram = MockMetric
    Gauge = MockMetric
    Summary = MockMetric


class MetricType(Enum):
    """メトリクスタイプ"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class Metric:
    """メトリクスデータ構造"""
    name: str
    type: MetricType
    value: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "type": self.type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp
        }


@dataclass
class AlertRule:
    """アラートルール"""
    name: str
    metric_name: str
    condition: Callable[[float], bool]
    message: str
    cooldown_seconds: int = 300  # 5分
    last_triggered: float = 0.0


@dataclass
class MetricValue:
    """メトリクス値."""
    value: float
    timestamp: float = field(default_factory=time.time)
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """メトリクス収集システム
    
    ワークフローの実行状況をモニタリングし、
    パフォーマンスメトリクスを収集・分析する。
    """
    
    def __init__(self, max_metrics_history: int = 10000):
        self.max_metrics_history = max_metrics_history
        
        # メトリクスストレージ
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._timers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # メトリクス履歴
        self._metrics_history: deque = deque(maxlen=max_metrics_history)
        
        # アラート関連
        self._alert_rules: Dict[str, AlertRule] = {}
        self._alert_callbacks: List[Callable] = []
        
        # スレッドセーフティ
        self._lock = threading.RLock()
        
        # 統計情報
        self._start_time = time.time()
        self._total_metrics_collected = 0
        
        self._initialize_metrics()
        
    def _initialize_metrics(self):
        """メトリクスの初期化."""
        # カウンター
        self.workflows_started = Counter(
            'workflows_started_total',
            'Total number of workflows started'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.workflows_completed = Counter(
            'workflows_completed_total',
            'Total number of workflows completed'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.workflows_failed = Counter(
            'workflows_failed_total',
            'Total number of workflows failed'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.events_published = Counter(
            'events_published_total',
            'Total number of events published',
            ['event_type']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.events_processed = Counter(
            'events_processed_total',
            'Total number of events processed',
            ['event_type', 'status']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        # ヒストグラム
        self.processing_time = Histogram(
            'processing_time_seconds',
            'Time spent processing',
            ['task_type']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.api_response_time = Histogram(
            'api_response_time_seconds',
            'API response time',
            ['api_name', 'endpoint']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.workflow_duration = Histogram(
            'workflow_duration_seconds',
            'Workflow execution duration'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        # ゲージ
        self.active_workers = Gauge(
            'active_workers',
            'Number of active workers',
            ['worker_type']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.queue_size = Gauge(
            'queue_size',
            'Current queue size',
            ['queue_name']
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        self.active_workflows = Gauge(
            'active_workflows_total',
            'Number of currently active workflows'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        # サマリー
        self.content_generation_quality = Summary(
            'content_generation_quality',
            'Quality score of generated content'
        ) if PROMETHEUS_AVAILABLE else MockMetric()
        
        # 内部メトリクス（非Prometheus）
        self._internal_metrics: Dict[str, Any] = {}
        
    def increment_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None) -> None:
        """カウンターをインクリメント"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            self._counters[metric_key] += value
            
            self._record_metric(Metric(
                name=name,
                type=MetricType.COUNTER,
                value=self._counters[metric_key],
                labels=labels or {}
            ))
    
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """ゲージの値を設定"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            self._gauges[metric_key] = value
            
            self._record_metric(Metric(
                name=name,
                type=MetricType.GAUGE,
                value=value,
                labels=labels or {}
            ))
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """ヒストグラムに値を記録"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            self._histograms[metric_key].append(value)
            
            # ヒストグラムサイズ制限
            if len(self._histograms[metric_key]) > 10000:
                self._histograms[metric_key] = self._histograms[metric_key][-5000:]
            
            self._record_metric(Metric(
                name=name,
                type=MetricType.HISTOGRAM,
                value=value,
                labels=labels or {}
            ))
    
    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None) -> None:
        """タイマーの実行時間を記録"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            self._timers[metric_key].append(duration)
            
            self._record_metric(Metric(
                name=name,
                type=MetricType.TIMER,
                value=duration,
                labels=labels or {}
            ))
    
    @contextmanager
    def measure_time(self, metric_name: str, labels: Dict[str, str] = None):
        """処理時間の計測."""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            
            # Prometheusメトリクスに記録
            if hasattr(self, metric_name) and PROMETHEUS_AVAILABLE:
                metric = getattr(self, metric_name)
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
            
            # 内部メトリクスに記録
            self._record_internal_metric(metric_name, duration, labels)
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """カウンター値を取得"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            return self._counters.get(metric_key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """ゲージ値を取得"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            return self._gauges.get(metric_key)
    
    def get_histogram_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """ヒストグラムの統計情報を取得"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            values = self._histograms.get(metric_key, [])
            
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
            
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "p50": self._percentile(values, 0.5),
                "p95": self._percentile(values, 0.95),
                "p99": self._percentile(values, 0.99)
            }
    
    def get_timer_stats(self, name: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """タイマーの統計情報を取得"""
        with self._lock:
            metric_key = self._get_metric_key(name, labels)
            values = list(self._timers.get(metric_key, []))
            
            if not values:
                return {"count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0}
            
            return {
                "count": len(values),
                "sum": sum(values),
                "avg": sum(values) / len(values),
                "min": min(values),
                "max": max(values),
                "p50": self._percentile(values, 0.5),
                "p95": self._percentile(values, 0.95),
                "p99": self._percentile(values, 0.99)
            }
    
    def add_alert_rule(self, rule: AlertRule) -> None:
        """アラートルールを追加"""
        with self._lock:
            self._alert_rules[rule.name] = rule
            logger.info(f"Added alert rule: {rule.name}")
    
    def remove_alert_rule(self, rule_name: str) -> None:
        """アラートルールを削除"""
        with self._lock:
            if rule_name in self._alert_rules:
                del self._alert_rules[rule_name]
                logger.info(f"Removed alert rule: {rule_name}")
    
    def add_alert_callback(self, callback: Callable[[str, str], None]) -> None:
        """アラートコールバックを追加"""
        self._alert_callbacks.append(callback)
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスを取得"""
        with self._lock:
            metrics = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {},
                "timers": {},
                "metadata": {
                    "start_time": self._start_time,
                    "uptime": time.time() - self._start_time,
                    "total_metrics_collected": self._total_metrics_collected,
                    "metrics_history_size": len(self._metrics_history)
                }
            }
            
            # ヒストグラム統計
            for key in self._histograms:
                metrics["histograms"][key] = self.get_histogram_stats(
                    *self._parse_metric_key(key)
                )
            
            # タイマー統計
            for key in self._timers:
                metrics["timers"][key] = self.get_timer_stats(
                    *self._parse_metric_key(key)
                )
            
            return metrics
    
    def get_metrics_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """メトリクス履歴を取得"""
        with self._lock:
            history = list(self._metrics_history)
            if limit:
                history = history[-limit:]
            return [metric.to_dict() for metric in history]
    
    def reset_metrics(self) -> None:
        """全メトリクスをリセット"""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._timers.clear()
            self._metrics_history.clear()
            self._total_metrics_collected = 0
            logger.info("All metrics reset")
    
    def export_prometheus_format(self) -> str:
        """Prometheus形式でメトリクスをエクスポート"""
        lines = []
        
        with self._lock:
            # カウンター
            for key, value in self._counters.items():
                name, labels = self._parse_metric_key(key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name}{label_str} {value}")
            
            # ゲージ
            for key, value in self._gauges.items():
                name, labels = self._parse_metric_key(key)
                label_str = self._format_prometheus_labels(labels)
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name}{label_str} {value}")
            
            # ヒストグラム（統計情報のみ）
            for key in self._histograms:
                name, labels = self._parse_metric_key(key)
                stats = self.get_histogram_stats(name, labels)
                label_str = self._format_prometheus_labels(labels)
                
                lines.append(f"# TYPE {name} histogram")
                lines.append(f"{name}_count{label_str} {stats['count']}")
                lines.append(f"{name}_sum{label_str} {stats['sum']}")
                lines.append(f"{name}_avg{label_str} {stats['avg']}")
        
        return "\n".join(lines)
    
    def _record_metric(self, metric: Metric) -> None:
        """メトリクスを記録"""
        self._metrics_history.append(metric)
        self._total_metrics_collected += 1
        
        # アラートチェック
        self._check_alerts(metric)
    
    def _check_alerts(self, metric: Metric) -> None:
        """アラートルールをチェック"""
        current_time = time.time()
        
        for rule in self._alert_rules.values():
            if (rule.metric_name == metric.name and 
                current_time - rule.last_triggered > rule.cooldown_seconds):
                
                if rule.condition(metric.value):
                    rule.last_triggered = current_time
                    self._trigger_alert(rule, metric)
    
    def _trigger_alert(self, rule: AlertRule, metric: Metric) -> None:
        """アラートを発生"""
        message = f"ALERT: {rule.message} (metric: {metric.name}={metric.value})"
        logger.warning(message)
        
        # コールバック実行
        for callback in self._alert_callbacks:
            try:
                callback(rule.name, message)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")
    
    def _get_metric_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """メトリクスキーを生成"""
        if not labels:
            return name
        
        label_parts = [f"{k}={v}" for k, v in sorted(labels.items())]
        return f"{name}{{{','.join(label_parts)}}}"
    
    def _parse_metric_key(self, key: str) -> tuple[str, Dict[str, str]]:
        """メトリクスキーをパース"""
        if "{" not in key:
            return key, {}
        
        name, label_part = key.split("{", 1)
        label_part = label_part.rstrip("}")
        
        labels = {}
        if label_part:
            for pair in label_part.split(","):
                k, v = pair.split("=", 1)
                labels[k] = v
        
        return name, labels
    
    def _format_prometheus_labels(self, labels: Dict[str, str]) -> str:
        """Prometheus形式のラベル文字列を生成"""
        if not labels:
            return ""
        
        label_pairs = [f'{k}="{v}"' for k, v in sorted(labels.items())]
        return "{" + ",".join(label_pairs) + "}"
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """パーセンタイル値を計算"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        
        if index >= len(sorted_values):
            return sorted_values[-1]
        
        return sorted_values[index]

    def _record_internal_metric(self, name: str, value: float, labels: Dict[str, str] = None):
        """内部メトリクスの記録."""
        metric_key = f"{name}:{str(labels) if labels else 'default'}"
        
        if metric_key not in self._internal_metrics:
            self._internal_metrics[metric_key] = []
            
        self._internal_metrics[metric_key].append(MetricValue(
            value=value,
            labels=labels or {}
        ))
        
        # 古いメトリクスを削除（最新100件のみ保持）
        if len(self._internal_metrics[metric_key]) > 100:
            self._internal_metrics[metric_key] = self._internal_metrics[metric_key][-100:]
            
    def record_workflow_started(self, workflow_id: str):
        """ワークフロー開始の記録."""
        self.workflows_started.inc()
        logger.debug(f"Recorded workflow started: {workflow_id}")
        
    def record_workflow_completed(self, workflow_id: str, duration: float):
        """ワークフロー完了の記録."""
        self.workflows_completed.inc()
        self.workflow_duration.observe(duration)
        logger.debug(f"Recorded workflow completed: {workflow_id} in {duration:.2f}s")
        
    def record_workflow_failed(self, workflow_id: str, error: str):
        """ワークフロー失敗の記録."""
        self.workflows_failed.inc()
        logger.debug(f"Recorded workflow failed: {workflow_id} - {error}")
        
    def record_event_published(self, event_type: str):
        """イベント発行の記録."""
        if PROMETHEUS_AVAILABLE:
            self.events_published.labels(event_type=event_type).inc()
        
    def record_event_processed(self, event_type: str, status: str):
        """イベント処理の記録."""
        if PROMETHEUS_AVAILABLE:
            self.events_processed.labels(event_type=event_type, status=status).inc()
        
    def set_active_workers(self, worker_type: str, count: int):
        """アクティブワーカー数の設定."""
        if PROMETHEUS_AVAILABLE:
            self.active_workers.labels(worker_type=worker_type).set(count)
        
    def set_queue_size(self, queue_name: str, size: int):
        """キューサイズの設定."""
        if PROMETHEUS_AVAILABLE:
            self.queue_size.labels(queue_name=queue_name).set(size)
        
    def set_active_workflows(self, count: int):
        """アクティブワークフロー数の設定."""
        self.active_workflows.set(count)
        
    def record_api_call(self, api_name: str, endpoint: str, response_time: float):
        """API呼び出しの記録."""
        if PROMETHEUS_AVAILABLE:
            self.api_response_time.labels(api_name=api_name, endpoint=endpoint).observe(response_time)
        
    def record_content_quality(self, quality_score: float):
        """コンテンツ品質の記録."""
        self.content_generation_quality.observe(quality_score)
        
    def get_internal_metrics(self, metric_name: Optional[str] = None) -> Dict[str, Any]:
        """内部メトリクスの取得."""
        if metric_name:
            return {k: v for k, v in self._internal_metrics.items() if k.startswith(metric_name)}
        return self._internal_metrics.copy()
        
    def get_metric_summary(self) -> Dict[str, Any]:
        """メトリクスサマリーの取得."""
        summary = {}
        
        # 内部メトリクスの統計
        for metric_key, values in self._internal_metrics.items():
            if values:
                metric_values = [v.value for v in values]
                summary[metric_key] = {
                    "count": len(metric_values),
                    "min": min(metric_values),
                    "max": max(metric_values),
                    "avg": sum(metric_values) / len(metric_values),
                    "latest": metric_values[-1]
                }
                
        return summary
        
    def clear_internal_metrics(self):
        """内部メトリクスのクリア."""
        self._internal_metrics.clear()
        logger.info("Internal metrics cleared")


class WorkflowMetrics:
    """ワークフロー専用メトリクス収集クラス"""
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics = metrics_collector
    
    def record_workflow_started(self, workflow_id: str) -> None:
        """ワークフロー開始を記録"""
        self.metrics.increment_counter(
            "workflow_started_total",
            labels={"workflow_id": workflow_id}
        )
    
    def record_workflow_completed(self, workflow_id: str, duration: float) -> None:
        """ワークフロー完了を記録"""
        self.metrics.increment_counter(
            "workflow_completed_total",
            labels={"workflow_id": workflow_id}
        )
        self.metrics.record_timer(
            "workflow_duration_seconds",
            duration,
            labels={"workflow_id": workflow_id}
        )
    
    def record_workflow_failed(self, workflow_id: str, error_type: str) -> None:
        """ワークフロー失敗を記録"""
        self.metrics.increment_counter(
            "workflow_failed_total",
            labels={"workflow_id": workflow_id, "error_type": error_type}
        )
    
    def record_task_completed(self, workflow_id: str, task_type: str, duration: float) -> None:
        """タスク完了を記録"""
        self.metrics.increment_counter(
            "task_completed_total",
            labels={"workflow_id": workflow_id, "task_type": task_type}
        )
        self.metrics.record_timer(
            "task_duration_seconds",
            duration,
            labels={"workflow_id": workflow_id, "task_type": task_type}
        )
    
    def record_task_failed(self, workflow_id: str, task_type: str, error_type: str) -> None:
        """タスク失敗を記録"""
        self.metrics.increment_counter(
            "task_failed_total",
            labels={
                "workflow_id": workflow_id,
                "task_type": task_type,
                "error_type": error_type
            }
        )
    
    def set_active_workflows(self, count: int) -> None:
        """アクティブワークフロー数を設定"""
        self.metrics.set_gauge("active_workflows", count)
    
    def set_queue_size(self, queue_name: str, size: int) -> None:
        """キューサイズを設定"""
        self.metrics.set_gauge(
            "queue_size",
            size,
            labels={"queue": queue_name}
        )


class PerformanceMonitor:
    """パフォーマンス監視."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """初期化."""
        self.metrics = metrics_collector
        self._thresholds = {
            "workflow_duration": 300.0,  # 5分
            "api_response_time": 10.0,   # 10秒
            "queue_size": 1000           # 1000件
        }
        
    def check_performance_thresholds(self) -> List[str]:
        """パフォーマンス閾値のチェック."""
        warnings = []
        
        # 内部メトリクスから最新値をチェック
        metrics = self.metrics.get_internal_metrics()
        
        for metric_key, values in metrics.items():
            if not values:
                continue
                
            latest_value = values[-1].value
            
            # 閾値チェック
            for threshold_key, threshold_value in self._thresholds.items():
                if threshold_key in metric_key and latest_value > threshold_value:
                    warnings.append(
                        f"Performance warning: {metric_key} = {latest_value:.2f} "
                        f"exceeds threshold {threshold_value:.2f}"
                    )
                    
        return warnings
        
    def set_threshold(self, metric: str, value: float):
        """閾値の設定."""
        self._thresholds[metric] = value
        
    def get_thresholds(self) -> Dict[str, float]:
        """閾値の取得."""
        return self._thresholds.copy() 