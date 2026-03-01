"""
Property-based tests for Continuous Learning

**Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
**Validates: Requirements 2.5, 3.5, 4.5**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import patch
import statistics

from src.agents.demand_forecast_agent import DemandForecastAgent


# Fixture for mocking AWS dependencies
@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        yield


# Property tests for continuous learning (Property 14)
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    accuracy_values=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=10,
        max_size=20
    )
)
def test_retraining_triggered_on_accuracy_degradation(mock_aws_dependencies, accuracy_values: List[float]):
    """
    Property: For any accuracy history showing degradation, retraining should be triggered
    
    **Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
    **Validates: Requirements 2.5**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Populate accuracy history
    for i, accuracy in enumerate(accuracy_values):
        agent.accuracy_history.append({
            'timestamp': (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
            'overall_accuracy': accuracy,
            'forecast_count': 10,
            'tracked_count': 10
        })
    
    # Check if retraining is triggered
    should_retrain = agent.check_retraining_trigger()
    
    # Calculate expected behavior
    if len(accuracy_values) >= 10:
        recent_avg = statistics.mean(accuracy_values[-5:])
        historical_avg = statistics.mean(accuracy_values[-10:-5])
        
        # Should trigger if accuracy degraded by more than 10% or falls below 75%
        expected_trigger = (
            (historical_avg > 0 and (historical_avg - recent_avg) / historical_avg > 0.1) or
            recent_avg < 0.75
        )
        
        assert should_retrain == expected_trigger, \
            f"Retraining trigger mismatch: got {should_retrain}, expected {expected_trigger}"
    else:
        # Not enough data, should not trigger
        assert not should_retrain


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    num_measurements=st.integers(min_value=0, max_value=20)
)
def test_performance_metrics_available(mock_aws_dependencies, num_measurements: int):
    """
    Property: For any accuracy history, performance metrics should be available
    
    **Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
    **Validates: Requirements 2.5**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Populate accuracy history with random data
    for i in range(num_measurements):
        agent.accuracy_history.append({
            'timestamp': (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
            'overall_accuracy': 0.85,
            'forecast_count': 10,
            'tracked_count': 8
        })
    
    # Get performance metrics
    metrics = agent.get_performance_metrics()
    
    # Verify metrics structure
    assert 'status' in metrics
    
    if num_measurements == 0:
        assert metrics['status'] == 'no_data'
    else:
        assert metrics['status'] in ['active', 'insufficient_data']
        
        if metrics['status'] == 'active':
            assert 'overall_accuracy' in metrics
            assert 'forecast_volume' in metrics
            assert 'retraining_recommended' in metrics
            assert 'last_updated' in metrics


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    sku=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    region=st.sampled_from(['north', 'south', 'east', 'west', 'central']),
    actual_demand=st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False)
)
def test_feedback_loop_stores_actual_demand(mock_aws_dependencies, sku: str, region: str, actual_demand: float):
    """
    Property: For any actual demand data, the feedback loop should store it for learning
    
    **Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
    **Validates: Requirements 2.5**
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository') as MockS3Repo:
        
        # Setup mock S3 repository
        mock_s3_repo = Mock()
        MockS3Repo.return_value = mock_s3_repo
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Update forecast accuracy with actual demand
        forecast_date = datetime.now(timezone.utc) + timedelta(days=1)
        result = agent.update_forecast_accuracy(sku, region, forecast_date, actual_demand)
        
        # Verify result structure
        assert 'sku' in result
        assert 'region' in result
        assert 'actual_demand' in result
        assert result['sku'] == sku
        assert result['region'] == region
        assert result['actual_demand'] == actual_demand
        
        # Verify S3 upload was called
        mock_s3_repo.upload_json.assert_called_once()


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    accuracy_history=st.lists(
        st.floats(min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=5,
        max_size=15
    )
)
def test_performance_metrics_calculate_correctly(mock_aws_dependencies, accuracy_history: List[float]):
    """
    Property: For any accuracy history, performance metrics should be calculated correctly
    
    **Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
    **Validates: Requirements 2.5**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Populate accuracy history
    for i, accuracy in enumerate(accuracy_history):
        agent.accuracy_history.append({
            'timestamp': (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
            'overall_accuracy': accuracy,
            'forecast_count': 10,
            'tracked_count': 10
        })
    
    # Get performance metrics
    metrics = agent.get_performance_metrics()
    
    if metrics['status'] == 'active':
        # Verify accuracy calculations
        expected_avg = statistics.mean(accuracy_history)
        expected_min = min(accuracy_history)
        expected_max = max(accuracy_history)
        
        assert abs(metrics['overall_accuracy']['average'] - expected_avg) < 0.01
        assert abs(metrics['overall_accuracy']['min'] - expected_min) < 0.01
        assert abs(metrics['overall_accuracy']['max'] - expected_max) < 0.01
        
        # Verify forecast volume calculations
        expected_total = len(accuracy_history) * 10
        expected_tracked = len(accuracy_history) * 10
        
        assert metrics['forecast_volume']['total_forecasts'] == expected_total
        assert metrics['forecast_volume']['tracked_forecasts'] == expected_tracked


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    stable_accuracy=st.floats(min_value=0.85, max_value=0.95, allow_nan=False, allow_infinity=False)
)
def test_no_retraining_for_stable_accuracy(mock_aws_dependencies, stable_accuracy: float):
    """
    Property: For stable high accuracy, retraining should not be triggered
    
    **Feature: retailmind-ai, Property 14: Continuous Learning and Improvement**
    **Validates: Requirements 2.5**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Populate accuracy history with stable high accuracy
    for i in range(15):
        agent.accuracy_history.append({
            'timestamp': (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
            'overall_accuracy': stable_accuracy,
            'forecast_count': 10,
            'tracked_count': 10
        })
    
    # Check if retraining is triggered
    should_retrain = agent.check_retraining_trigger()
    
    # Should not trigger for stable high accuracy
    assert not should_retrain, "Retraining should not be triggered for stable high accuracy"
