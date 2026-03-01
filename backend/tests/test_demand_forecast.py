"""
Property-based tests for Demand Forecast Agent

**Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
**Validates: Requirements 2.1, 2.2**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import patch
import statistics

from src.agents.demand_forecast_agent import (
    DemandForecastAgent,
    DemandForecastInput,
    HistoricalSalesData,
    DemandForecast
)


# Fixture for mocking AWS dependencies
@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        yield


# Custom strategies for generating test data
@st.composite
def historical_sales_strategy(draw):
    """Generate random HistoricalSalesData instances"""
    sku = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    sales_volume = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    price = draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    
    # Generate timestamp within last 90 days
    days_ago = draw(st.integers(min_value=0, max_value=90))
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    return HistoricalSalesData(
        sku=sku,
        region=region,
        sales_volume=sales_volume,
        timestamp=timestamp,
        price=price
    )


@st.composite
def demand_forecast_input_strategy(draw, min_sales=0, max_sales=50):
    """Generate random DemandForecastInput instances"""
    num_sales = draw(st.integers(min_value=min_sales, max_value=max_sales))
    
    historical_sales = [draw(historical_sales_strategy()) for _ in range(num_sales)]
    forecast_horizon_days = draw(st.integers(min_value=7, max_value=90))
    
    return DemandForecastInput(
        historical_sales=historical_sales,
        forecast_horizon_days=forecast_horizon_days
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_sku_level_forecasts_generated_for_all_skus(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any historical sales data, the agent should generate SKU-level forecasts for all SKUs
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    sku_forecasts = forecast_results['sku_forecasts']
    
    # Collect all unique SKU-region combinations from input that have at least 2 data points
    # (time-series forecasting requires at least 2 points)
    sku_region_counts = {}
    for s in input_data.historical_sales:
        key = (s.sku, s.region)
        sku_region_counts[key] = sku_region_counts.get(key, 0) + 1
    
    sku_region_pairs = set(k for k, v in sku_region_counts.items() if v >= 2)
    
    # Collect all SKU-region combinations from forecasts
    forecast_pairs = set((f.sku, f.region) for f in sku_forecasts)
    
    # Verify all SKU-region combinations with sufficient data have forecasts
    for sku, region in sku_region_pairs:
        assert (sku, region) in forecast_pairs, f"Missing forecast for SKU {sku} in region {region}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_forecasts_have_correct_horizon(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast horizon, the agent should generate forecasts for the specified number of days
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    sku_forecasts = forecast_results['sku_forecasts']
    
    if sku_forecasts:
        # Group forecasts by SKU-region
        sku_region_forecasts = {}
        for forecast in sku_forecasts:
            key = (forecast.sku, forecast.region)
            if key not in sku_region_forecasts:
                sku_region_forecasts[key] = []
            sku_region_forecasts[key].append(forecast)
        
        # Verify each SKU-region has forecasts for the full horizon
        for key, forecasts in sku_region_forecasts.items():
            assert len(forecasts) == input_data.forecast_horizon_days, \
                f"Expected {input_data.forecast_horizon_days} forecasts for {key}, got {len(forecasts)}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_region_wise_predictions_cover_all_regions(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any historical sales data, the agent should provide region-wise predictions for all regions
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract region forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    region_forecasts = forecast_results['region_forecasts']
    
    # Collect all unique regions from input
    regions = set(s.region for s in input_data.historical_sales)
    
    # Verify all regions have forecasts
    for region in regions:
        assert region in region_forecasts, f"Missing forecast for region {region}"
        
        # Verify each region has SKU-level predictions
        assert isinstance(region_forecasts[region], dict)
        assert len(region_forecasts[region]) > 0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_forecasts_have_confidence_intervals(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast, confidence intervals should be provided
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    sku_forecasts = forecast_results['sku_forecasts']
    
    # Verify all forecasts have confidence intervals
    for forecast in sku_forecasts:
        assert forecast.confidence_interval is not None
        assert isinstance(forecast.confidence_interval, tuple)
        assert len(forecast.confidence_interval) == 2
        
        lower, upper = forecast.confidence_interval
        
        # Verify confidence interval is valid
        assert lower >= 0.0, "Lower bound should be non-negative"
        assert upper >= lower, "Upper bound should be >= lower bound"
        assert lower <= forecast.predicted_demand <= upper, \
            "Predicted demand should be within confidence interval"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_forecast_dates_are_in_future(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast, forecast dates should be in the future relative to historical data
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    sku_forecasts = forecast_results['sku_forecasts']
    
    if sku_forecasts and input_data.historical_sales:
        # Group historical sales by SKU-region to find latest date for each
        sku_region_latest = {}
        for s in input_data.historical_sales:
            key = (s.sku, s.region)
            if key not in sku_region_latest or s.timestamp > sku_region_latest[key]:
                sku_region_latest[key] = s.timestamp
        
        # Verify all forecast dates are after the latest historical date for that SKU-region
        for forecast in sku_forecasts:
            key = (forecast.sku, forecast.region)
            if key in sku_region_latest:
                latest_historical = sku_region_latest[key]
                assert forecast.forecast_date > latest_historical, \
                    f"Forecast date {forecast.forecast_date} should be after latest historical date {latest_historical} for {key}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_predicted_demand_is_non_negative(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast, predicted demand should be non-negative
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    sku_forecasts = forecast_results['sku_forecasts']
    
    # Verify all predicted demands are non-negative
    for forecast in sku_forecasts:
        assert forecast.predicted_demand >= 0.0, \
            f"Predicted demand {forecast.predicted_demand} should be non-negative"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_decision_includes_accuracy_metrics(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast decision, accuracy metrics should be included
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1, 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract forecast results from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    
    # Verify accuracy metrics are present
    assert 'accuracy_metrics' in forecast_results
    accuracy_metrics = forecast_results['accuracy_metrics']
    
    assert 'overall_accuracy' in accuracy_metrics
    assert 'forecast_count' in accuracy_metrics
    assert 'tracked_count' in accuracy_metrics
    
    # Verify accuracy is within valid range
    assert 0.0 <= accuracy_metrics['overall_accuracy'] <= 1.0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_decision_confidence_based_on_accuracy(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any forecast, decision confidence should correlate with forecast accuracy
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1, 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract accuracy metrics
    forecast_results = decision.recommendation.supporting_data[0]
    accuracy_metrics = forecast_results['accuracy_metrics']
    
    # Verify confidence is within valid range
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    
    # If we have tracked accuracy data, confidence should reflect it
    if accuracy_metrics['tracked_count'] > 0:
        overall_accuracy = accuracy_metrics['overall_accuracy']
        # Confidence should not exceed accuracy for tracked forecasts
        assert decision.recommendation.confidence <= overall_accuracy * 1.2


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_decision_includes_all_required_metadata(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any demand forecast decision, all required metadata should be present
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1, 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify all required fields are present
    assert decision.agent_id == "demand-forecast-agent"
    assert decision.decision_id is not None
    assert decision.timestamp is not None
    assert isinstance(decision.timestamp, datetime)
    assert decision.recommendation is not None
    assert decision.recommendation.action == "demand_forecast_update"
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    assert decision.recommendation.reasoning is not None
    assert len(decision.recommendation.supporting_data) == 2  # forecast_results and recommendations
    
    # Verify forecast results structure
    forecast_results = decision.recommendation.supporting_data[0]
    assert 'sku_forecasts' in forecast_results
    assert 'region_forecasts' in forecast_results
    assert 'accuracy_metrics' in forecast_results
    
    # Verify recommendations
    recommendations = decision.recommendation.supporting_data[1]
    assert isinstance(recommendations, list)


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    historical_sales=st.lists(historical_sales_strategy(), min_size=5, max_size=20),
    sku=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    region=st.sampled_from(['north', 'south', 'east', 'west', 'central'])
)
def test_forecast_based_on_historical_average(mock_aws_dependencies, historical_sales: List[HistoricalSalesData], sku: str, region: str):
    """
    Property: For any SKU-region combination, forecast should be based on historical average
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1**
    """
    # Filter sales data to specific SKU and region
    filtered_sales = [s for s in historical_sales if s.sku == sku and s.region == region]
    
    # Skip if insufficient data
    assume(len(filtered_sales) >= 2)
    
    agent = DemandForecastAgent(register_with_council=False)
    
    # Generate forecasts
    forecasts = agent.generate_sku_forecasts(
        historical_sales=filtered_sales,
        forecast_horizon_days=30,
        sku_filter=sku
    )
    
    if forecasts:
        # Calculate expected average from historical data
        expected_avg = statistics.mean([s.sales_volume for s in filtered_sales])
        
        # Verify forecasts are based on historical average
        for forecast in forecasts:
            if forecast.sku == sku and forecast.region == region:
                # Forecast should be close to historical average
                # Allow some variance due to confidence intervals
                # For zero average, just check it's non-negative
                if expected_avg == 0.0:
                    assert forecast.predicted_demand >= 0.0
                else:
                    assert abs(forecast.predicted_demand - expected_avg) < expected_avg * 0.5, \
                        f"Forecast {forecast.predicted_demand} should be close to historical average {expected_avg}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=0, max_sales=0))
def test_agent_handles_empty_data_gracefully(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For empty historical data, the agent should handle it gracefully without errors
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.1, 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process empty input - should not raise exception
    decision = agent.process(input_data)
    
    # Verify decision is still valid
    assert decision is not None
    assert decision.recommendation is not None
    
    # Verify forecasts are empty
    forecast_results = decision.recommendation.supporting_data[0]
    assert len(forecast_results['sku_forecasts']) == 0
    assert len(forecast_results['region_forecasts']) == 0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=demand_forecast_input_strategy(min_sales=5, max_sales=50))
def test_region_forecasts_aggregate_correctly(mock_aws_dependencies, input_data: DemandForecastInput):
    """
    Property: For any historical sales data, region-wise forecasts should correctly aggregate SKU forecasts
    
    **Feature: retailmind-ai, Property 2: Demand Forecasting Accuracy**
    **Validates: Requirements 2.2**
    """
    agent = DemandForecastAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract region forecasts from supporting data
    forecast_results = decision.recommendation.supporting_data[0]
    region_forecasts = forecast_results['region_forecasts']
    
    # Verify region forecasts match input data structure
    for region, sku_forecasts in region_forecasts.items():
        # Get all SKUs for this region from input that have data
        region_sales = [s for s in input_data.historical_sales if s.region == region]
        region_skus = set(s.sku for s in region_sales)
        
        # Verify all SKUs in the region have forecasts
        for sku in region_skus:
            assert sku in sku_forecasts, f"Missing forecast for SKU {sku} in region {region}"
            
            # Verify forecast value is non-negative
            assert sku_forecasts[sku] >= 0.0, f"Forecast for SKU {sku} in region {region} should be non-negative"


# Integration tests
@pytest.mark.integration
def test_agent_registration_with_council():
    """
    Test that Demand Forecast Agent can register with AI Council
    
    Validates: Requirements 2.1, 6.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry') as MockRegistry, \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        # Setup mocks
        mock_registry_instance = Mock()
        MockRegistry.return_value = mock_registry_instance
        
        # Create agent without auto-registration
        agent = DemandForecastAgent(register_with_council=False)
        
        # Manually register
        agent.register()
        
        # Verify register_agent was called with correct metadata
        mock_registry_instance.register_agent.assert_called_once()
        call_args = mock_registry_instance.register_agent.call_args[0][0]
        assert call_args.agent_id == "demand-forecast-agent"
        assert call_args.agent_type == "demand_forecast"
        assert "sku_level_forecasting" in call_args.capabilities
        assert "region_wise_prediction" in call_args.capabilities
        assert "time_series_analysis" in call_args.capabilities
        assert "forecast_accuracy_tracking" in call_args.capabilities


