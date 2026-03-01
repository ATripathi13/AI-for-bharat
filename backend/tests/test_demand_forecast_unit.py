"""
Unit tests for Demand Forecast Agent

Validates: Requirements 2.1, 2.2
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from src.agents.demand_forecast_agent import (
    DemandForecastAgent,
    HistoricalSalesData,
    DemandForecast
)


# Unit tests for Demand Forecast Agent
@pytest.mark.unit
def test_forecast_generation_with_sample_data():
    """
    Unit test: Verify forecast generation with specific sample data
    
    Validates: Requirements 2.1, 2.2
    """
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
