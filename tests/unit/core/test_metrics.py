"""
MetricsCollectorの単体テスト

MetricsCollector、Metric、AlertRule、WorkflowMetricsクラスの機能をテストします：
- メトリクス収集（カウンター、ゲージ、ヒストグラム、タイマー）
- 統計計算とパーセンタイル
- アラート機能
- Prometheus形式エクスポート
- ワークフロー専用メトリクス
"""

import pytest
import time
from unittest.mock import Mock, call

from src.core.metrics import (
    MetricsCollector,
    Metric,
    MetricType,
    AlertRule,
    WorkflowMetrics
)


@pytest.fixture
def metrics_collector():
    """MetricsCollectorのフィクスチャ"""
    return MetricsCollector(max_metrics_history=100)


@pytest.fixture
def workflow_metrics(metrics_collector):
    """WorkflowMetricsのフィクスチャ"""
    return WorkflowMetrics(metrics_collector)


class TestMetric:
    """Metricクラスのテスト"""
    
    def test_metric_creation(self):
        """メトリクスの作成テスト"""
        metric = Metric(
            name="test_counter",
            type=MetricType.COUNTER,
            value=42.0,
            labels={"service": "test"}
        )
        
        assert metric.name == "test_counter"
        assert metric.type == MetricType.COUNTER
        assert metric.value == 42.0
        assert metric.labels == {"service": "test"}
        assert metric.timestamp > 0
    
    def test_metric_to_dict(self):
        """メトリクスの辞書変換テスト"""
        metric = Metric(
            name="test_gauge",
            type=MetricType.GAUGE,
            value=100.5,
            labels={"env": "prod"},
            timestamp=1234567890.0
        )
        
        result = metric.to_dict()
        
        assert result["name"] == "test_gauge"
        assert result["type"] == "gauge"
        assert result["value"] == 100.5
        assert result["labels"] == {"env": "prod"}
        assert result["timestamp"] == 1234567890.0


class TestAlertRule:
    """AlertRuleクラスのテスト"""
    
    def test_alert_rule_creation(self):
        """アラートルールの作成テスト"""
        rule = AlertRule(
            name="high_error_rate",
            metric_name="error_rate",
            condition=lambda x: x > 0.1,
            message="Error rate is too high",
            cooldown_seconds=60
        )
        
        assert rule.name == "high_error_rate"
        assert rule.metric_name == "error_rate"
        assert rule.condition(0.2) is True
        assert rule.condition(0.05) is False
        assert rule.message == "Error rate is too high"
        assert rule.cooldown_seconds == 60