@pytest.mark.integration
def test_agent_persists_forecast_data():
    """
    Test that Demand Forecast Agent persists data to DynamoDB and S3
    
    Validates: Requirements 2.1, 8.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.demand_forecast_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_bi_repo = Mock()
        mock_s3_repo = Mock()
        MockBIRepo.return_value = mock_bi_repo
        MockS3Repo.return_value = mock_s3_repo
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Create sample forecast results
        forecast_results = {
            'sku_forecasts': [
                DemandForecast(
                    sku='test-sku',
                    region='north',
                    forecast_date=datetime.now(timezone.utc) + timedelta(days=1),
                    predicted_demand=100.0,
                    confidence_interval=(80.0, 120.0)
                )
            ],
            'region_forecasts': {'north': {'test-sku': 3000.0}},
            'accuracy_metrics': {'overall_accuracy': 0.85, 'forecast_count': 1, 'tracked_count': 0}
        }
        
        # Persist forecasts
        agent.persist_forecasts(forecast_results, confidence=0.85)
        
        # Verify data was persisted to DynamoDB
        mock_bi_repo.create.assert_called_once()
        
        # Verify S3 upload was called
        mock_s3_repo.upload_json.assert_called_once()


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



# Unit tests for Demand Forecast Agent
@pytest.mark.unit
def test_forecast_generation_with_sample_data():
    """
    Unit test: Verify forecast generation with specific sample data
    
    Validates: Requirements 2.1, 2.2
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Create sample historical sales data
        historical_sales = [
            HistoricalSalesData(
                sku='laptop-001',
                region='north',
                sales_volume=100.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=10),
                price=1000.0
            ),
            HistoricalSalesData(
                sku='laptop-001',
                region='north',
                sales_volume=120.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                price=1000.0
            ),
            HistoricalSalesData(
                sku='laptop-001',
                region='north',
                sales_volume=110.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=1),
                price=1000.0
            )
        ]
        
        # Generate forecasts
        forecasts = agent.generate_sku_forecasts(
            historical_sales=historical_sales,
            forecast_horizon_days=7,
            sku_filter='laptop-001'
        )
        
        # Verify forecasts were generated
        assert len(forecasts) == 7  # 7 days of forecasts
        
        # Verify all forecasts are for the correct SKU and region
        for forecast in forecasts:
            assert forecast.sku == 'laptop-001'
            assert forecast.region == 'north'
            assert forecast.predicted_demand > 0
            assert forecast.confidence_interval is not None


