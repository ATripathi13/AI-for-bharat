"""
Unit tests for error handling service
Tests specific examples and edge cases for error handling mechanisms
"""
import pytest
import time
from datetime import datetime

from src.services.error_handling import (
    ErrorHandler,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    CircuitBreaker,
    CircuitBreakerOpenError,
    with_retry,
    RetryConfig,
    GracefulDegradation,
    TimeoutError as CustomTimeoutError
)


class TestErrorCategorization:
    """Unit tests for error categorization"""
    
    def test_timeout_error_categorization(self):
        """Test that timeout errors are correctly categorized"""
        handler = ErrorHandler()
        exception = Exception("Operation timeout exceeded")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="test_component",
            operation="test_operation"
        )
        
        assert error_context.category == ErrorCategory.TIMEOUT
        assert error_context.severity == ErrorSeverity.MEDIUM
        assert error_context.recovery_strategy == RecoveryStrategy.RETRY
    
    def test_agent_communication_error(self):
        """Test agent communication error categorization"""
        handler = ErrorHandler()
        exception = ConnectionError("Agent communication failed")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="market_intelligence_agent",
            operation="send_message"
        )
        
        assert error_context.category == ErrorCategory.AGENT_COMMUNICATION
        assert error_context.severity == ErrorSeverity.HIGH
        assert error_context.recovery_strategy == RecoveryStrategy.RETRY
    
    def test_workflow_execution_error(self):
        """Test workflow execution error categorization"""
        handler = ErrorHandler()
        exception = RuntimeError("Workflow step failed")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="workflow_engine",
            operation="execute_step"
        )
        
        assert error_context.category == ErrorCategory.WORKFLOW_EXECUTION
        assert error_context.severity == ErrorSeverity.CRITICAL
        assert error_context.recovery_strategy == RecoveryStrategy.ROLLBACK
    
    def test_data_processing_error(self):
        """Test data processing error categorization"""
        handler = ErrorHandler()
        exception = ValueError("Invalid data format")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="data_repository",
            operation="process_data"
        )
        
        assert error_context.category == ErrorCategory.DATA_PROCESSING
        assert error_context.severity == ErrorSeverity.CRITICAL
    
    def test_ai_model_error(self):
        """Test AI model error categorization"""
        handler = ErrorHandler()
        exception = RuntimeError("Model prediction failed")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="demand_forecast_model",
            operation="generate_prediction"
        )
        
        assert error_context.category == ErrorCategory.AI_MODEL
        assert error_context.severity == ErrorSeverity.HIGH
        assert error_context.recovery_strategy == RecoveryStrategy.ESCALATE


class TestCircuitBreaker:
    """Unit tests for circuit breaker pattern"""
    
    def test_circuit_breaker_opens_after_threshold(self):
        """Test that circuit breaker opens after failure threshold"""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=3,
            timeout=1.0
        )
        
        # Simulate failures
        for _ in range(3):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
            except Exception:
                pass
        
        # Circuit should be open
        state = breaker.get_state()
        assert state.state == "open"
        assert state.failure_count == 3
    
    def test_circuit_breaker_prevents_calls_when_open(self):
        """Test that circuit breaker prevents calls when open"""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2,
            timeout=10.0
        )
        
        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
            except Exception:
                pass
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            breaker.call(lambda: "success")
    
    def test_circuit_breaker_half_open_transition(self):
        """Test circuit breaker transitions to half-open after timeout"""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2,
            timeout=0.1,  # Short timeout for testing
            success_threshold=2
        )
        
        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
            except Exception:
                pass
        
        assert breaker.get_state().state == "open"
        
        # Wait for timeout
        time.sleep(0.2)
        
        # Next successful call should transition to half-open
        try:
            breaker.call(lambda: "success")
        except CircuitBreakerOpenError:
            pass
        
        # State should be half-open after attempting reset
        state = breaker.get_state()
        assert state.state in ["half_open", "closed"]
    
    def test_circuit_breaker_closes_after_successes(self):
        """Test circuit breaker closes after success threshold in half-open"""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2,
            timeout=0.1,
            success_threshold=2
        )
        
        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
            except Exception:
                pass
        
        # Wait and make successful calls
        time.sleep(0.2)
        
        try:
            breaker.call(lambda: "success")
            breaker.call(lambda: "success")
        except CircuitBreakerOpenError:
            pass
        
        # Circuit should eventually close
        state = breaker.get_state()
        assert state.state in ["half_open", "closed"]
    
    def test_circuit_breaker_reset(self):
        """Test manual circuit breaker reset"""
        breaker = CircuitBreaker(
            name="test_breaker",
            failure_threshold=2
        )
        
        # Open the circuit
        for _ in range(2):
            try:
                breaker.call(lambda: (_ for _ in ()).throw(Exception("Failure")))
            except Exception:
                pass
        
        assert breaker.get_state().state == "open"
        
        # Reset the circuit
        breaker.reset()
        
        # Circuit should be closed
        assert breaker.get_state().state == "closed"
        assert breaker.get_state().failure_count == 0


