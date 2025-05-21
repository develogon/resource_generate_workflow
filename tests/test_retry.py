import pytest
import time
from unittest.mock import patch, MagicMock

from utils.retry import retry_on_exception, retry_on_result, exponential_backoff, circuit_breaker


class TestRetryMechanisms:
    """リトライメカニズムのテストクラス"""

    def test_retry_on_exception_success(self):
        """例外発生時のリトライ成功テスト"""
        # 最初の2回は例外を発生させ、3回目で成功する関数
        mock_func = MagicMock(side_effect=[ValueError("Error 1"), ValueError("Error 2"), "success"])
        
        # リトライデコレータを適用
        decorated_func = retry_on_exception(max_attempts=3, exceptions=(ValueError,))(mock_func)
        
        # スリープをモックしてリトライの待機をスキップ
        with patch('time.sleep') as mock_sleep:
            result = decorated_func("test_arg", kwarg="test_kwarg")
            
            # 結果の検証
            assert result == "success"
            
            # 関数が3回呼ばれたことを確認
            assert mock_func.call_count == 3
            
            # スリープが2回呼ばれたことを確認（3回目は成功したため、その後のスリープはない）
            assert mock_sleep.call_count == 2

    def test_retry_on_exception_max_attempts_reached(self):
        """例外発生時の最大試行回数到達テスト"""
        # 常に例外を発生させる関数
        mock_func = MagicMock(side_effect=ValueError("Persistent error"))
        
        # リトライデコレータを適用
        decorated_func = retry_on_exception(max_attempts=3, exceptions=(ValueError,))(mock_func)
        
        # スリープをモックしてリトライの待機をスキップ
        with patch('time.sleep') as mock_sleep:
            # 最大試行回数到達で例外が再発生することを確認
            with pytest.raises(ValueError) as excinfo:
                decorated_func()
            
            # 関数が3回呼ばれたことを確認
            assert mock_func.call_count == 3
            
            # スリープが2回呼ばれたことを確認（3回目の失敗後は再発生するため、スリープはない）
            assert mock_sleep.call_count == 2
            
            # 発生した例外が最後の例外であることを確認
            assert str(excinfo.value) == "Persistent error"

    def test_retry_on_exception_different_exception(self):
        """指定外の例外発生時のテスト"""
        # TypeError（指定外の例外）を発生させる関数
        mock_func = MagicMock(side_effect=TypeError("Type error"))
        
        # ValueError時のみリトライするデコレータを適用
        decorated_func = retry_on_exception(max_attempts=3, exceptions=(ValueError,))(mock_func)
        
        # 指定外の例外はそのまま発生することを確認
        with pytest.raises(TypeError) as excinfo:
            decorated_func()
        
        # 関数が1回だけ呼ばれたことを確認（リトライされない）
        assert mock_func.call_count == 1
        
        # 発生した例外が元の例外であることを確認
        assert str(excinfo.value) == "Type error"

    def test_retry_on_result_success(self):
        """結果検証失敗時のリトライ成功テスト"""
        # 最初の2回は検証失敗の結果を返し、3回目で成功結果を返す関数
        mock_func = MagicMock(side_effect=[{"status": "error"}, {"status": "error"}, {"status": "success"}])
        
        # 結果検証関数
        def validate_result(result):
            return result["status"] == "success"
        
        # リトライデコレータを適用
        decorated_func = retry_on_result(max_attempts=3, validate_result=validate_result)(mock_func)
        
        # スリープをモックしてリトライの待機をスキップ
        with patch('time.sleep') as mock_sleep:
            result = decorated_func()
            
            # 結果の検証
            assert result["status"] == "success"
            
            # 関数が3回呼ばれたことを確認
            assert mock_func.call_count == 3
            
            # スリープが2回呼ばれたことを確認
            assert mock_sleep.call_count == 2

    def test_retry_on_result_max_attempts_reached(self):
        """結果検証失敗時の最大試行回数到達テスト"""
        # 常に検証失敗の結果を返す関数
        mock_func = MagicMock(return_value={"status": "error"})
        
        # 結果検証関数
        def validate_result(result):
            return result["status"] == "success"
        
        # リトライデコレータを適用
        decorated_func = retry_on_result(max_attempts=3, validate_result=validate_result)(mock_func)
        
        # スリープをモックしてリトライの待機をスキップ
        with patch('time.sleep') as mock_sleep:
            # 最大試行回数到達で最後の結果が返されることを確認
            result = decorated_func()
            
            # 結果の検証
            assert result["status"] == "error"
            
            # 関数が3回呼ばれたことを確認
            assert mock_func.call_count == 3
            
            # スリープが2回呼ばれたことを確認
            assert mock_sleep.call_count == 2

    def test_exponential_backoff(self):
        """指数バックオフ計算のテスト"""
        # 初回の遅延（試行回数1、係数0.1）
        delay = exponential_backoff(1, 0.1)
        assert 0.1 <= delay < 0.2  # ジッターがあるので範囲で確認
        
        # 2回目の遅延（試行回数2、係数0.1）
        delay = exponential_backoff(2, 0.1)
        assert 0.2 <= delay < 0.4  # 0.1 * 2^1 = 0.2（ジッター付き）
        
        # 3回目の遅延（試行回数3、係数0.1）
        delay = exponential_backoff(3, 0.1)
        assert 0.4 <= delay < 0.8  # 0.1 * 2^2 = 0.4（ジッター付き）
        
        # 係数を変えた場合の遅延
        delay = exponential_backoff(2, 0.5)
        assert 1.0 <= delay < 2.0  # 0.5 * 2^1 = 1.0（ジッター付き）

    def test_circuit_breaker_closed(self):
        """回路遮断器の閉鎖状態テスト"""
        # 成功する関数
        success_func = MagicMock(return_value="success")
        
        # 回路遮断器デコレータを適用（閾値3）
        breaker = circuit_breaker(failure_threshold=3)
        decorated_func = breaker(success_func)
        
        # 関数呼び出し
        result = decorated_func()
        
        # 結果の検証
        assert result == "success"
        
        # 関数が1回呼ばれたことを確認
        assert success_func.call_count == 1
        
        # 回路の状態が閉じていることを確認
        assert breaker.failure_count == 0
        assert not breaker.is_open

    def test_circuit_breaker_open(self):
        """回路遮断器の開放状態テスト"""
        # 常に例外を発生させる関数
        failing_func = MagicMock(side_effect=ValueError("Error"))
        
        # 回路遮断器デコレータを適用（閾値3）
        breaker = circuit_breaker(failure_threshold=3)
        decorated_func = breaker(failing_func)
        
        # 最初の3回は例外が発生
        for _ in range(3):
            with pytest.raises(ValueError):
                decorated_func()
        
        # 4回目は回路が開いているため、CircuitBreakerOpenエラーが発生
        with pytest.raises(Exception) as excinfo:
            decorated_func()
        
        assert "Circuit breaker is open" in str(excinfo.value)
        
        # 関数が3回だけ呼ばれたことを確認（4回目は回路が開いているため呼ばれない）
        assert failing_func.call_count == 3
        
        # 回路の状態が開いていることを確認
        assert breaker.failure_count == 3
        assert breaker.is_open

    def test_circuit_breaker_half_open(self):
        """回路遮断器の半開状態テスト"""
        # 常に例外を発生させる関数
        failing_func = MagicMock(side_effect=ValueError("Error"))
        
        # 回路遮断器デコレータを適用（閾値2、リセット時間0秒）
        breaker = circuit_breaker(failure_threshold=2, reset_timeout=0)
        decorated_func = breaker(failing_func)
        
        # 最初の2回は例外が発生し、回路が開く
        for _ in range(2):
            with pytest.raises(ValueError):
                decorated_func()
        
        # 回路が開いていることを確認
        assert breaker.is_open
        
        # リセット時間を過ぎたことにする
        breaker.last_failure_time = 0
        
        # 次の呼び出しで回路が半開状態になり、関数が再度呼ばれて例外が発生
        with pytest.raises(ValueError):
            decorated_func()
        
        # 関数が3回呼ばれたことを確認
        assert failing_func.call_count == 3
        
        # 回路の状態が開いていることを確認（失敗したので再度開状態）
        assert breaker.is_open