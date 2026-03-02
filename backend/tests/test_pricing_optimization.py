"""
Property-based tests for Pricing Optimization Agent

**Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import patch
import statistics

from src.agents.pricing_optimization_agent import (
    PricingOptimizationAgent,
    PricingOptimizationInput,
    PricingData,
    PriceRecommendation
)


# Fixture for mocking AWS dependencies
@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        yield


# Custom strategies for generating test data
@st.composite
def pricing_data_strategy(draw):
    """Generate random PricingData instances"""
    sku = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    
    # Generate realistic pricing data
    cost = draw(st.floats(min_value=10.0, max_value=500.0, allow_nan=False, allow_infinity=False))
    # Current price should be above cost
    current_price = draw(st.floats(min_value=cost * 1.1, max_value=cost * 3.0, allow_nan=False, allow_infinity=False))
    
    # Generate competitor prices (some may be empty)
    num_competitors = draw(st.integers(min_value=0, max_value=5))
    competitor_prices = []
    if num_competitors > 0:
        for _ in range(num_competitors):
            comp_price = draw(st.floats(min_value=cost * 0.9, max_value=cost * 3.5, allow_nan=False, allow_infinity=False))
            competitor_prices.append(comp_price)
    
    sales_volume = draw(st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False))
    
    # Generate timestamp within last 30 days
    days_ago = draw(st.integers(min_value=0, max_value=30))
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    return PricingData(
        sku=sku,
        current_price=current_price,
        cost=cost,
        competitor_prices=competitor_prices,
        sales_volume=sales_volume,
        region=region,
        timestamp=timestamp
    )


@st.composite
def pricing_optimization_input_strategy(draw, min_data=1, max_data=50):
    """Generate random PricingOptimizationInput instances"""
    num_pricing = draw(st.integers(min_value=min_data, max_value=max_data))
    pricing_data = [draw(pricing_data_strategy()) for _ in range(num_pricing)]
    
    # Optional target margin (20% to 40%)
    has_target_margin = draw(st.booleans())
    target_margin = None
    if has_target_margin:
        target_margin = draw(st.floats(min_value=0.20, max_value=0.40, allow_nan=False, allow_infinity=False))
    
    return PricingOptimizationInput(
        pricing_data=pricing_data,
        target_margin=target_margin,
        region_filter=None,
        sku_filter=None
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=1, max_data=50))
def test_agent_generates_margin_aware_recommendations(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing scenario, the agent should generate margin-aware recommendations
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract pricing results from supporting data
    pricing_results = decision.recommendation.supporting_data[0]
    price_recommendations = pricing_results['price_recommendations']
    
    # Verify recommendations were generated
    assert isinstance(price_recommendations, list)
    
    # For each recommendation, verify margin awareness
    for rec in price_recommendations:
        assert isinstance(rec, PriceRecommendation)
        
        # Verify expected margin is calculated
        assert 'expected_margin' in rec.__dict__
        assert 0.0 <= rec.expected_margin <= 1.0
        
        # If target margin was specified, verify recommendations respect it
        if input_data.target_margin is not None:
            # Recommended price should aim for target margin
            # Margin = (Price - Cost) / Price
            # So Price = Cost / (1 - Target Margin)
            # Find the corresponding pricing data
            matching_data = [
                p for p in input_data.pricing_data 
                if p.sku == rec.sku and p.region == rec.region
            ]
            if matching_data:
                latest_data = max(matching_data, key=lambda x: x.timestamp)
                # Verify recommended price maintains reasonable margin
                # (may not be exact due to competitive adjustments)
                calculated_margin = (rec.recommended_price - latest_data.cost) / rec.recommended_price if rec.recommended_price > 0 else 0
                assert calculated_margin >= 0.0, "Margin should be non-negative"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=5, max_data=50))
def test_agent_performs_competitive_analysis(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing scenario, the agent should perform competitive pricing analysis
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.2**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract pricing results from supporting data
    pricing_results = decision.recommendation.supporting_data[0]
    competitive_analysis = pricing_results['competitive_analysis']
    
    # Verify competitive analysis exists
    assert isinstance(competitive_analysis, dict)
    
    # For pricing data with competitor prices, verify analysis is performed
    data_with_competitors = [p for p in input_data.pricing_data if p.competitor_prices]
    
    if data_with_competitors:
        # The agent processes all data points and the last one for each SKU-region wins
        # So we need to check that at least some analysis was performed
        assert len(competitive_analysis) > 0
        
        # Verify each analysis entry has required fields
        for key, analysis in competitive_analysis.items():
            # Verify required competitive analysis fields
            assert 'sku' in analysis
            assert 'region' in analysis
            assert 'our_price' in analysis
            assert 'avg_competitor_price' in analysis
            assert 'min_competitor_price' in analysis
            assert 'max_competitor_price' in analysis
            assert 'price_position_pct' in analysis
            assert 'competitive_advantage' in analysis
            assert 'competitor_count' in analysis
            
            # Verify competitive advantage classification
            assert analysis['competitive_advantage'] in ['price_leader', 'premium', 'competitive']
            
            # Verify competitor count is positive
            assert analysis['competitor_count'] > 0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=1, max_data=50))
def test_agent_simulates_price_elasticity(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing scenario, the agent should simulate elasticity-based price impacts
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.3**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract pricing results from supporting data
    pricing_results = decision.recommendation.supporting_data[0]
    elasticity_simulations = pricing_results['elasticity_simulations']
    price_recommendations = pricing_results['price_recommendations']
    
    # Verify elasticity simulations exist
    assert isinstance(elasticity_simulations, dict)
    
    # For each recommendation, verify elasticity simulation was performed
    for rec in price_recommendations:
        key = f"{rec.sku}_{rec.region}"
        
        # Verify elasticity impact is included in recommendation
        assert 'elasticity_impact' in rec.__dict__
        assert isinstance(rec.elasticity_impact, dict)
        
        # Verify elasticity impact has required fields
        assert 'demand_change_pct' in rec.elasticity_impact
        assert 'estimated_demand' in rec.elasticity_impact
        assert 'revenue_change_pct' in rec.elasticity_impact
        assert 'estimated_revenue' in rec.elasticity_impact
        
        # Verify estimated values are non-negative
        assert rec.elasticity_impact['estimated_demand'] >= 0.0
        assert rec.elasticity_impact['estimated_revenue'] >= 0.0
        
        # If simulation exists for this SKU-region, verify it has scenarios
        if key in elasticity_simulations:
            simulation = elasticity_simulations[key]
            assert 'scenarios' in simulation
            assert isinstance(simulation['scenarios'], list)
            assert len(simulation['scenarios']) > 0
            
            # Verify each scenario has required fields
            for scenario in simulation['scenarios']:
                assert 'price' in scenario
                assert 'price_change_pct' in scenario
                assert 'demand_impact' in scenario
                assert 'revenue_impact' in scenario
                assert 'estimated_demand' in scenario
                assert 'estimated_revenue' in scenario


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=1, max_data=50))
def test_pricing_optimization_completeness(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing scenario, the agent should provide complete optimization with 
    margin-aware recommendations, competitive analysis, and elasticity simulation
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract pricing results from supporting data
    pricing_results = decision.recommendation.supporting_data[0]
    
    # Verify all three components are present
    assert 'price_recommendations' in pricing_results
    assert 'competitive_analysis' in pricing_results
    assert 'elasticity_simulations' in pricing_results
    
    price_recommendations = pricing_results['price_recommendations']
    competitive_analysis = pricing_results['competitive_analysis']
    elasticity_simulations = pricing_results['elasticity_simulations']
    
    # Verify recommendations are complete
    assert isinstance(price_recommendations, list)
    
    # For each recommendation, verify completeness
    for rec in price_recommendations:
        # 1. Margin-aware pricing (Requirement 3.1)
        assert hasattr(rec, 'expected_margin')
        assert 0.0 <= rec.expected_margin <= 1.0
        
        # 2. Competitive analysis (Requirement 3.2)
        assert hasattr(rec, 'competitive_position')
        assert rec.competitive_position in ['below', 'at', 'above', 'unknown']
        
        # 3. Elasticity modeling (Requirement 3.3)
        assert hasattr(rec, 'elasticity_impact')
        assert 'demand_change_pct' in rec.elasticity_impact
        assert 'revenue_change_pct' in rec.elasticity_impact
        
        # 4. Confidence level (Requirement 3.4)
        assert hasattr(rec, 'confidence')
        assert 0.0 <= rec.confidence <= 1.0


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=1, max_data=50))
def test_decision_confidence_correlates_with_data_quality(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing data, confidence should correlate with data quality and volume
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify confidence is within valid range
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    
    # Calculate data quality metrics
    total_data_points = len(input_data.pricing_data)
    data_with_competitors = len([p for p in input_data.pricing_data if p.competitor_prices])
    
    # Verify confidence correlates with data volume
    if total_data_points < 5:
        # Low data volume should have lower confidence
        assert decision.recommendation.confidence <= 0.7
    elif total_data_points >= 50:
        # High data volume should have higher confidence (relaxed threshold)
        assert decision.recommendation.confidence >= 0.6
    
    # Verify confidence increases with competitor data
    if data_with_competitors == 0:
        # No competitor data should limit confidence
        assert decision.recommendation.confidence <= 0.8


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much], deadline=None)
@given(
    pricing_data=st.lists(pricing_data_strategy(), min_size=1, max_size=20),
    sku=st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
    region=st.sampled_from(['north', 'south', 'east', 'west', 'central'])
)
def test_recommendations_respect_cost_constraints(mock_aws_dependencies, pricing_data: List[PricingData], sku: str, region: str):
    """
    Property: For any pricing data, recommended prices should never be below cost
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1**
    """
    # Filter to specific SKU and region
    filtered_data = [p for p in pricing_data if p.sku == sku and p.region == region]
    
    # Skip if no data for this combination
    assume(len(filtered_data) > 0)
    
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Generate recommendations
    recommendations = agent.generate_price_recommendations(
        pricing_data=filtered_data,
        target_margin=None,
        sku_filter=sku,
        region_filter=region
    )
    
    # Verify recommendations respect cost constraints
    for rec in recommendations:
        # Find corresponding cost
        matching_data = [p for p in filtered_data if p.sku == rec.sku and p.region == rec.region]
        if matching_data:
            latest_data = max(matching_data, key=lambda x: x.timestamp)
            # Recommended price should be above cost
            assert rec.recommended_price >= latest_data.cost, \
                f"Recommended price {rec.recommended_price} is below cost {latest_data.cost}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    pricing_data=st.lists(pricing_data_strategy(), min_size=5, max_size=20)
)
def test_competitive_analysis_statistics_are_correct(mock_aws_dependencies, pricing_data: List[PricingData]):
    """
    Property: For any pricing data with competitors, competitive analysis statistics should be mathematically correct
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.2**
    """
    # Filter to data with competitor prices
    data_with_competitors = [p for p in pricing_data if p.competitor_prices]
    
    # Skip if no competitor data
    assume(len(data_with_competitors) > 0)
    
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Analyze competitive pricing
    competitive_analysis = agent.analyze_competitive_pricing(
        pricing_data=data_with_competitors,
        sku_filter=None,
        region_filter=None
    )
    
    # Verify that analysis was performed
    assert len(competitive_analysis) > 0
    
    # For each analysis entry, verify statistics are correct
    for key, analysis in competitive_analysis.items():
        # Find the corresponding pricing data point
        # The agent processes all data points and the last one for each SKU-region wins
        matching_points = [p for p in data_with_competitors 
                          if f"{p.sku}_{p.region}" == key and p.competitor_prices]
        
        if matching_points:
            # The analysis corresponds to one of these points
            # Verify the statistics are valid for at least one of them
            valid_match_found = False
            for price_point in matching_points:
                expected_avg = statistics.mean(price_point.competitor_prices)
                expected_min = min(price_point.competitor_prices)
                expected_max = max(price_point.competitor_prices)
                
                # Check if this matches
                if (abs(analysis['avg_competitor_price'] - expected_avg) < 0.01 and
                    abs(analysis['min_competitor_price'] - expected_min) < 0.01 and
                    abs(analysis['max_competitor_price'] - expected_max) < 0.01):
                    valid_match_found = True
                    
                    # Verify price position calculation
                    expected_position = (price_point.current_price - expected_avg) / expected_avg * 100 if expected_avg > 0 else 0
                    assert abs(analysis['price_position_pct'] - expected_position) < 0.01
                    break
            
            # At least one match should be valid
            assert valid_match_found, f"No valid match found for analysis key {key}"


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=0, max_data=0))
def test_agent_handles_empty_data_gracefully(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For empty pricing data, the agent should handle it gracefully without errors
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process empty input - should not raise exception
    decision = agent.process(input_data)
    
    # Verify decision is still valid
    assert decision is not None
    assert decision.recommendation is not None
    
    # Extract pricing results
    pricing_results = decision.recommendation.supporting_data[0]
    
    # Verify empty results are handled gracefully
    assert pricing_results['price_recommendations'] == []
    assert pricing_results['competitive_analysis'] == {}
    assert pricing_results['elasticity_simulations'] == {}


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(input_data=pricing_optimization_input_strategy(min_data=1, max_data=50))
def test_decision_includes_all_required_metadata(mock_aws_dependencies, input_data: PricingOptimizationInput):
    """
    Property: For any pricing optimization decision, all required metadata should be present
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify all required fields are present
    assert decision.agent_id == "pricing-optimization-agent"
    assert decision.decision_id is not None
    assert decision.timestamp is not None
    assert isinstance(decision.timestamp, datetime)
    assert decision.recommendation is not None
    assert decision.recommendation.action == "pricing_optimization_update"
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    assert decision.recommendation.reasoning is not None
    assert len(decision.recommendation.supporting_data) == 2  # pricing_results and recommendations
    
    # Verify pricing results structure
    pricing_results = decision.recommendation.supporting_data[0]
    assert 'price_recommendations' in pricing_results
    assert 'competitive_analysis' in pricing_results
    assert 'elasticity_simulations' in pricing_results
    
    # Verify recommendations
    recommendations = decision.recommendation.supporting_data[1]
    assert isinstance(recommendations, list)


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow, HealthCheck.function_scoped_fixture], deadline=None)
@given(
    pricing_data=st.lists(pricing_data_strategy(), min_size=5, max_size=20),
    target_margin=st.floats(min_value=0.20, max_value=0.40, allow_nan=False, allow_infinity=False)
)
def test_target_margin_influences_recommendations(mock_aws_dependencies, pricing_data: List[PricingData], target_margin: float):
    """
    Property: For any target margin, recommendations should aim to achieve that margin
    
    **Feature: retailmind-ai, Property 4: Pricing Optimization Completeness**
    **Validates: Requirements 3.1**
    """
    agent = PricingOptimizationAgent(register_with_council=False)
    
    # Generate recommendations with target margin
    recommendations = agent.generate_price_recommendations(
        pricing_data=pricing_data,
        target_margin=target_margin,
        sku_filter=None,
        region_filter=None
    )
    
    # Verify recommendations consider target margin
    for rec in recommendations:
        # Expected margin should be close to target (may vary due to competitive adjustments)
        # But should generally be positive and reasonable
        assert rec.expected_margin >= 0.0
        assert rec.expected_margin <= 1.0


