"""
Error Handling Service for RetailMind AI
Provides comprehensive error categorization, routing, timeout, retry, and circuit breaker patterns
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Callable, List
from enum import Enum
import time
import uuid
from functools import wraps


class ErrorCategory(Enum):
    """Categories of errors in the system"""
    AGENT_COMMUNICATION = "agent_communication"
    WORKFLOW_EXECUTION = "workflow_execution"
    DATA_PROCESSING = "data_processing"
    AI_MODEL = "ai_model"
    EXTERNAL_SERVICE = "external_service"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecoveryStrategy(Enum):
    """Recovery strategies for different error types"""
    RETRY = "retry"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ROLLBACK = "rollback"
    IGNORE = "ignore"
    CIRCUIT_BREAK = "circuit_break"


@dataclass
class ErrorContext:
    """Context information for an error"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    timestamp: datetime
    component: str
    operation: str
    details: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    recovery_strategy: Optional[RecoveryStrategy] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'errorId': self.error_id,
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'operation': self.operation,
            'details': self.details,
            'stackTrace': self.stack_trace,
            'recoveryStrategy': self.recovery_strategy.value if self.recovery_strategy else None
        }


@dataclass
class RetryConfig:
    """Configuration for retry mechanism"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    backoff_multiplier: float = 2.0
    exponential_backoff: bool = True
    retryable_exceptions: List[type] = field(default_factory=lambda: [Exception])
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        if self.exponential_backoff:
            delay = self.initial_delay * (self.backoff_multiplier ** (attempt - 1))
        else:
            delay = self.initial_delay
        
        return min(delay, self.max_delay)


@dataclass
class CircuitBreakerState:
    """State of a circuit breaker"""
    name: str
    state: str = "closed"  # closed, open, half_open
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_state_change: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'state': self.state,
            'failureCount': self.failure_count,
            'successCount': self.success_count,
            'lastFailureTime': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'lastStateChange': self.last_state_change.isoformat()
        }


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for agent communication
    Prevents cascading failures by temporarily blocking calls to failing services
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 60.0,
        half_open_timeout: float = 30.0
    ):
        """
        Initialize circuit breaker
        
        Args:
            name: Name of the circuit breaker
            failure_threshold: Number of failures before opening circuit
            success_threshold: Number of successes in half-open before closing
            timeout: Time in seconds before attempting to close an open circuit
            half_open_timeout: Time in seconds for half-open state
        """
        self.state = CircuitBreakerState(name=name)
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.half_open_timeout = half_open_timeout
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function execution
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state.state == "open":
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.state.name}' is open"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.state.last_failure_time is None:
            return True
        
        time_since_failure = datetime.utcnow() - self.state.last_failure_time
        return time_since_failure.total_seconds() >= self.timeout
    
    def _transition_to_half_open(self):
        """Transition circuit to half-open state"""
        self.state.state = "half_open"
        self.state.success_count = 0
        self.state.last_state_change = datetime.utcnow()
    
    def _on_success(self):
        """Handle successful call"""
        if self.state.state == "half_open":
            self.state.success_count += 1
            if self.state.success_count >= self.success_threshold:
                self._close_circuit()
        elif self.state.state == "closed":
            # Reset failure count on success
            self.state.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.state.failure_count += 1
        self.state.last_failure_time = datetime.utcnow()
        
        if self.state.state == "half_open":
            self._open_circuit()
        elif self.state.state == "closed":
            if self.state.failure_count >= self.failure_threshold:
                self._open_circuit()
    
    def _open_circuit(self):
        """Open the circuit"""
        self.state.state = "open"
        self.state.last_state_change = datetime.utcnow()
    
    def _close_circuit(self):
        """Close the circuit"""
        self.state.state = "closed"
        self.state.failure_count = 0
        self.state.success_count = 0
        self.state.last_state_change = datetime.utcnow()
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self.state
    
    def reset(self):
        """Manually reset circuit breaker to closed state"""
        self._close_circuit()


class ErrorHandler:
    """
    Comprehensive error handling service
    Provides error categorization, routing, and recovery strategies
    """
    
    def __init__(self):
        """Initialize error handler"""
        self.error_log: List[ErrorContext] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_handlers: Dict[ErrorCategory, Callable] = {}
    
    def categorize_error(
        self,
        exception: Exception,
        component: str,
        operation: str
    ) -> ErrorContext:
        """
        Categorize an error and create error context
        
        Args:
            exception: The exception that occurred
            component: Component where error occurred
            operation: Operation being performed
            
        Returns:
            ErrorContext with categorized error information
        """
        # Determine category based on exception type and context
        category = self._determine_category(exception, component, operation)
        severity = self._determine_severity(category, exception)
        recovery_strategy = self._determine_recovery_strategy(category, severity)
        
        error_context = ErrorContext(
            error_id=str(uuid.uuid4()),
            category=category,
            severity=severity,
            message=str(exception),
            timestamp=datetime.utcnow(),
            component=component,
            operation=operation,
            details={
                'exception_type': type(exception).__name__,
                'exception_args': exception.args
            },
            stack_trace=None,  # Could be populated with traceback
            recovery_strategy=recovery_strategy
        )
        
        # Log the error
        self.error_log.append(error_context)
        
        return error_context
    
    def _determine_category(
        self,
        exception: Exception,
        component: str,
        operation: str
    ) -> ErrorCategory:
        """Determine error category based on exception and context"""
        exception_name = type(exception).__name__.lower()
        
        # Check for timeout errors
        if 'timeout' in exception_name or 'timeout' in str(exception).lower():
            return ErrorCategory.TIMEOUT
        
        # Check for agent communication errors
        if 'agent' in component.lower() or 'communication' in operation.lower():
            return ErrorCategory.AGENT_COMMUNICATION
        
        # Check for workflow errors
        if 'workflow' in component.lower() or 'workflow' in operation.lower():
            return ErrorCategory.WORKFLOW_EXECUTION
        
        # Check for data processing errors
        if 'data' in component.lower() or 'repository' in component.lower():
            return ErrorCategory.DATA_PROCESSING
        
        # Check for AI model errors
        if 'model' in component.lower() or 'forecast' in component.lower() or 'prediction' in operation.lower():
            return ErrorCategory.AI_MODEL
        
        # Check for validation errors
        if 'validation' in exception_name or 'invalid' in exception_name:
            return ErrorCategory.VALIDATION
        
        # Check for resource unavailability
        if 'unavailable' in exception_name or 'notfound' in exception_name:
            return ErrorCategory.RESOURCE_UNAVAILABLE
        
        return ErrorCategory.UNKNOWN
    
    def _determine_severity(
        self,
        category: ErrorCategory,
        exception: Exception
    ) -> ErrorSeverity:
        """Determine error severity"""
        # Critical errors
        if category in [ErrorCategory.WORKFLOW_EXECUTION, ErrorCategory.DATA_PROCESSING]:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category in [ErrorCategory.AI_MODEL, ErrorCategory.AGENT_COMMUNICATION]:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.RESOURCE_UNAVAILABLE]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors
        return ErrorSeverity.LOW
    
    def _determine_recovery_strategy(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity
    ) -> RecoveryStrategy:
        """Determine appropriate recovery strategy"""
        # Timeout and communication errors should be retried
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.AGENT_COMMUNICATION]:
            return RecoveryStrategy.RETRY
        
        # Workflow execution errors should be rolled back
        if category == ErrorCategory.WORKFLOW_EXECUTION:
            return RecoveryStrategy.ROLLBACK
        
        # AI model errors with low confidence should escalate
        if category == ErrorCategory.AI_MODEL:
            return RecoveryStrategy.ESCALATE
        
        # Resource unavailable should use circuit breaker
        if category == ErrorCategory.RESOURCE_UNAVAILABLE:
            return RecoveryStrategy.CIRCUIT_BREAK
        
        # Validation errors should escalate
        if category == ErrorCategory.VALIDATION:
            return RecoveryStrategy.ESCALATE
        
        # Default to retry
        return RecoveryStrategy.RETRY
    
    def handle_error(
        self,
        error_context: ErrorContext,
        fallback_handler: Optional[Callable] = None
    ) -> Any:
        """
        Handle error based on its category and recovery strategy
        
        Args:
            error_context: Error context information
            fallback_handler: Optional fallback handler function
            
        Returns:
            Result of error handling
        """
        # Check if there's a registered handler for this category
        if error_context.category in self.error_handlers:
            return self.error_handlers[error_context.category](error_context)
        
        # Use fallback handler if provided
        if fallback_handler:
            return fallback_handler(error_context)
        
        # Default handling based on recovery strategy
        if error_context.recovery_strategy == RecoveryStrategy.ESCALATE:
            return self._escalate_error(error_context)
        elif error_context.recovery_strategy == RecoveryStrategy.ROLLBACK:
            return self._rollback_error(error_context)
        
        return None
    
    def _escalate_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Escalate error to human oversight"""
        return {
            'action': 'escalate',
            'error_id': error_context.error_id,
            'message': f"Error escalated: {error_context.message}",
            'requires_human_intervention': True
        }
    
    def _rollback_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Initiate rollback for error"""
        return {
            'action': 'rollback',
            'error_id': error_context.error_id,
            'message': f"Initiating rollback for: {error_context.message}",
            'rollback_required': True
        }
    
    def register_handler(
        self,
        category: ErrorCategory,
        handler: Callable
    ):
        """
        Register a custom error handler for a category
        
        Args:
            category: Error category
            handler: Handler function
        """
        self.error_handlers[category] = handler
    
    def get_circuit_breaker(
        self,
        name: str,
        **kwargs
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker
        
        Args:
            name: Name of the circuit breaker
            **kwargs: Additional configuration for circuit breaker
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self.circuit_breakers:
            self.circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
        
        return self.circuit_breakers[name]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about errors
        
        Returns:
            Dictionary with error statistics
        """
        if not self.error_log:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {},
                'by_component': {}
            }
        
        stats = {
            'total_errors': len(self.error_log),
            'by_category': {},
            'by_severity': {},
            'by_component': {}
        }
        
        for error in self.error_log:
            # Count by category
            category_key = error.category.value
            stats['by_category'][category_key] = stats['by_category'].get(category_key, 0) + 1
            
            # Count by severity
            severity_key = error.severity.value
            stats['by_severity'][severity_key] = stats['by_severity'].get(severity_key, 0) + 1
            
            # Count by component
            stats['by_component'][error.component] = stats['by_component'].get(error.component, 0) + 1
        
        return stats


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to a function
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorated function with retry logic
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(config.retryable_exceptions) as e:
                    last_exception = e
                    
                    if attempt < config.max_attempts:
                        delay = config.get_delay(attempt)
                        time.sleep(delay)
                    else:
                        # Last attempt failed
                        raise
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to a function
    Note: This is a simplified version. For production, use threading or asyncio
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        Decorated function with timeout
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # This is a simplified implementation
            # In production, you would use threading.Timer or asyncio.wait_for
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            
            if elapsed > timeout_seconds:
                raise TimeoutError(f"Function {func.__name__} exceeded timeout of {timeout_seconds}s")
            
            return result
        
        return wrapper
    return decorator


class GracefulDegradation:
    """
    Provides graceful degradation logic for system failures
    """
    
    def __init__(self):
        """Initialize graceful degradation handler"""
        self.fallback_strategies: Dict[str, Callable] = {}
    
    def register_fallback(
        self,
        component: str,
        fallback_func: Callable
    ):
        """
        Register a fallback strategy for a component
        
        Args:
            component: Component name
            fallback_func: Fallback function to use
        """
        self.fallback_strategies[component] = fallback_func
    
    def execute_with_fallback(
        self,
        component: str,
        primary_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with fallback on failure
        
        Args:
            component: Component name
            primary_func: Primary function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Result from primary or fallback function
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            # Try fallback if available
            if component in self.fallback_strategies:
                fallback_func = self.fallback_strategies[component]
                return fallback_func(*args, **kwargs)
            else:
                # No fallback available, re-raise
                raise


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class TimeoutError(Exception):
    """Exception raised when operation times out"""
    pass