@pytest.mark.unit
def test_region_wise_prediction_logic():
    """
    Unit test: Verify region-wise prediction logic with specific data
    
    Validates: Requirements 2.2
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Create sample historical sales data for multiple regions
        historical_sales = [
            HistoricalSalesData(
                sku='phone-001',
                region='north',
                sales_volume=50.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                price=500.0
            ),
            HistoricalSalesData(
                sku='phone-001',
                region='south',
                sales_volume=75.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                price=500.0
            ),
            HistoricalSalesData(
                sku='phone-002',
                region='north',
                sales_volume=30.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=5),
                price=300.0
            )
        ]
        
        # Generate region forecasts
        region_forecasts = agent.generate_region_forecasts(
            historical_sales=historical_sales,
            forecast_horizon_days=30
        )
        
        # Verify forecasts for both regions
        assert 'north' in region_forecasts
        assert 'south' in region_forecasts
        
        # Verify SKUs in each region
        assert 'phone-001' in region_forecasts['north']
        assert 'phone-002' in region_forecasts['north']
        assert 'phone-001' in region_forecasts['south']
        
        # Verify forecast values are reasonable (30 days * daily average)
        assert region_forecasts['north']['phone-001'] == 50.0 * 30
        assert region_forecasts['south']['phone-001'] == 75.0 * 30
        assert region_forecasts['north']['phone-002'] == 30.0 * 30


@pytest.mark.unit
def test_accuracy_calculation():
    """
    Unit test: Verify accuracy calculation logic
    
    Validates: Requirements 2.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Create sample forecasts with accuracy data
        forecasts = [
            DemandForecast(
                sku='test-sku-1',
                region='north',
                forecast_date=datetime.now(timezone.utc) + timedelta(days=1),
                predicted_demand=100.0,
                confidence_interval=(90.0, 110.0),
                accuracy=0.90
            ),
            DemandForecast(
                sku='test-sku-2',
                region='south',
                forecast_date=datetime.now(timezone.utc) + timedelta(days=1),
                predicted_demand=200.0,
                confidence_interval=(180.0, 220.0),
                accuracy=0.85
            ),
            DemandForecast(
                sku='test-sku-3',
                region='east',
                forecast_date=datetime.now(timezone.utc) + timedelta(days=1),
                predicted_demand=150.0,
                confidence_interval=(135.0, 165.0),
                accuracy=0.80
            )
        ]
        
        # Track accuracy
        accuracy_metrics = agent.track_forecast_accuracy(forecasts)
        
        # Verify accuracy metrics
        assert accuracy_metrics['forecast_count'] == 3
        assert accuracy_metrics['tracked_count'] == 3
        # All forecasts have accuracy >= 0.85, so 2 out of 3 are accurate
        assert accuracy_metrics['overall_accuracy'] == 2.0 / 3.0