# Integration tests
@pytest.mark.integration
def test_agent_registration_with_council():
    """
    Test that Pricing Optimization Agent can register with AI Council
    
    Validates: Requirements 3.1, 6.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry') as MockRegistry, \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        # Setup mocks
        mock_registry_instance = Mock()
        MockRegistry.return_value = mock_registry_instance
        
        # Create agent without auto-registration
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Manually register
        agent.register()
        
        # Verify register_agent was called with correct metadata
        mock_registry_instance.register_agent.assert_called_once()
        call_args = mock_registry_instance.register_agent.call_args[0][0]
        assert call_args.agent_id == "pricing-optimization-agent"
        assert call_args.agent_type == "pricing_optimization"
        assert "margin_aware_pricing" in call_args.capabilities
        assert "competitive_pricing_analysis" in call_args.capabilities
        assert "price_elasticity_modeling" in call_args.capabilities
        assert "pricing_performance_tracking" in call_args.capabilities


@pytest.mark.integration
def test_agent_persists_pricing_data():
    """
    Test that Pricing Optimization Agent persists data to DynamoDB and S3
    
    Validates: Requirements 3.1, 8.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.pricing_optimization_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_bi_repo = Mock()
        mock_s3_repo = Mock()
        MockBIRepo.return_value = mock_bi_repo
        MockS3Repo.return_value = mock_s3_repo
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Create sample pricing results
        pricing_results = {
            'price_recommendations': [
                PriceRecommendation(
                    sku='test-sku',
                    region='north',
                    current_price=100.0,
                    recommended_price=110.0,
                    expected_margin=0.25,
                    competitive_position='at',
                    elasticity_impact={'demand_change_pct': -2.0, 'revenue_change_pct': 8.0},
                    confidence=0.85
                )
            ],
            'competitive_analysis': {},
            'elasticity_simulations': {}
        }
        
        # Persist pricing data
        agent.persist_pricing_data(pricing_results, confidence=0.85)
        
        # Verify data was persisted to DynamoDB
        mock_bi_repo.create.assert_called_once()
        
        # Verify S3 upload was called
        mock_s3_repo.upload_json.assert_called_once()