class TestMetricsCollector:
    """MetricsCollectorクラスのテスト"""
    
    def test_increment_counter(self, metrics_collector):
        """カウンター増加テスト"""
        metrics_collector.increment_counter("test_counter")
        assert metrics_collector.get_counter("test_counter") == 1.0
        
        metrics_collector.increment_counter("test_counter", 5.0)
        assert metrics_collector.get_counter("test_counter") == 6.0
    
    def test_increment_counter_with_labels(self, metrics_collector):
        """ラベル付きカウンター増加テスト"""
        metrics_collector.increment_counter("requests_total", labels={"method": "GET"})
        metrics_collector.increment_counter("requests_total", labels={"method": "POST"})
        metrics_collector.increment_counter("requests_total", labels={"method": "GET"})
        
        assert metrics_collector.get_counter("requests_total", {"method": "GET"}) == 2.0
        assert metrics_collector.get_counter("requests_total", {"method": "POST"}) == 1.0
        assert metrics_collector.get_counter("requests_total", {"method": "DELETE"}) == 0.0
    
    def test_set_gauge(self, metrics_collector):
        """ゲージ設定テスト"""
        metrics_collector.set_gauge("temperature", 25.5)
        assert metrics_collector.get_gauge("temperature") == 25.5
        
        metrics_collector.set_gauge("temperature", 30.0)
        assert metrics_collector.get_gauge("temperature") == 30.0
    
    def test_set_gauge_with_labels(self, metrics_collector):
        """ラベル付きゲージ設定テスト"""
        metrics_collector.set_gauge("cpu_usage", 50.0, {"core": "0"})
        metrics_collector.set_gauge("cpu_usage", 75.0, {"core": "1"})
        
        assert metrics_collector.get_gauge("cpu_usage", {"core": "0"}) == 50.0
        assert metrics_collector.get_gauge("cpu_usage", {"core": "1"}) == 75.0
        assert metrics_collector.get_gauge("cpu_usage", {"core": "2"}) is None
    
    def test_record_histogram(self, metrics_collector):
        """ヒストグラム記録テスト"""
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            metrics_collector.record_histogram("response_time", value)
        
        stats = metrics_collector.get_histogram_stats("response_time")
        
        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["avg"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
    
    def test_record_timer(self, metrics_collector):
        """タイマー記録テスト"""
        durations = [0.1, 0.2, 0.15, 0.3, 0.25]
        for duration in durations:
            metrics_collector.record_timer("processing_time", duration)
        
        stats = metrics_collector.get_timer_stats("processing_time")
        
        assert stats["count"] == 5
        assert abs(stats["sum"] - 1.0) < 0.001
        assert abs(stats["avg"] - 0.2) < 0.001
        assert stats["min"] == 0.1
        assert stats["max"] == 0.3
    
    def test_histogram_percentiles(self, metrics_collector):
        """ヒストグラムパーセンタイルテスト"""
        # 1から100まで記録
        for i in range(1, 101):
            metrics_collector.record_histogram("test_metric", float(i))
        
        stats = metrics_collector.get_histogram_stats("test_metric")
        
        assert stats["count"] == 100
        # パーセンタイル計算は実装によって若干の誤差があるため、範囲で確認
        assert 49.0 <= stats["p50"] <= 51.0  # 中央値（50付近）
        assert 94.0 <= stats["p95"] <= 96.0  # 95パーセンタイル（95付近）
        assert 98.0 <= stats["p99"] <= 100.0  # 99パーセンタイル（99付近）
    
    def test_measure_time_context_manager(self, metrics_collector):
        """時間測定コンテキストマネージャーテスト"""
        with metrics_collector.measure_time("operation_duration"):
            time.sleep(0.01)  # 短時間スリープ
        
        stats = metrics_collector.get_timer_stats("operation_duration")
        assert stats["count"] == 1
        assert stats["avg"] >= 0.01  # 最低でも10ms以上
    
    def test_get_empty_stats(self, metrics_collector):
        """空のメトリクス統計テスト"""
        histogram_stats = metrics_collector.get_histogram_stats("nonexistent")
        timer_stats = metrics_collector.get_timer_stats("nonexistent")
        
        expected_empty = {
            "count": 0, "sum": 0.0, "avg": 0.0, "min": 0.0, "max": 0.0
        }
        
        for key, value in expected_empty.items():
            assert histogram_stats[key] == value
            assert timer_stats[key] == value
    
    def test_alert_rules(self, metrics_collector):
        """アラートルールテスト"""
        # アラートコールバックのモック
        alert_callback = Mock()
        metrics_collector.add_alert_callback(alert_callback)
        
        # アラートルール追加
        rule = AlertRule(
            name="high_value",
            metric_name="test_metric",
            condition=lambda x: x > 100,
            message="Value is too high"
        )
        metrics_collector.add_alert_rule(rule)
        
        # 閾値以下の値（アラートなし）
        metrics_collector.set_gauge("test_metric", 50.0)
        alert_callback.assert_not_called()
        
        # 閾値超過（アラート発生）
        metrics_collector.set_gauge("test_metric", 150.0)
        alert_callback.assert_called_once()
        
        # アラートルール削除
        metrics_collector.remove_alert_rule("high_value")
        alert_callback.reset_mock()
        
        metrics_collector.set_gauge("test_metric", 200.0)
        alert_callback.assert_not_called()
    
    def test_alert_cooldown(self, metrics_collector):
        """アラートクールダウンテスト"""
        alert_callback = Mock()
        metrics_collector.add_alert_callback(alert_callback)
        
        # 短いクールダウンでアラートルール追加
        rule = AlertRule(
            name="test_alert",
            metric_name="test_metric",
            condition=lambda x: x > 10,
            message="Test alert",
            cooldown_seconds=1
        )
        metrics_collector.add_alert_rule(rule)
        
        # 最初のアラート
        metrics_collector.set_gauge("test_metric", 20.0)
        assert alert_callback.call_count == 1
        
        # クールダウン中（アラートなし）
        metrics_collector.set_gauge("test_metric", 30.0)
        assert alert_callback.call_count == 1
        
        # クールダウン後（アラート発生）
        time.sleep(1.1)
        metrics_collector.set_gauge("test_metric", 40.0)
        assert alert_callback.call_count == 2
    
    def test_get_all_metrics(self, metrics_collector):
        """全メトリクス取得テスト"""
        # 各種メトリクスを記録
        metrics_collector.increment_counter("counter_test", 5.0)
        metrics_collector.set_gauge("gauge_test", 42.0)
        metrics_collector.record_histogram("histogram_test", 10.0)
        metrics_collector.record_timer("timer_test", 0.5)
        
        all_metrics = metrics_collector.get_all_metrics()
        
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timers" in all_metrics
        assert "metadata" in all_metrics
        
        assert all_metrics["counters"]["counter_test"] == 5.0
        assert all_metrics["gauges"]["gauge_test"] == 42.0
        assert all_metrics["histograms"]["histogram_test"]["count"] == 1
        assert all_metrics["timers"]["timer_test"]["count"] == 1
        
        metadata = all_metrics["metadata"]
        assert "start_time" in metadata
        assert "uptime" in metadata
        assert "total_metrics_collected" in metadata
    
    def test_metrics_history(self, metrics_collector):
        """メトリクス履歴テスト"""
        # 初期状態は空
        history = metrics_collector.get_metrics_history()
        assert len(history) == 0
        
        # メトリクス記録
        metrics_collector.increment_counter("test_counter")
        metrics_collector.set_gauge("test_gauge", 10.0)
        
        # 履歴確認
        history = metrics_collector.get_metrics_history()
        assert len(history) == 2
        
        # 制限付き取得
        limited_history = metrics_collector.get_metrics_history(limit=1)
        assert len(limited_history) == 1
    
    def test_reset_metrics(self, metrics_collector):
        """メトリクスリセットテスト"""
        # メトリクス記録
        metrics_collector.increment_counter("counter", 10.0)
        metrics_collector.set_gauge("gauge", 20.0)
        metrics_collector.record_histogram("histogram", 5.0)
        
        # リセット前の確認
        assert metrics_collector.get_counter("counter") == 10.0
        assert metrics_collector.get_gauge("gauge") == 20.0
        
        # リセット
        metrics_collector.reset_metrics()
        
        # リセット後の確認
        assert metrics_collector.get_counter("counter") == 0.0
        assert metrics_collector.get_gauge("gauge") is None
        assert len(metrics_collector.get_metrics_history()) == 0
    
    def test_export_prometheus_format(self, metrics_collector):
        """Prometheus形式エクスポートテスト"""
        # メトリクス記録
        metrics_collector.increment_counter("http_requests_total", 100.0, {"method": "GET"})
        metrics_collector.set_gauge("cpu_usage_percent", 75.5, {"core": "0"})
        metrics_collector.record_histogram("response_time_seconds", 0.5)
        
        prometheus_output = metrics_collector.export_prometheus_format()
        
        assert "# TYPE http_requests_total counter" in prometheus_output
        assert 'http_requests_total{method="GET"} 100.0' in prometheus_output
        assert "# TYPE cpu_usage_percent gauge" in prometheus_output
        assert 'cpu_usage_percent{core="0"} 75.5' in prometheus_output
        assert "# TYPE response_time_seconds histogram" in prometheus_output
        assert "response_time_seconds_count 1" in prometheus_output
    
    def test_metric_key_parsing(self, metrics_collector):
        """メトリクスキーのパース機能テスト"""
        # ラベルなし
        name, labels = metrics_collector._parse_metric_key("simple_metric")
        assert name == "simple_metric"
        assert labels == {}
        
        # ラベルあり
        name, labels = metrics_collector._parse_metric_key("metric{key1=value1,key2=value2}")
        assert name == "metric"
        assert labels == {"key1": "value1", "key2": "value2"}
    
    def test_prometheus_labels_formatting(self, metrics_collector):
        """Prometheusラベル形式テスト"""
        # ラベルなし
        result = metrics_collector._format_prometheus_labels({})
        assert result == ""
        
        # ラベルあり
        result = metrics_collector._format_prometheus_labels({"method": "GET", "status": "200"})
        assert result == '{method="GET",status="200"}'
    
    def test_thread_safety(self, metrics_collector):
        """スレッドセーフティテスト"""
        import threading
        import time
        
        def increment_counter():
            for i in range(100):
                metrics_collector.increment_counter("thread_test")
        
        # 複数スレッドで同時実行
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 全ての増加が正しく記録されている
        assert metrics_collector.get_counter("thread_test") == 500.0


class TestWorkflowMetrics:
    """WorkflowMetricsクラスのテスト"""
    
    def test_record_workflow_started(self, workflow_metrics):
        """ワークフロー開始記録テスト"""
        workflow_metrics.record_workflow_started("workflow-001")
        
        count = workflow_metrics.metrics.get_counter(
            "workflow_started_total",
            {"workflow_id": "workflow-001"}
        )
        assert count == 1.0
    
    def test_record_workflow_completed(self, workflow_metrics):
        """ワークフロー完了記録テスト"""
        workflow_metrics.record_workflow_completed("workflow-001", 120.5)
        
        count = workflow_metrics.metrics.get_counter(
            "workflow_completed_total",
            {"workflow_id": "workflow-001"}
        )
        assert count == 1.0
        
        timer_stats = workflow_metrics.metrics.get_timer_stats(
            "workflow_duration_seconds",
            {"workflow_id": "workflow-001"}
        )
        assert timer_stats["count"] == 1
        assert timer_stats["avg"] == 120.5
    
    def test_record_workflow_failed(self, workflow_metrics):
        """ワークフロー失敗記録テスト"""
        workflow_metrics.record_workflow_failed("workflow-001", "timeout")
        
        count = workflow_metrics.metrics.get_counter(
            "workflow_failed_total",
            {"workflow_id": "workflow-001", "error_type": "timeout"}
        )
        assert count == 1.0
    
    def test_record_task_completed(self, workflow_metrics):
        """タスク完了記録テスト"""
        workflow_metrics.record_task_completed("workflow-001", "parse", 5.2)
        
        count = workflow_metrics.metrics.get_counter(
            "task_completed_total",
            {"workflow_id": "workflow-001", "task_type": "parse"}
        )
        assert count == 1.0
        
        timer_stats = workflow_metrics.metrics.get_timer_stats(
            "task_duration_seconds",
            {"workflow_id": "workflow-001", "task_type": "parse"}
        )
        assert timer_stats["avg"] == 5.2
    
    def test_record_task_failed(self, workflow_metrics):
        """タスク失敗記録テスト"""
        workflow_metrics.record_task_failed("workflow-001", "ai_generation", "api_error")
        
        count = workflow_metrics.metrics.get_counter(
            "task_failed_total",
            {
                "workflow_id": "workflow-001",
                "task_type": "ai_generation",
                "error_type": "api_error"
            }
        )
        assert count == 1.0
    
    def test_set_active_workflows(self, workflow_metrics):
        """アクティブワークフロー数設定テスト"""
        workflow_metrics.set_active_workflows(5)
        
        value = workflow_metrics.metrics.get_gauge("active_workflows")
        assert value == 5.0
    
    def test_set_queue_size(self, workflow_metrics):
        """キューサイズ設定テスト"""
        workflow_metrics.set_queue_size("event_queue", 42)
        
        value = workflow_metrics.metrics.get_gauge("queue_size", {"queue": "event_queue"})
        assert value == 42.0 