@pytest.mark.unit
def test_empty_data_handling():
    """
    Unit test: Verify agent handles empty data gracefully
    
    Validates: Requirements 2.1, 2.2
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Test with empty historical sales
        forecasts = agent.generate_sku_forecasts(
            historical_sales=[],
            forecast_horizon_days=30
        )
        
        assert forecasts == []
        
        # Test with empty region forecasts
        region_forecasts = agent.generate_region_forecasts(
            historical_sales=[],
            forecast_horizon_days=30
        )
        
        assert region_forecasts == {}


@pytest.mark.unit
def test_confidence_interval_calculation():
    """
    Unit test: Verify confidence interval calculation
    
    Validates: Requirements 2.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        
        agent = DemandForecastAgent(register_with_council=False)
        
        # Create sample historical sales with known variance
        historical_sales = [
            HistoricalSalesData(
                sku='test-sku',
                region='north',
                sales_volume=100.0,
                timestamp=datetime.now(timezone.utc) - timedelta(days=i),
                price=500.0
            )
            for i in range(10, 0, -1)
        ]
        
        # Generate forecasts
        forecasts = agent.generate_sku_forecasts(
            historical_sales=historical_sales,
            forecast_horizon_days=1
        )
        
        assert len(forecasts) == 1
        forecast = forecasts[0]
        
        # Verify confidence interval structure
        assert forecast.confidence_interval is not None
        lower, upper = forecast.confidence_interval
        
        # Verify interval is valid
        assert lower >= 0
        assert upper >= lower
        assert lower <= forecast.predicted_demand <= upper
