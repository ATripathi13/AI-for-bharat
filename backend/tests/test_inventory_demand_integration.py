"""
Integration tests for Inventory Planning Agent and Demand Forecast Agent collaboration

Validates: Requirements 6.1, 6.2
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.agents.inventory_planning_agent import (
    InventoryPlanningAgent,
    InventoryLevel,
    DemandForecastData
)
from src.agents.demand_forecast_agent import DemandForecastAgent


@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'), \
         patch('src.agents.demand_forecast_agent.AgentRegistry'), \
         patch('src.agents.demand_forecast_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.demand_forecast_agent.S3Repository'):
        yield


@pytest.mark.integration
def test_inventory_agent_requests_demand_forecasts(mock_aws_dependencies):
    """
    Test that Inventory Planning Agent can request demand forecasts from Demand Forecast Agent
    
    Validates: Requirements 6.1, 6.2
    """
    # Create agents
    inventory_agent = InventoryPlanningAgent(register_with_council=False)
    
    # Mock the communication interface
    mock_response = {
        'status': 'success',
        'data': [
            {
                'insights': {
                    'prediction': {
                        'sku_forecasts': [
                            {
                                'sku': 'laptop-001',
                                'region': 'north',
                                'predicted_demand': 300.0
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    inventory_agent.communication.send_request = Mock(return_value=mock_response)
    
    # Request demand forecasts
    sku_region_pairs = [('laptop-001', 'north')]
    forecasts = inventory_agent.request_demand_forecasts(sku_region_pairs, 'test-correlation-id')
    
    # Verify request was sent
    inventory_agent.communication.send_request.assert_called_once()
    call_args = inventory_agent.communication.send_request.call_args
    
    assert call_args[1]['from_agent_id'] == 'inventory-planning-agent'
    assert call_args[1]['to_agent_id'] == 'demand-forecast-agent'
    assert call_args[1]['payload']['request_type'] == 'demand_forecast'
    
    # Verify forecasts were parsed
    assert len(forecasts) == 1
    assert forecasts[0].sku == 'laptop-001'
    assert forecasts[0].region == 'north'
    assert forecasts[0].predicted_demand == 300.0


@pytest.mark.integration
def test_inventory_agent_processes_with_demand_forecasts(mock_aws_dependencies):
    """
    Test that Inventory Planning Agent can process inventory with automatic forecast retrieval
    
    Validates: Requirements 6.1, 6.2
    """
    # Create inventory agent
    inventory_agent = InventoryPlanningAgent(register_with_council=False)
    
    # Mock the communication interface
    mock_response = {
        'status': 'success',
        'data': [
            {
                'insights': {
                    'prediction': {
                        'sku_forecasts': [
                            {
                                'sku': 'phone-001',
                                'region': 'south',
                                'predicted_demand': 600.0
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    inventory_agent.communication.send_request = Mock(return_value=mock_response)
    
    # Create inventory levels
    inventory_levels = [
        InventoryLevel(
            sku='phone-001',
            region='south',
            current_stock=100.0,
            reorder_point=200.0,
            max_stock=1000.0,
            timestamp=datetime.now(timezone.utc)
        )
    ]
    
    # Process with automatic forecast retrieval
    decision = inventory_agent.process_with_demand_forecasts(
        inventory_levels=inventory_levels,
        lead_time_days=7
    )
    
    # Verify decision was made
    assert decision is not None
    assert decision.agent_id == 'inventory-planning-agent'
    assert decision.recommendation is not None
    
    # Verify planning results include forecasts
    planning_results = decision.recommendation.supporting_data[0]
    assert 'stock_conditions' in planning_results
    assert 'optimization_recommendations' in planning_results
    
    # Verify request was sent to demand forecast agent
    inventory_agent.communication.send_request.assert_called_once()


@pytest.mark.integration
def test_collaborative_decision_making(mock_aws_dependencies):
    """
    Test collaborative decision-making between Inventory Planning and Demand Forecast agents
    
    Validates: Requirements 6.1, 6.2
    """
    # Create inventory agent
    inventory_agent = InventoryPlanningAgent(register_with_council=False)
    
    # Mock demand forecast response with high demand prediction
    mock_response = {
        'status': 'success',
        'data': [
            {
                'insights': {
                    'prediction': {
                        'sku_forecasts': [
                            {
                                'sku': 'tablet-001',
                                'region': 'east',
                                'predicted_demand': 900.0  # High demand
                            }
                        ]
                    }
                }
            }
        ]
    }
    
    inventory_agent.communication.send_request = Mock(return_value=mock_response)
    
    # Create inventory with low stock
    inventory_levels = [
        InventoryLevel(
            sku='tablet-001',
            region='east',
            current_stock=50.0,  # Low stock
            reorder_point=100.0,
            max_stock=1000.0,
            timestamp=datetime.now(timezone.utc)
        )
    ]
    
    # Process with forecast integration
    decision = inventory_agent.process_with_demand_forecasts(
        inventory_levels=inventory_levels,
        lead_time_days=7
    )
    
    # Verify stockout was detected due to high demand forecast
    planning_results = decision.recommendation.supporting_data[0]
    stock_conditions = planning_results['stock_conditions']
    
    assert len(stock_conditions) == 1
    assert stock_conditions[0].condition in ['stockout', 'approaching_stockout']
    
    # Verify reorder recommendation was made
    recommendations = planning_results['optimization_recommendations']
    assert len(recommendations) == 1
    assert recommendations[0].action_type == 'reorder'
    assert recommendations[0].reorder_quantity is not None
    assert recommendations[0].reorder_quantity > 0


@pytest.mark.unit
def test_demand_forecast_data_conversion():
    """
    Test conversion of demand forecast response to DemandForecastData objects
    
    Validates: Requirements 6.1, 6.2
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        
        inventory_agent = InventoryPlanningAgent(register_with_council=False)
        
        # Mock response with multiple forecasts
        mock_response = {
            'status': 'success',
            'data': [
                {
                    'insights': {
                        'prediction': {
                            'sku_forecasts': [
                                {
                                    'sku': 'product-a',
                                    'region': 'north',
                                    'predicted_demand': 100.0
                                },
                                {
                                    'sku': 'product-b',
                                    'region': 'south',
                                    'predicted_demand': 200.0
                                }
                            ]
                        }
                    }
                }
            ]
        }
        
        inventory_agent.communication.send_request = Mock(return_value=mock_response)
        
        # Request forecasts
        forecasts = inventory_agent.request_demand_forecasts(
            [('product-a', 'north'), ('product-b', 'south')],
            'test-id'
        )
        
        # Verify conversion
        assert len(forecasts) == 2
        assert forecasts[0].sku == 'product-a'
        assert forecasts[0].region == 'north'
        assert forecasts[0].predicted_demand == 100.0
        assert forecasts[1].sku == 'product-b'
        assert forecasts[1].region == 'south'
        assert forecasts[1].predicted_demand == 200.0