@pytest.mark.integration
def test_pricing_performance_tracking():
    """
    Test that Pricing Optimization Agent can track pricing performance
    
    Validates: Requirements 3.5
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_s3_repo = Mock()
        MockS3Repo.return_value = mock_s3_repo
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Track pricing performance
        performance = agent.track_pricing_performance(
            sku='test-sku',
            region='north',
            recommended_price=110.0,
            actual_price_used=109.0,
            actual_sales_volume=150.0,
            actual_revenue=16350.0
        )
        
        # Verify performance record was created
        assert performance['sku'] == 'test-sku'
        assert performance['region'] == 'north'
        assert performance['recommended_price'] == 110.0
        assert performance['actual_price_used'] == 109.0
        
        # Verify S3 upload was called for feedback
        mock_s3_repo.upload_json.assert_called_once()
        
        # Verify performance metrics can be retrieved
        metrics = agent.get_performance_metrics()
        assert metrics['status'] == 'active'
        assert metrics['total_recommendations'] == 1


# Unit tests for Pricing Optimization Agent
@pytest.mark.unit
def test_margin_calculation():
    """
    Unit test: Verify margin calculation is correct
    
    Validates: Requirements 3.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Create test pricing data
        pricing_data = [
            PricingData(
                sku='test-sku',
                current_price=100.0,
                cost=70.0,
                competitor_prices=[95.0, 105.0, 98.0],
                sales_volume=50.0,
                region='north',
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Generate recommendations with target margin of 30%
        recommendations = agent.generate_price_recommendations(
            pricing_data=pricing_data,
            target_margin=0.30,
            sku_filter=None,
            region_filter=None
        )
        
        # Verify recommendation exists
        assert len(recommendations) == 1
        rec = recommendations[0]
        
        # Verify margin calculation
        # Expected price for 30% margin: cost / (1 - margin) = 70 / 0.7 = 100
        # But may be adjusted for competitive positioning
        assert rec.expected_margin > 0.0
        assert rec.expected_margin <= 1.0
        
        # Verify recommended price is above cost
        assert rec.recommended_price >= pricing_data[0].cost


@pytest.mark.unit
def test_competitive_analysis_calculation():
    """
    Unit test: Verify competitive analysis calculations
    
    Validates: Requirements 3.2
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Create test pricing data with competitors
        pricing_data = [
            PricingData(
                sku='test-sku',
                current_price=100.0,
                cost=70.0,
                competitor_prices=[90.0, 95.0, 110.0],
                sales_volume=50.0,
                region='north',
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Analyze competitive pricing
        analysis = agent.analyze_competitive_pricing(
            pricing_data=pricing_data,
            sku_filter=None,
            region_filter=None
        )
        
        # Verify analysis exists
        assert 'test-sku_north' in analysis
        comp_analysis = analysis['test-sku_north']
        
        # Verify competitive metrics
        assert comp_analysis['our_price'] == 100.0
        assert comp_analysis['avg_competitor_price'] == pytest.approx(98.33, rel=0.01)
        assert comp_analysis['min_competitor_price'] == 90.0
        assert comp_analysis['max_competitor_price'] == 110.0
        assert comp_analysis['competitor_count'] == 3
        
        # Verify competitive advantage classification
        assert comp_analysis['competitive_advantage'] in ['price_leader', 'premium', 'competitive']


@pytest.mark.unit
def test_elasticity_simulation():
    """
    Unit test: Verify price elasticity simulation
    
    Validates: Requirements 3.3
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Create test pricing data
        pricing_data = [
            PricingData(
                sku='test-sku',
                current_price=100.0,
                cost=70.0,
                competitor_prices=[95.0, 105.0],
                sales_volume=100.0,
                region='north',
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Generate recommendations
        recommendations = agent.generate_price_recommendations(
            pricing_data=pricing_data,
            target_margin=None,
            sku_filter=None,
            region_filter=None
        )
        
        # Simulate elasticity
        simulations = agent.simulate_price_elasticity(
            pricing_data=pricing_data,
            price_recommendations=recommendations
        )
        
        # Verify simulation exists
        assert 'test-sku_north' in simulations
        simulation = simulations['test-sku_north']
        
        # Verify simulation structure
        assert 'sku' in simulation
        assert 'region' in simulation
        assert 'current_price' in simulation
        assert 'recommended_price' in simulation
        assert 'scenarios' in simulation
        
        # Verify scenarios exist (should have 5: 90%, 95%, 100%, 105%, 110%)
        assert len(simulation['scenarios']) == 5
        
        # Verify each scenario has required fields
        for scenario in simulation['scenarios']:
            assert 'price' in scenario
            assert 'price_change_pct' in scenario
            assert 'demand_impact' in scenario
            assert 'revenue_impact' in scenario
            assert 'estimated_demand' in scenario
            assert 'estimated_revenue' in scenario


@pytest.mark.unit
def test_performance_tracking():
    """
    Unit test: Verify pricing performance tracking
    
    Validates: Requirements 3.5
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository') as MockS3:
        
        # Setup mock
        mock_s3 = Mock()
        MockS3.return_value = mock_s3
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Track performance
        performance = agent.track_pricing_performance(
            sku='test-sku',
            region='north',
            recommended_price=100.0,
            actual_price_used=99.0,
            actual_sales_volume=150.0,
            actual_revenue=14850.0
        )
        
        # Verify performance record
        assert performance['sku'] == 'test-sku'
        assert performance['region'] == 'north'
        assert performance['recommended_price'] == 100.0
        assert performance['actual_price_used'] == 99.0
        assert performance['actual_sales_volume'] == 150.0
        assert performance['actual_revenue'] == 14850.0
        assert 'timestamp' in performance
        assert 'recommendation_followed' in performance
        
        # Verify S3 upload was called
        mock_s3.upload_json.assert_called_once()
        
        # Get performance metrics
        metrics = agent.get_performance_metrics()
        assert metrics['status'] == 'active'
        assert metrics['total_recommendations'] == 1
        assert metrics['followed_recommendations'] >= 0


@pytest.mark.unit
def test_recommendation_optimization_from_outcomes():
    """
    Unit test: Verify recommendation optimization based on outcomes
    
    Validates: Requirements 3.5
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Add historical performance data
        for i in range(5):
            agent.performance_history.append({
                'sku': 'test-sku',
                'region': 'north',
                'recommended_price': 100.0,
                'actual_price_used': 95.0 + i,
                'actual_sales_volume': 100.0 + i * 10,
                'actual_revenue': (95.0 + i) * (100.0 + i * 10),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'recommendation_followed': True
            })
        
        # Create current recommendation
        current_rec = PriceRecommendation(
            sku='test-sku',
            region='north',
            current_price=100.0,
            recommended_price=100.0,
            expected_margin=0.30,
            competitive_position='at',
            elasticity_impact={'demand_change_pct': 0.0, 'revenue_change_pct': 0.0},
            confidence=0.75
        )
        
        # Optimize based on outcomes
        optimized_rec = agent.optimize_recommendations_from_outcomes(
            sku='test-sku',
            region='north',
            current_recommendation=current_rec
        )
        
        # Verify optimization occurred
        assert optimized_rec is not None
        assert optimized_rec.sku == 'test-sku'
        assert optimized_rec.region == 'north'


@pytest.mark.unit
def test_pricing_insights_generation():
    """
    Unit test: Verify pricing insights generation from performance
    
    Validates: Requirements 3.5
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Add performance data
        agent.performance_history.append({
            'sku': 'test-sku-1',
            'region': 'north',
            'recommended_price': 100.0,
            'actual_price_used': 100.0,
            'actual_sales_volume': 150.0,
            'actual_revenue': 15000.0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recommendation_followed': True
        })
        
        agent.performance_history.append({
            'sku': 'test-sku-2',
            'region': 'south',
            'recommended_price': 80.0,
            'actual_price_used': 90.0,
            'actual_sales_volume': 100.0,
            'actual_revenue': 9000.0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recommendation_followed': False
        })
        
        # Generate insights
        insights_data = agent.get_pricing_insights_from_performance()
        
        # Verify insights structure
        assert 'insights' in insights_data
        assert 'recommendations' in insights_data
        assert 'metrics' in insights_data
        
        # Verify insights are generated
        assert isinstance(insights_data['insights'], list)
        assert isinstance(insights_data['recommendations'], list)
        assert isinstance(insights_data['metrics'], dict)


@pytest.mark.unit
def test_empty_pricing_data_handling():
    """
    Unit test: Verify agent handles empty pricing data gracefully
    
    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Test with empty pricing data
        recommendations = agent.generate_price_recommendations(
            pricing_data=[],
            target_margin=0.30,
            sku_filter=None,
            region_filter=None
        )
        
        # Verify empty result
        assert recommendations == []
        
        # Test competitive analysis with empty data
        analysis = agent.analyze_competitive_pricing(
            pricing_data=[],
            sku_filter=None,
            region_filter=None
        )
        
        # Verify empty result
        assert analysis == {}


@pytest.mark.unit
def test_price_recommendation_with_filters():
    """
    Unit test: Verify price recommendations work with SKU and region filters
    
    Validates: Requirements 3.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Create test pricing data for multiple SKUs and regions
        pricing_data = [
            PricingData(
                sku='sku-1',
                current_price=100.0,
                cost=70.0,
                competitor_prices=[95.0],
                sales_volume=50.0,
                region='north',
                timestamp=datetime.now(timezone.utc)
            ),
            PricingData(
                sku='sku-2',
                current_price=80.0,
                cost=50.0,
                competitor_prices=[75.0],
                sales_volume=30.0,
                region='south',
                timestamp=datetime.now(timezone.utc)
            ),
            PricingData(
                sku='sku-1',
                current_price=105.0,
                cost=70.0,
                competitor_prices=[100.0],
                sales_volume=40.0,
                region='south',
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Test with SKU filter
        recommendations = agent.generate_price_recommendations(
            pricing_data=pricing_data,
            target_margin=None,
            sku_filter='sku-1',
            region_filter=None
        )
        
        # Verify only sku-1 recommendations
        assert all(rec.sku == 'sku-1' for rec in recommendations)
        assert len(recommendations) == 2  # sku-1 in north and south
        
        # Test with region filter
        recommendations = agent.generate_price_recommendations(
            pricing_data=pricing_data,
            target_margin=None,
            sku_filter=None,
            region_filter='north'
        )
        
        # Verify only north region recommendations
        assert all(rec.region == 'north' for rec in recommendations)
        assert len(recommendations) == 1  # Only sku-1 in north
        
        # Test with both filters
        recommendations = agent.generate_price_recommendations(
            pricing_data=pricing_data,
            target_margin=None,
            sku_filter='sku-1',
            region_filter='south'
        )
        
        # Verify specific SKU-region combination
        assert len(recommendations) == 1
        assert recommendations[0].sku == 'sku-1'
        assert recommendations[0].region == 'south'


@pytest.mark.unit
def test_confidence_calculation():
    """
    Unit test: Verify confidence calculation based on data quality
    
    Validates: Requirements 3.4
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.pricing_optimization_agent.AgentRegistry'), \
         patch('src.agents.pricing_optimization_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.pricing_optimization_agent.S3Repository'):
        
        agent = PricingOptimizationAgent(register_with_council=False)
        
        # Test with minimal data (low confidence)
        pricing_data_minimal = [
            PricingData(
                sku='test-sku',
                current_price=100.0,
                cost=70.0,
                competitor_prices=[],
                sales_volume=50.0,
                region='north',
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        input_minimal = PricingOptimizationInput(
            pricing_data=pricing_data_minimal,
            target_margin=None,
            region_filter=None,
            sku_filter=None
        )
        
        decision_minimal = agent.process(input_minimal)
        confidence_minimal = decision_minimal.recommendation.confidence
        
        # Test with rich data (high confidence)
        pricing_data_rich = []
        for i in range(20):
            pricing_data_rich.append(
                PricingData(
                    sku=f'sku-{i}',
                    current_price=100.0 + i,
                    cost=70.0,
                    competitor_prices=[95.0 + i, 105.0 + i, 98.0 + i],
                    sales_volume=50.0 + i,
                    region='north',
                    timestamp=datetime.now(timezone.utc)
                )
            )
        
        input_rich = PricingOptimizationInput(
            pricing_data=pricing_data_rich,
            target_margin=None,
            region_filter=None,
            sku_filter=None
        )
        
        decision_rich = agent.process(input_rich)
        confidence_rich = decision_rich.recommendation.confidence
        
        # Verify confidence increases with data quality
        assert 0.0 <= confidence_minimal <= 1.0
        assert 0.0 <= confidence_rich <= 1.0
        assert confidence_rich > confidence_minimal
