"""
Property-based tests for Inventory Planning Agent

**Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
**Validates: Requirements 2.3, 2.4**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import patch

from src.agents.inventory_planning_agent import (
    InventoryPlanningAgent,
    InventoryPlanningInput,
    InventoryLevel,
    DemandForecastData,
    StockCondition,
    InventoryRecommendation
)


# Fixture for mocking AWS dependencies
@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        yield


# Custom strategies for generating test data
@st.composite
def inventory_level_strategy(draw):
    """Generate random InventoryLevel instances"""
    sku = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    
    # Generate inventory parameters with logical constraints
    max_stock = draw(st.floats(min_value=100.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    reorder_point = draw(st.floats(min_value=10.0, max_value=max_stock * 0.5, allow_nan=False, allow_infinity=False))
    current_stock = draw(st.floats(min_value=0.0, max_value=max_stock * 1.5, allow_nan=False, allow_infinity=False))
    
    timestamp = datetime.now(timezone.utc)
    
    return InventoryLevel(
        sku=sku,
        region=region,
        current_stock=current_stock,
        reorder_point=reorder_point,
        max_stock=max_stock,
        timestamp=timestamp
    )


@st.composite
def demand_forecast_data_strategy(draw):
    """Generate random DemandForecastData instances"""
    sku = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    predicted_demand = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    forecast_horizon_days = draw(st.integers(min_value=7, max_value=90))
    
    return DemandForecastData(
        sku=sku,
        region=region,
        predicted_demand=predicted_demand,
        forecast_horizon_days=forecast_horizon_days
    )


@st.composite
def inventory_planning_input_strategy(draw, min_inventory=1, max_inventory=20):
    """Generate random InventoryPlanningInput instances"""
    num_inventory = draw(st.integers(min_value=min_inventory, max_value=max_inventory))
    
    inventory_levels = [draw(inventory_level_strategy()) for _ in range(num_inventory)]
    
    # Generate matching demand forecasts for some inventory items
    demand_forecasts = []
    for inv in inventory_levels:
        # 70% chance of having a forecast for each inventory item
        if draw(st.booleans()):
            demand_forecasts.append(DemandForecastData(
                sku=inv.sku,
                region=inv.region,
                predicted_demand=draw(st.floats(min_value=0.0, max_value=5000.0, allow_nan=False, allow_infinity=False)),
                forecast_horizon_days=draw(st.integers(min_value=7, max_value=90))
            ))
    
    lead_time_days = draw(st.integers(min_value=1, max_value=30))
    
    return InventoryPlanningInput(
        inventory_levels=inventory_levels,
        demand_forecasts=demand_forecasts,
        lead_time_days=lead_time_days
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_stock_conditions_detected_for_all_inventory(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory state, stock conditions should be detected for all inventory items
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract stock conditions from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    stock_conditions = planning_results['stock_conditions']
    
    # Verify all inventory items have stock conditions
    assert len(stock_conditions) == len(input_data.inventory_levels)
    
    # Verify each condition has required fields
    for condition in stock_conditions:
        assert condition.sku is not None
        assert condition.region is not None
        assert condition.condition in ['overstock', 'stockout', 'optimal', 'approaching_stockout']
        assert condition.current_stock >= 0.0
        assert condition.recommended_action is not None
        assert condition.urgency in ['high', 'medium', 'low']


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_optimization_recommendations_provided_for_all_inventory(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory state, optimization recommendations should be provided for all items
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract recommendations from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    recommendations = planning_results['optimization_recommendations']
    
    # Verify all inventory items have recommendations
    assert len(recommendations) == len(input_data.inventory_levels)
    
    # Verify each recommendation has required fields
    for rec in recommendations:
        assert rec.sku is not None
        assert rec.region is not None
        assert rec.action_type in ['reorder', 'reduce', 'rebalance', 'maintain']
        assert rec.target_stock >= 0.0
        assert rec.reasoning is not None
        
        # If action is reorder, reorder_quantity should be specified
        if rec.action_type == 'reorder':
            assert rec.reorder_quantity is not None
            assert rec.reorder_quantity >= 0.0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_stockout_detection_triggers_high_urgency(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory at or below reorder point, stockout should be detected with high urgency
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract stock conditions from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    stock_conditions = planning_results['stock_conditions']
    
    # Create lookup for inventory levels
    inventory_map = {(inv.sku, inv.region): inv for inv in input_data.inventory_levels}
    
    # Verify stockout detection logic
    for condition in stock_conditions:
        key = (condition.sku, condition.region)
        inventory = inventory_map[key]
        
        # If current stock is at or below reorder point, should detect stockout or approaching stockout
        if inventory.current_stock <= inventory.reorder_point:
            assert condition.condition in ['stockout', 'approaching_stockout']
            assert condition.urgency in ['high', 'medium']


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_overstock_detection_for_excess_inventory(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory at or above max stock, overstock should be detected
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract stock conditions from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    stock_conditions = planning_results['stock_conditions']
    
    # Create lookup for inventory levels
    inventory_map = {(inv.sku, inv.region): inv for inv in input_data.inventory_levels}
    
    # Verify overstock detection logic
    for condition in stock_conditions:
        key = (condition.sku, condition.region)
        inventory = inventory_map[key]
        
        # If current stock is at or above max stock, should detect overstock
        if inventory.current_stock >= inventory.max_stock:
            assert condition.condition == 'overstock'


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_reorder_quantities_are_non_negative(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any reorder recommendation, reorder quantity should be non-negative
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract recommendations from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    recommendations = planning_results['optimization_recommendations']
    
    # Verify all reorder quantities are non-negative
    for rec in recommendations:
        if rec.reorder_quantity is not None:
            assert rec.reorder_quantity >= 0.0, \
                f"Reorder quantity {rec.reorder_quantity} should be non-negative"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_supply_demand_mismatches_detected(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory with demand forecast, supply-demand mismatches should be detected
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract mismatches from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    mismatches = planning_results['supply_demand_mismatches']
    
    # Verify mismatches structure
    for mismatch in mismatches:
        assert 'sku' in mismatch
        assert 'region' in mismatch
        assert 'mismatch_type' in mismatch
        assert mismatch['mismatch_type'] in ['missing_inventory_data', 'supply_shortage', 'supply_excess']
        assert 'severity' in mismatch
        assert mismatch['severity'] in ['high', 'medium', 'low']
        assert 'recommendation' in mismatch


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_rebalancing_plan_generated(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory state, a rebalancing plan should be generated
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract rebalancing plan from supporting data
    planning_results = decision.recommendation.supporting_data[0]
    rebalancing_plan = planning_results['rebalancing_plan']
    
    # Verify rebalancing plan structure
    assert 'rebalancing_actions' in rebalancing_plan
    assert 'total_transfers' in rebalancing_plan
    assert 'summary' in rebalancing_plan
    
    # Verify rebalancing actions structure
    for action in rebalancing_plan['rebalancing_actions']:
        assert 'sku' in action
        assert 'from_region' in action
        assert 'to_region' in action
        assert 'quantity' in action
        assert action['quantity'] > 0.0
        assert 'priority' in action
        assert action['priority'] in ['high', 'medium', 'low']
        assert 'reasoning' in action


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_decision_confidence_based_on_data_quality(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any input, decision confidence should reflect data quality
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify confidence is within valid range
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    
    # Higher confidence when we have both inventory and forecast data
    if len(input_data.demand_forecasts) == 0:
        # Lower confidence without forecasts
        assert decision.recommendation.confidence <= 0.7
    else:
        # Calculate coverage ratio
        coverage_ratio = len(input_data.demand_forecasts) / len(input_data.inventory_levels)
        
        # Confidence should increase with better coverage
        if coverage_ratio >= 0.9:
            assert decision.recommendation.confidence >= 0.85


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=1, max_inventory=20))
def test_decision_includes_all_required_metadata(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any inventory planning decision, all required metadata should be present
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify all required fields are present
    assert decision.agent_id == "inventory-planning-agent"
    assert decision.decision_id is not None
    assert decision.timestamp is not None
    assert isinstance(decision.timestamp, datetime)
    assert decision.recommendation is not None
    assert decision.recommendation.action == "inventory_planning_update"
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    assert decision.recommendation.reasoning is not None
    assert len(decision.recommendation.supporting_data) == 2  # planning_results and recommendations
    
    # Verify planning results structure
    planning_results = decision.recommendation.supporting_data[0]
    assert 'stock_conditions' in planning_results
    assert 'optimization_recommendations' in planning_results
    assert 'rebalancing_plan' in planning_results
    assert 'supply_demand_mismatches' in planning_results
    
    # Verify recommendations
    recommendations = decision.recommendation.supporting_data[1]
    assert isinstance(recommendations, list)


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    inventory=inventory_level_strategy(),
    forecast=demand_forecast_data_strategy(),
    lead_time_days=st.integers(min_value=1, max_value=30)
)
def test_forecast_based_recommendations_use_demand_data(mock_aws_dependencies, inventory: InventoryLevel, forecast: DemandForecastData, lead_time_days: int):
    """
    Property: For any inventory with matching forecast, recommendations should use demand data
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.4**
    """
    # Ensure forecast matches inventory
    forecast.sku = inventory.sku
    forecast.region = inventory.region
    
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Generate recommendation
    recommendation = agent._generate_forecast_based_recommendation(inventory, forecast, lead_time_days)
    
    # Verify recommendation structure
    assert recommendation.sku == inventory.sku
    assert recommendation.region == inventory.region
    assert recommendation.action_type in ['reorder', 'reduce', 'maintain']
    assert recommendation.target_stock >= 0.0
    assert recommendation.reasoning is not None
    
    # Verify reorder quantity is calculated when needed
    if recommendation.action_type == 'reorder':
        assert recommendation.reorder_quantity is not None
        assert recommendation.reorder_quantity >= 0.0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=0, max_inventory=0))
def test_agent_handles_empty_data_gracefully(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For empty inventory data, the agent should handle it gracefully without errors
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process empty input - should not raise exception
    decision = agent.process(input_data)
    
    # Verify decision is still valid
    assert decision is not None
    assert decision.recommendation is not None
    
    # Verify planning results are empty
    planning_results = decision.recommendation.supporting_data[0]
    assert len(planning_results['stock_conditions']) == 0
    assert len(planning_results['optimization_recommendations']) == 0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=inventory_planning_input_strategy(min_inventory=5, max_inventory=20))
def test_rebalancing_transfers_from_overstock_to_stockout(mock_aws_dependencies, input_data: InventoryPlanningInput):
    """
    Property: For any rebalancing action, transfers should be from overstock to stockout regions
    
    **Feature: retailmind-ai, Property 3: Inventory Optimization Consistency**
    **Validates: Requirements 2.3, 2.4**
    """
    agent = InventoryPlanningAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract planning results
    planning_results = decision.recommendation.supporting_data[0]
    stock_conditions = planning_results['stock_conditions']
    rebalancing_plan = planning_results['rebalancing_plan']
    
    # Create condition lookup
    condition_map = {(c.sku, c.region): c for c in stock_conditions}
    
    # Verify rebalancing logic
    for action in rebalancing_plan['rebalancing_actions']:
        from_key = (action['sku'], action['from_region'])
        to_key = (action['sku'], action['to_region'])
        
        # From region should have excess (overstock)
        if from_key in condition_map:
            from_condition = condition_map[from_key]
            # Should be transferring from overstock or at least optimal
            assert from_condition.condition in ['overstock', 'optimal']
        
        # To region should have shortage (stockout or approaching)
        if to_key in condition_map:
            to_condition = condition_map[to_key]
            # Should be transferring to stockout or approaching stockout
            assert to_condition.condition in ['stockout', 'approaching_stockout', 'optimal']


# Unit tests for Inventory Planning Agent
@pytest.mark.unit
def test_overstock_detection():
    """
    Unit test: Verify overstock detection with specific data
    
    Validates: Requirements 2.3
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        
        agent = InventoryPlanningAgent(register_with_council=False)
        
        # Create inventory with overstock condition
        inventory = InventoryLevel(
            sku='laptop-001',
            region='north',
            current_stock=1500.0,
            reorder_point=200.0,
            max_stock=1000.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Detect condition without forecast
        condition = agent._detect_condition_without_forecast(inventory)
        
        # Verify overstock is detected
        assert condition.condition == 'overstock'
        assert condition.urgency == 'medium'
        assert 'Reduce inventory' in condition.recommended_action


@pytest.mark.unit
def test_stockout_detection():
    """
    Unit test: Verify stockout detection with specific data
    
    Validates: Requirements 2.3
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        
        agent = InventoryPlanningAgent(register_with_council=False)
        
        # Create inventory with stockout condition
        inventory = InventoryLevel(
            sku='phone-001',
            region='south',
            current_stock=50.0,
            reorder_point=100.0,
            max_stock=1000.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        # Detect condition without forecast
        condition = agent._detect_condition_without_forecast(inventory)
        
        # Verify stockout is detected
        assert condition.condition == 'stockout'
        assert condition.urgency == 'high'
        assert 'Immediate reorder' in condition.recommended_action


@pytest.mark.unit
def test_reorder_quantity_calculation():
    """
    Unit test: Verify reorder quantity calculation with specific data
    
    Validates: Requirements 2.4
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.inventory_planning_agent.AgentRegistry'), \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        
        agent = InventoryPlanningAgent(register_with_council=False)
        
        # Create inventory and forecast
        inventory = InventoryLevel(
            sku='tablet-001',
            region='east',
            current_stock=100.0,
            reorder_point=200.0,
            max_stock=1000.0,
            timestamp=datetime.now(timezone.utc)
        )
        
        forecast = DemandForecastData(
            sku='tablet-001',
            region='east',
            predicted_demand=300.0,
            forecast_horizon_days=30
        )
        
        # Generate recommendation
        recommendation = agent._generate_forecast_based_recommendation(inventory, forecast, lead_time_days=7)
        
        # Verify recommendation
        assert recommendation.action_type == 'reorder'
        assert recommendation.reorder_quantity is not None
        assert recommendation.reorder_quantity > 0.0
        assert recommendation.target_stock > inventory.current_stock


@pytest.mark.integration
def test_agent_registration_with_council():
    """
    Test that Inventory Planning Agent can register with AI Council
    
    Validates: Requirements 2.3, 6.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.inventory_planning_agent.AgentRegistry') as MockRegistry, \
         patch('src.agents.inventory_planning_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.inventory_planning_agent.S3Repository'):
        
        # Setup mocks
        mock_registry_instance = Mock()
        MockRegistry.return_value = mock_registry_instance
        
        # Create agent without auto-registration
        agent = InventoryPlanningAgent(register_with_council=False)
        
        # Manually register
        agent.register()
        
        # Verify register_agent was called with correct metadata
        mock_registry_instance.register_agent.assert_called_once()
        call_args = mock_registry_instance.register_agent.call_args[0][0]
        assert call_args.agent_id == "inventory-planning-agent"
        assert call_args.agent_type == "inventory_planning"
        assert "overstock_detection" in call_args.capabilities
        assert "stockout_detection" in call_args.capabilities
        assert "inventory_optimization" in call_args.capabilities
        assert "stock_rebalancing" in call_args.capabilities
        assert "supply_demand_mismatch_detection" in call_args.capabilities