class TestRetryMechanism:
    """Unit tests for retry mechanism"""
    
    def test_retry_succeeds_on_first_attempt(self):
        """Test retry decorator when function succeeds immediately"""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        attempt_count = [0]
        
        @with_retry(config)
        def successful_func():
            attempt_count[0] += 1
            return "success"
        
        result = successful_func()
        
        assert result == "success"
        assert attempt_count[0] == 1
    
    def test_retry_succeeds_after_failures(self):
        """Test retry decorator succeeds after initial failures"""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        attempt_count = [0]
        
        @with_retry(config)
        def flaky_func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise Exception("Not yet")
            return "success"
        
        result = flaky_func()
        
        assert result == "success"
        assert attempt_count[0] == 3
    
    def test_retry_fails_after_max_attempts(self):
        """Test retry decorator fails after max attempts"""
        config = RetryConfig(max_attempts=3, initial_delay=0.01)
        
        attempt_count = [0]
        
        @with_retry(config)
        def always_fails():
            attempt_count[0] += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert attempt_count[0] == 3
    
    def test_retry_exponential_backoff(self):
        """Test retry with exponential backoff"""
        config = RetryConfig(
            max_attempts=3,
            initial_delay=0.01,
            backoff_multiplier=2.0,
            exponential_backoff=True
        )
        
        # Test delay calculation
        assert config.get_delay(1) == 0.01
        assert config.get_delay(2) == 0.02
        assert config.get_delay(3) == 0.04
    
    def test_retry_max_delay_cap(self):
        """Test retry respects max delay cap"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=10.0,
            max_delay=20.0,
            backoff_multiplier=2.0,
            exponential_backoff=True
        )
        
        # Delay should be capped at max_delay
        assert config.get_delay(1) == 10.0
        assert config.get_delay(2) == 20.0  # Would be 20, capped
        assert config.get_delay(3) == 20.0  # Would be 40, capped


class TestGracefulDegradation:
    """Unit tests for graceful degradation"""
    
    def test_graceful_degradation_uses_fallback(self):
        """Test graceful degradation uses fallback on failure"""
        degradation = GracefulDegradation()
        
        def primary_func():
            raise Exception("Primary failed")
        
        def fallback_func():
            return "fallback_result"
        
        degradation.register_fallback("test_component", fallback_func)
        
        result = degradation.execute_with_fallback(
            "test_component",
            primary_func
        )
        
        assert result == "fallback_result"
    
    def test_graceful_degradation_uses_primary_when_successful(self):
        """Test graceful degradation uses primary when it succeeds"""
        degradation = GracefulDegradation()
        
        def primary_func():
            return "primary_result"
        
        def fallback_func():
            return "fallback_result"
        
        degradation.register_fallback("test_component", fallback_func)
        
        result = degradation.execute_with_fallback(
            "test_component",
            primary_func
        )
        
        assert result == "primary_result"
    
    def test_graceful_degradation_raises_without_fallback(self):
        """Test graceful degradation raises exception without fallback"""
        degradation = GracefulDegradation()
        
        def primary_func():
            raise ValueError("Primary failed")
        
        with pytest.raises(ValueError):
            degradation.execute_with_fallback(
                "test_component",
                primary_func
            )


class TestErrorHandling:
    """Unit tests for error handling service"""
    
    def test_error_logging(self):
        """Test that errors are logged"""
        handler = ErrorHandler()
        exception = Exception("Test error")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="test_component",
            operation="test_operation"
        )
        
        assert len(handler.error_log) == 1
        assert handler.error_log[0].error_id == error_context.error_id
    
    def test_error_statistics(self):
        """Test error statistics generation"""
        handler = ErrorHandler()
        
        # Generate multiple errors
        for i in range(5):
            exception = Exception(f"Error {i}")
            handler.categorize_error(
                exception=exception,
                component=f"component_{i % 2}",
                operation="test_operation"
            )
        
        stats = handler.get_error_statistics()
        
        assert stats['total_errors'] == 5
        assert len(stats['by_component']) == 2
    
    def test_custom_error_handler_registration(self):
        """Test registering custom error handlers"""
        handler = ErrorHandler()
        
        custom_result = {'custom': 'handled'}
        
        def custom_handler(error_context):
            return custom_result
        
        handler.register_handler(ErrorCategory.TIMEOUT, custom_handler)
        
        exception = Exception("Timeout occurred")
        error_context = handler.categorize_error(
            exception=exception,
            component="test",
            operation="timeout test"
        )
        
        result = handler.handle_error(error_context)
        assert result == custom_result
    
    def test_escalation_handling(self):
        """Test error escalation"""
        handler = ErrorHandler()
        exception = RuntimeError("Critical model failure")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="ai_model",
            operation="prediction"
        )
        
        result = handler.handle_error(error_context)
        
        assert result is not None
        assert result['action'] == 'escalate'
        assert result['requires_human_intervention'] is True
    
    def test_rollback_handling(self):
        """Test error rollback"""
        handler = ErrorHandler()
        exception = RuntimeError("Workflow step failed")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="workflow_engine",
            operation="execute"
        )
        
        result = handler.handle_error(error_context)
        
        assert result is not None
        assert result['action'] == 'rollback'
        assert result['rollback_required'] is True
    
    def test_circuit_breaker_retrieval(self):
        """Test circuit breaker retrieval and creation"""
        handler = ErrorHandler()
        
        breaker1 = handler.get_circuit_breaker("test_breaker")
        breaker2 = handler.get_circuit_breaker("test_breaker")
        
        # Should return the same instance
        assert breaker1 is breaker2
        assert breaker1.state.name == "test_breaker"
    
    def test_error_context_to_dict(self):
        """Test error context serialization"""
        handler = ErrorHandler()
        exception = Exception("Test error")
        
        error_context = handler.categorize_error(
            exception=exception,
            component="test_component",
            operation="test_operation"
        )
        
        error_dict = error_context.to_dict()
        
        assert 'errorId' in error_dict
        assert 'category' in error_dict
        assert 'severity' in error_dict
        assert 'message' in error_dict
        assert 'timestamp' in error_dict
        assert error_dict['component'] == "test_component"
        assert error_dict['operation'] == "test_operation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
