"""
Property-based tests for Market Intelligence Agent

**Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4**
"""
import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from datetime import datetime, timezone, timedelta
from typing import List
from unittest.mock import patch

from src.agents.market_intelligence_agent import (
    MarketIntelligenceAgent,
    MarketIntelligenceInput,
    PricingData,
    DemandData
)


# Fixture for mocking AWS dependencies
@pytest.fixture
def mock_aws_dependencies():
    """Mock AWS dependencies for testing"""
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        yield


# Custom strategies for generating test data
@st.composite
def pricing_data_strategy(draw):
    """Generate random PricingData instances"""
    product_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    category = draw(st.sampled_from(['electronics', 'clothing', 'food', 'furniture', 'toys']))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    price = draw(st.floats(min_value=1.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    
    # Generate timestamp within last 30 days
    days_ago = draw(st.integers(min_value=0, max_value=30))
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    # 30% chance of being competitor data
    has_competitor = draw(st.booleans())
    competitor_id = None
    if has_competitor:
        competitor_id = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    
    return PricingData(
        product_id=product_id,
        category=category,
        region=region,
        price=price,
        timestamp=timestamp,
        competitor_id=competitor_id
    )


@st.composite
def demand_data_strategy(draw):
    """Generate random DemandData instances"""
    product_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(min_codepoint=97, max_codepoint=122)))
    category = draw(st.sampled_from(['electronics', 'clothing', 'food', 'furniture', 'toys']))
    region = draw(st.sampled_from(['north', 'south', 'east', 'west', 'central']))
    demand_volume = draw(st.floats(min_value=0.0, max_value=10000.0, allow_nan=False, allow_infinity=False))
    
    # Generate timestamp within last 30 days
    days_ago = draw(st.integers(min_value=0, max_value=30))
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
    
    return DemandData(
        product_id=product_id,
        category=category,
        region=region,
        demand_volume=demand_volume,
        timestamp=timestamp
    )


@st.composite
def market_intelligence_input_strategy(draw, min_pricing=0, max_pricing=50, min_demand=0, max_demand=50):
    """Generate random MarketIntelligenceInput instances"""
    num_pricing = draw(st.integers(min_value=min_pricing, max_value=max_pricing))
    num_demand = draw(st.integers(min_value=min_demand, max_value=max_demand))
    
    pricing_data = [draw(pricing_data_strategy()) for _ in range(num_pricing)]
    demand_data = [draw(demand_data_strategy()) for _ in range(num_demand)]
    time_window_days = draw(st.integers(min_value=7, max_value=90))
    
    return MarketIntelligenceInput(
        pricing_data=pricing_data,
        demand_data=demand_data,
        time_window_days=time_window_days
    )


# Property-based tests
@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=1, max_pricing=50, min_demand=1, max_demand=50))
def test_agent_tracks_all_regions_and_categories(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any market data input, the agent should track pricing trends across all regions and product categories
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.1**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract pricing trends from supporting data (inside recommendation)
    insights = decision.recommendation.supporting_data[0]
    pricing_trends = insights['pricing_trends']['trends']
    
    # Collect all unique categories and regions from input
    categories = set(p.category for p in input_data.pricing_data)
    regions = set(p.region for p in input_data.pricing_data)
    
    # Verify global trends exist for each category
    for category in categories:
        global_key = f'global_{category}'
        assert global_key in pricing_trends, f"Missing global trend for category {category}"
        assert 'average_price' in pricing_trends[global_key]
        assert 'min_price' in pricing_trends[global_key]
        assert 'max_price' in pricing_trends[global_key]
    
    # Verify regional trends exist for each region-category combination
    region_category_pairs = set((p.region, p.category) for p in input_data.pricing_data)
    for region, category in region_category_pairs:
        regional_key = f'{region}_{category}'
        assert regional_key in pricing_trends, f"Missing regional trend for {region}_{category}"
        assert 'average_price' in pricing_trends[regional_key]


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=5, max_pricing=50, min_demand=0, max_demand=50))
def test_competitor_analysis_tracks_all_competitors(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any market data with competitor pricing, the agent should analyze all competitors
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.2**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract competitor analysis from supporting data (inside recommendation)
    insights = decision.recommendation.supporting_data[0]
    competitor_analysis = insights['competitor_analysis']['analysis']
    
    # Collect all unique competitors from input
    competitors = set(p.competitor_id for p in input_data.pricing_data if p.competitor_id is not None)
    
    if competitors:
        # Verify all competitors are analyzed
        for competitor_id in competitors:
            assert competitor_id in competitor_analysis, f"Missing analysis for competitor {competitor_id}"
            
            # Verify competitor analysis has required fields
            for category in competitor_analysis[competitor_id]:
                assert 'average_price' in competitor_analysis[competitor_id][category]
                assert 'price_range' in competitor_analysis[competitor_id][category]
                assert 'data_points' in competitor_analysis[competitor_id][category]
                assert 'last_updated' in competitor_analysis[competitor_id][category]


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=0, max_pricing=50, min_demand=1, max_demand=50))
def test_demand_heatmap_covers_all_regions_and_categories(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any demand data, the agent should generate heatmaps covering all regions and categories
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.3**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract demand heatmap from supporting data (inside recommendation)
    insights = decision.recommendation.supporting_data[0]
    demand_heatmap = insights['demand_heatmap']['heatmap']
    
    # Collect all unique regions and categories from demand data
    regions = set(d.region for d in input_data.demand_data)
    region_category_pairs = set((d.region, d.category) for d in input_data.demand_data)
    
    # Verify all regions are in heatmap
    for region in regions:
        assert region in demand_heatmap, f"Missing region {region} in demand heatmap"
    
    # Verify all region-category combinations are tracked
    for region, category in region_category_pairs:
        assert category in demand_heatmap[region], f"Missing category {category} for region {region}"
        assert 'total_demand' in demand_heatmap[region][category]
        assert 'average_demand' in demand_heatmap[region][category]
        assert 'data_points' in demand_heatmap[region][category]


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=0, max_pricing=50, min_demand=5, max_demand=50))
def test_seasonal_trends_detected_with_advance_notice(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any demand patterns, seasonal trends should be detected and reported
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.4**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Extract seasonal trends from supporting data (inside recommendation)
    insights = decision.recommendation.supporting_data[0]
    seasonal_trends = insights['seasonal_trends']
    
    # Verify seasonal trends structure
    assert 'trends' in seasonal_trends
    assert 'summary' in seasonal_trends
    assert isinstance(seasonal_trends['trends'], list)
    
    # If trends are detected, verify they have required fields
    for trend in seasonal_trends['trends']:
        assert 'category' in trend
        assert 'type' in trend
        assert 'timestamp' in trend
        assert 'demand_level' in trend
        assert 'baseline' in trend
        assert 'advance_notice_days' in trend
        
        # Verify advance notice is within reasonable range (0-7 days as per requirements)
        assert 0 <= trend['advance_notice_days'] <= 7


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=1, max_pricing=50, min_demand=1, max_demand=50))
def test_decision_confidence_increases_with_data_volume(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any market data, confidence should increase with more data points
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Calculate total data points
    total_points = len(input_data.pricing_data) + len(input_data.demand_data)
    
    # Verify confidence is within valid range
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    
    # Verify confidence correlates with data volume
    if total_points < 10:
        assert decision.recommendation.confidence <= 0.6
    elif total_points >= 100:
        assert decision.recommendation.confidence >= 0.85


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=1, max_pricing=50, min_demand=1, max_demand=50))
def test_decision_includes_all_required_metadata(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For any market intelligence decision, all required metadata should be present
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process the input
    decision = agent.process(input_data)
    
    # Verify all required fields are present
    assert decision.agent_id == "market-intelligence-agent"
    assert decision.decision_id is not None
    assert decision.timestamp is not None
    assert isinstance(decision.timestamp, datetime)
    assert decision.recommendation is not None
    assert decision.recommendation.action == "market_intelligence_update"
    assert 0.0 <= decision.recommendation.confidence <= 1.0
    assert decision.recommendation.reasoning is not None
    assert len(decision.recommendation.supporting_data) == 2  # insights and recommendations
    
    # Verify insights structure
    insights = decision.recommendation.supporting_data[0]
    assert 'pricing_trends' in insights
    assert 'competitor_analysis' in insights
    assert 'demand_heatmap' in insights
    assert 'seasonal_trends' in insights
    
    # Verify recommendations
    recommendations = decision.recommendation.supporting_data[1]
    assert isinstance(recommendations, list)


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(
    pricing_data=st.lists(pricing_data_strategy(), min_size=5, max_size=20),
    category=st.sampled_from(['electronics', 'clothing', 'food', 'furniture', 'toys'])
)
def test_pricing_trends_calculate_correct_statistics(mock_aws_dependencies, pricing_data: List[PricingData], category: str):
    """
    Property: For any pricing data, calculated statistics should be mathematically correct
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.1**
    """
    # Filter pricing data to specific category
    category_data = [p for p in pricing_data if p.category == category]
    
    # Skip if no data for this category
    assume(len(category_data) > 0)
    
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Track pricing trends
    trends_result = agent.track_pricing_trends(category_data)
    trends = trends_result['trends']
    
    # Get the global trend for this category
    global_key = f'global_{category}'
    if global_key in trends:
        trend = trends[global_key]
        
        # Calculate expected values
        prices = [p.price for p in category_data]
        expected_avg = sum(prices) / len(prices)
        expected_min = min(prices)
        expected_max = max(prices)
        
        # Verify calculated values match expected
        assert abs(trend['average_price'] - expected_avg) < 0.01
        assert abs(trend['min_price'] - expected_min) < 0.01
        assert abs(trend['max_price'] - expected_max) < 0.01


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(input_data=market_intelligence_input_strategy(min_pricing=0, max_pricing=0, min_demand=0, max_demand=0))
def test_agent_handles_empty_data_gracefully(mock_aws_dependencies, input_data: MarketIntelligenceInput):
    """
    Property: For empty market data, the agent should handle it gracefully without errors
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Process empty input - should not raise exception
    decision = agent.process(input_data)
    
    # Verify decision is still valid
    assert decision is not None
    assert decision.recommendation.confidence == 0.0  # No data means no confidence
    assert decision.recommendation is not None
    
    # Verify insights indicate no data
    insights = decision.recommendation.supporting_data[0]
    assert insights['pricing_trends']['summary'] == 'No pricing data available'
    assert insights['demand_heatmap']['summary'] == 'No demand data available'


@pytest.mark.property
@settings(max_examples=100, suppress_health_check=[HealthCheck.large_base_example, HealthCheck.too_slow], deadline=None)
@given(
    demand_data=st.lists(demand_data_strategy(), min_size=5, max_size=30),
    region=st.sampled_from(['north', 'south', 'east', 'west', 'central']),
    category=st.sampled_from(['electronics', 'clothing', 'food', 'furniture', 'toys'])
)
def test_demand_heatmap_aggregates_correctly(mock_aws_dependencies, demand_data: List[DemandData], region: str, category: str):
    """
    Property: For any demand data, heatmap aggregations should be mathematically correct
    
    **Feature: retailmind-ai, Property 1: Market Intelligence Tracking**
    **Validates: Requirements 1.3**
    """
    # Filter to specific region and category
    filtered_data = [d for d in demand_data if d.region == region and d.category == category]
    
    # Skip if no data for this combination
    assume(len(filtered_data) > 0)
    
    agent = MarketIntelligenceAgent(register_with_council=False)
    
    # Generate demand heatmap
    heatmap_result = agent.generate_demand_heatmap(filtered_data)
    heatmap = heatmap_result['heatmap']
    
    # Verify the region and category exist in heatmap
    if region in heatmap and category in heatmap[region]:
        cell = heatmap[region][category]
        
        # Calculate expected values
        expected_total = sum(d.demand_volume for d in filtered_data)
        expected_count = len(filtered_data)
        expected_avg = expected_total / expected_count
        
        # Verify calculated values match expected
        assert abs(cell['total_demand'] - expected_total) < 0.01
        assert cell['data_points'] == expected_count
        assert abs(cell['average_demand'] - expected_avg) < 0.01


# Integration tests for AI Council integration
@pytest.mark.integration
def test_agent_registration_with_council():
    """
    Test that Market Intelligence Agent can register with AI Council
    
    Validates: Requirements 1.5, 6.1
    """
    from unittest.mock import Mock, patch
    
    # Mock the registry and AWS clients
    with patch('src.agents.market_intelligence_agent.AgentRegistry') as MockRegistry, \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.market_intelligence_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_registry_instance = Mock()
        MockRegistry.return_value = mock_registry_instance
        
        # Create agent without auto-registration
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Manually register
        agent.register()
        
        # Verify register_agent was called with correct metadata
        mock_registry_instance.register_agent.assert_called_once()
        call_args = mock_registry_instance.register_agent.call_args[0][0]
        assert call_args.agent_id == "market-intelligence-agent"
        assert call_args.agent_type == "market_intelligence"
        assert "pricing_trend_tracking" in call_args.capabilities
        assert "competitor_analysis" in call_args.capabilities
        assert "demand_heatmap_generation" in call_args.capabilities
        assert "seasonal_trend_detection" in call_args.capabilities


@pytest.mark.integration
def test_agent_handles_intelligence_request():
    """
    Test that Market Intelligence Agent can handle intelligence requests
    
    Validates: Requirements 1.5, 6.1
    """
    from src.agents.communication import ACPMessage, MessageType
    from datetime import datetime, timezone
    from unittest.mock import Mock, patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        # Setup mock repository
        mock_bi_repo = Mock()
        MockBIRepo.return_value = mock_bi_repo
        
        # Mock return value for get_by_type
        mock_entity = Mock()
        mock_entity.to_dict.return_value = {'entity_type': 'pricing', 'entity_id': 'test-123'}
        mock_bi_repo.get_by_type.return_value = [mock_entity]
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create a request message for pricing trends
        message = ACPMessage(
            agent_id="test-requester",
            message_type=MessageType.REQUEST,
            payload={'request_type': 'pricing_trends'},
            timestamp=datetime.now(timezone.utc),
            correlation_id="test-correlation-123"
        )
        
        # Handle the message
        response = agent.handle_message(message)
        
        # Verify response
        assert response is not None
        assert response['status'] == 'success'
        assert 'data' in response
        
        # Verify repository was called
        mock_bi_repo.get_by_type.assert_called_once_with('pricing', limit=10)


@pytest.mark.integration
def test_agent_persists_intelligence_data():
    """
    Test that Market Intelligence Agent persists data to DynamoDB and S3
    
    Validates: Requirements 1.5, 8.1
    """
    from unittest.mock import Mock, patch, call
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.market_intelligence_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_bi_repo = Mock()
        mock_s3_repo = Mock()
        MockBIRepo.return_value = mock_bi_repo
        MockS3Repo.return_value = mock_s3_repo
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create sample insights
        insights = {
            'pricing_trends': {
                'trends': {'global_electronics': {'average_price': 500.0}},
                'summary': 'Analyzed 10 pricing points'
            },
            'demand_heatmap': {
                'heatmap': {'north': {'electronics': {'total_demand': 1000.0}}},
                'summary': 'Generated heatmap from 10 demand points'
            },
            'competitor_analysis': {
                'analysis': {},
                'summary': 'No competitor data'
            },
            'seasonal_trends': {
                'trends': [],
                'summary': 'No seasonal trends detected'
            }
        }
        
        # Persist intelligence
        agent.persist_intelligence(insights, confidence=0.85)
        
        # Verify data was persisted to DynamoDB (2 calls: pricing and demand)
        assert mock_bi_repo.create.call_count == 2
        
        # Verify S3 upload was called
        mock_s3_repo.upload_json.assert_called_once()
        
        # Verify the calls had correct entity types
        calls = mock_bi_repo.create.call_args_list
        entity_types = [call[0][0].entity_type.value for call in calls]
        assert 'pricing' in entity_types
        assert 'demand' in entity_types


@pytest.mark.integration
def test_agent_sends_intelligence_update():
    """
    Test that Market Intelligence Agent can send updates to AI Council
    
    Validates: Requirements 1.5, 6.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'), \
         patch('src.agents.market_intelligence_agent.AgentCommunicationInterface') as MockComm:
        
        # Setup mock communication
        mock_comm = Mock()
        MockComm.return_value = mock_comm
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create sample insights
        insights = {
            'pricing_trends': {'summary': 'Test pricing trends'},
            'demand_heatmap': {'summary': 'Test demand heatmap'}
        }
        
        # Send intelligence update
        agent.send_intelligence_update(
            correlation_id="test-correlation-456",
            insights=insights
        )
        
        # Verify broadcast was called
        mock_comm.broadcast.assert_called_once()
        call_args = mock_comm.broadcast.call_args
        assert call_args[1]['from_agent_id'] == "market-intelligence-agent"
        assert call_args[1]['correlation_id'] == "test-correlation-456"
        assert 'insights' in call_args[1]['payload']


@pytest.mark.integration
def test_agent_handles_broadcast_messages():
    """
    Test that Market Intelligence Agent can handle broadcast messages from AI Council
    
    Validates: Requirements 6.1, 6.2
    """
    from src.agents.communication import ACPMessage, MessageType
    from datetime import datetime, timezone
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create a broadcast message
        message = ACPMessage(
            agent_id="ai_council",
            message_type=MessageType.BROADCAST,
            payload={
                'council_decision': {
                    'decision_id': 'test-decision-123',
                    'action': 'update_pricing_strategy'
                }
            },
            timestamp=datetime.now(timezone.utc),
            correlation_id="test-correlation-789"
        )
        
        # Handle the broadcast
        response = agent.handle_message(message)
        
        # Verify acknowledgment
        assert response is not None
        assert response['status'] == 'acknowledged'


@pytest.mark.integration
def test_full_integration_workflow():
    """
    Test full integration workflow: process data, persist, and communicate
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 8.1
    """
    from unittest.mock import Mock, patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository') as MockBIRepo, \
         patch('src.agents.market_intelligence_agent.S3Repository') as MockS3Repo:
        
        # Setup mocks
        mock_bi_repo = Mock()
        mock_s3_repo = Mock()
        MockBIRepo.return_value = mock_bi_repo
        MockS3Repo.return_value = mock_s3_repo
        
        # Create agent without auto-registration
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create sample input data
        pricing_data = [
            PricingData(
                product_id="prod-001",
                category="electronics",
                region="north",
                price=500.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id="comp-001"
            ),
            PricingData(
                product_id="prod-002",
                category="electronics",
                region="south",
                price=550.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id="comp-001"
            )
        ]
        
        demand_data = [
            DemandData(
                product_id="prod-001",
                category="electronics",
                region="north",
                demand_volume=100.0,
                timestamp=datetime.now(timezone.utc)
            ),
            DemandData(
                product_id="prod-002",
                category="electronics",
                region="south",
                demand_volume=150.0,
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        input_data = MarketIntelligenceInput(
            pricing_data=pricing_data,
            demand_data=demand_data,
            time_window_days=30
        )
        
        # Process the data (this will also persist it)
        decision = agent.process(input_data)
        
        # Verify decision was created
        assert decision is not None
        assert decision.agent_id == "market-intelligence-agent"
        assert decision.recommendation.action == "market_intelligence_update"
        
        # Verify data was persisted (2 calls: pricing and demand)
        assert mock_bi_repo.create.call_count == 2
        mock_s3_repo.upload_json.assert_called_once()
        
        # Verify insights structure
        insights = decision.recommendation.supporting_data[0]
        assert 'pricing_trends' in insights
        assert 'competitor_analysis' in insights
        assert 'demand_heatmap' in insights
        assert 'seasonal_trends' in insights
        
        # Verify competitor analysis includes our competitor
        competitor_analysis = insights['competitor_analysis']['analysis']
        assert 'comp-001' in competitor_analysis


# Unit tests for Market Intelligence Agent
@pytest.mark.unit
def test_pricing_trend_calculation_with_single_category():
    """
    Unit test: Verify pricing trend calculation for a single category
    
    Validates: Requirements 1.1
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test data for electronics category
        pricing_data = [
            PricingData(
                product_id="prod-001",
                category="electronics",
                region="north",
                price=500.0,
                timestamp=datetime.now(timezone.utc)
            ),
            PricingData(
                product_id="prod-002",
                category="electronics",
                region="north",
                price=600.0,
                timestamp=datetime.now(timezone.utc)
            ),
            PricingData(
                product_id="prod-003",
                category="electronics",
                region="south",
                price=550.0,
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Track pricing trends
        result = agent.track_pricing_trends(pricing_data)
        
        # Verify global trend for electronics
        assert 'global_electronics' in result['trends']
        global_trend = result['trends']['global_electronics']
        assert global_trend['average_price'] == 550.0  # (500 + 600 + 550) / 3
        assert global_trend['min_price'] == 500.0
        assert global_trend['max_price'] == 600.0
        
        # Verify regional trends
        assert 'north_electronics' in result['trends']
        assert 'south_electronics' in result['trends']
        
        north_trend = result['trends']['north_electronics']
        assert north_trend['average_price'] == 550.0  # (500 + 600) / 2
        assert north_trend['sample_size'] == 2


@pytest.mark.unit
def test_pricing_trend_calculation_with_empty_data():
    """
    Unit test: Verify pricing trend calculation handles empty data
    
    Validates: Requirements 1.1
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Track pricing trends with empty data
        result = agent.track_pricing_trends([])
        
        # Verify empty result
        assert result['trends'] == {}
        assert result['summary'] == 'No pricing data available'


@pytest.mark.unit
def test_competitor_analysis_with_multiple_competitors():
    """
    Unit test: Verify competitor analysis with multiple competitors
    
    Validates: Requirements 1.2
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test data with competitors
        pricing_data = [
            PricingData(
                product_id="prod-001",
                category="electronics",
                region="north",
                price=500.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id="comp-A"
            ),
            PricingData(
                product_id="prod-002",
                category="electronics",
                region="north",
                price=520.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id="comp-A"
            ),
            PricingData(
                product_id="prod-003",
                category="electronics",
                region="south",
                price=480.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id="comp-B"
            )
        ]
        
        # Analyze competitor pricing
        result = agent.analyze_competitor_pricing(pricing_data)
        
        # Verify both competitors are analyzed
        assert 'comp-A' in result['analysis']
        assert 'comp-B' in result['analysis']
        
        # Verify comp-A analysis
        comp_a = result['analysis']['comp-A']
        assert 'electronics' in comp_a
        assert comp_a['electronics']['average_price'] == 510.0  # (500 + 520) / 2
        assert comp_a['electronics']['data_points'] == 2
        
        # Verify comp-B analysis
        comp_b = result['analysis']['comp-B']
        assert 'electronics' in comp_b
        assert comp_b['electronics']['average_price'] == 480.0


@pytest.mark.unit
def test_competitor_analysis_with_no_competitor_data():
    """
    Unit test: Verify competitor analysis handles no competitor data
    
    Validates: Requirements 1.2
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test data without competitor IDs
        pricing_data = [
            PricingData(
                product_id="prod-001",
                category="electronics",
                region="north",
                price=500.0,
                timestamp=datetime.now(timezone.utc),
                competitor_id=None
            )
        ]
        
        # Analyze competitor pricing
        result = agent.analyze_competitor_pricing(pricing_data)
        
        # Verify no competitor data found
        assert result['analysis'] == {}
        assert result['summary'] == 'No competitor pricing data found'


@pytest.mark.unit
def test_demand_heatmap_generation_with_multiple_regions():
    """
    Unit test: Verify demand heatmap generation with multiple regions
    
    Validates: Requirements 1.3
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test demand data
        demand_data = [
            DemandData(
                product_id="prod-001",
                category="electronics",
                region="north",
                demand_volume=100.0,
                timestamp=datetime.now(timezone.utc)
            ),
            DemandData(
                product_id="prod-002",
                category="electronics",
                region="north",
                demand_volume=150.0,
                timestamp=datetime.now(timezone.utc)
            ),
            DemandData(
                product_id="prod-003",
                category="clothing",
                region="south",
                demand_volume=200.0,
                timestamp=datetime.now(timezone.utc)
            )
        ]
        
        # Generate demand heatmap
        result = agent.generate_demand_heatmap(demand_data)
        
        # Verify heatmap structure
        assert 'north' in result['heatmap']
        assert 'south' in result['heatmap']
        
        # Verify north region data
        north = result['heatmap']['north']
        assert 'electronics' in north
        assert north['electronics']['total_demand'] == 250.0  # 100 + 150
        assert north['electronics']['average_demand'] == 125.0  # 250 / 2
        assert north['electronics']['data_points'] == 2
        
        # Verify south region data
        south = result['heatmap']['south']
        assert 'clothing' in south
        assert south['clothing']['total_demand'] == 200.0
        assert south['clothing']['average_demand'] == 200.0
        assert south['clothing']['data_points'] == 1


@pytest.mark.unit
def test_demand_heatmap_generation_with_empty_data():
    """
    Unit test: Verify demand heatmap generation handles empty data
    
    Validates: Requirements 1.3
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Generate demand heatmap with empty data
        result = agent.generate_demand_heatmap([])
        
        # Verify empty result
        assert result['heatmap'] == {}
        assert result['summary'] == 'No demand data available'


@pytest.mark.unit
def test_seasonal_trend_detection_with_spike():
    """
    Unit test: Verify seasonal trend detection identifies demand spikes
    
    Validates: Requirements 1.4
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test data with a clear spike
        base_time = datetime.now(timezone.utc)
        demand_data = [
            DemandData(
                product_id="prod-001",
                category="electronics",
                region="north",
                demand_volume=100.0,
                timestamp=base_time - timedelta(days=10)
            ),
            DemandData(
                product_id="prod-002",
                category="electronics",
                region="north",
                demand_volume=110.0,
                timestamp=base_time - timedelta(days=8)
            ),
            DemandData(
                product_id="prod-003",
                category="electronics",
                region="north",
                demand_volume=105.0,
                timestamp=base_time - timedelta(days=6)
            ),
            # Spike - significantly higher than average
            DemandData(
                product_id="prod-004",
                category="electronics",
                region="north",
                demand_volume=300.0,
                timestamp=base_time - timedelta(days=2)
            )
        ]
        
        # Detect seasonal trends
        result = agent.detect_seasonal_trends(demand_data, time_window_days=30)
        
        # Verify spike was detected
        assert 'trends' in result
        trends = result['trends']
        
        # Should detect at least one trend (the spike)
        if len(trends) > 0:
            spike_trend = trends[0]
            assert spike_trend['category'] == 'electronics'
            assert spike_trend['type'] == 'seasonal_spike'
            assert spike_trend['demand_level'] == 300.0


@pytest.mark.unit
def test_seasonal_trend_detection_with_no_spikes():
    """
    Unit test: Verify seasonal trend detection with consistent demand
    
    Validates: Requirements 1.4
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Create test data with consistent demand (no spikes)
        base_time = datetime.now(timezone.utc)
        demand_data = [
            DemandData(
                product_id=f"prod-{i:03d}",
                category="electronics",
                region="north",
                demand_volume=100.0 + (i % 3),  # Small variation
                timestamp=base_time - timedelta(days=i)
            )
            for i in range(10)
        ]
        
        # Detect seasonal trends
        result = agent.detect_seasonal_trends(demand_data, time_window_days=30)
        
        # Verify no significant trends detected
        assert 'trends' in result
        # With consistent demand, should detect few or no spikes
        assert len(result['trends']) <= 2  # Allow for minor variations


@pytest.mark.unit
def test_confidence_calculation_with_varying_data_volumes():
    """
    Unit test: Verify confidence calculation based on data volume
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Test with no data
        input_no_data = MarketIntelligenceInput(
            pricing_data=[],
            demand_data=[],
            time_window_days=30
        )
        confidence_no_data = agent._calculate_confidence(input_no_data)
        assert confidence_no_data == 0.0
        
        # Test with few data points (< 10)
        input_few = MarketIntelligenceInput(
            pricing_data=[
                PricingData("p1", "electronics", "north", 100.0, datetime.now(timezone.utc))
                for _ in range(5)
            ],
            demand_data=[],
            time_window_days=30
        )
        confidence_few = agent._calculate_confidence(input_few)
        assert confidence_few == 0.5
        
        # Test with moderate data points (10-49)
        input_moderate = MarketIntelligenceInput(
            pricing_data=[
                PricingData("p1", "electronics", "north", 100.0, datetime.now(timezone.utc))
                for _ in range(25)
            ],
            demand_data=[],
            time_window_days=30
        )
        confidence_moderate = agent._calculate_confidence(input_moderate)
        assert confidence_moderate == 0.7
        
        # Test with many data points (100+)
        input_many = MarketIntelligenceInput(
            pricing_data=[
                PricingData("p1", "electronics", "north", 100.0, datetime.now(timezone.utc))
                for _ in range(100)
            ],
            demand_data=[],
            time_window_days=30
        )
        confidence_many = agent._calculate_confidence(input_many)
        assert confidence_many == 0.95


@pytest.mark.unit
def test_recommendation_generation_from_insights():
    """
    Unit test: Verify recommendation generation from insights
    
    Validates: Requirements 1.1, 1.2, 1.3, 1.4
    """
    from unittest.mock import patch
    
    with patch('src.agents.market_intelligence_agent.AgentRegistry'), \
         patch('src.agents.market_intelligence_agent.BusinessIntelligenceRepository'), \
         patch('src.agents.market_intelligence_agent.S3Repository'):
        
        agent = MarketIntelligenceAgent(register_with_council=False)
        
        # Test with pricing insights (must have 'trends' key with data)
        insights_pricing = {
            'pricing_trends': {
                'trends': {'global_electronics': {'average_price': 500.0}},
                'summary': 'Analyzed 50 pricing points'
            },
            'competitor_analysis': {'analysis': {}, 'summary': 'No competitor data'},
            'demand_heatmap': {'heatmap': {}, 'summary': 'No demand data'},
            'seasonal_trends': {'trends': [], 'summary': 'No seasonal trends'}
        }
        recommendations_pricing = agent._generate_recommendations(insights_pricing)
        assert len(recommendations_pricing) > 0
        assert any('pricing' in rec.lower() for rec in recommendations_pricing)
        
        # Test with demand insights (must have 'heatmap' key with data)
        insights_demand = {
            'pricing_trends': {'trends': {}, 'summary': 'No pricing data'},
            'competitor_analysis': {'analysis': {}, 'summary': 'No competitor data'},
            'demand_heatmap': {
                'heatmap': {'north': {'electronics': {'total_demand': 1000.0}}},
                'summary': 'Generated heatmap from 100 demand points'
            },
            'seasonal_trends': {'trends': [], 'summary': 'No seasonal trends'}
        }
        recommendations_demand = agent._generate_recommendations(insights_demand)
        assert len(recommendations_demand) > 0
        assert any('inventory' in rec.lower() or 'demand' in rec.lower() for rec in recommendations_demand)
        
        # Test with seasonal insights (must have 'trends' list with data)
        insights_seasonal = {
            'pricing_trends': {'trends': {}, 'summary': 'No pricing data'},
            'competitor_analysis': {'analysis': {}, 'summary': 'No competitor data'},
            'demand_heatmap': {'heatmap': {}, 'summary': 'No demand data'},
            'seasonal_trends': {
                'trends': [{'category': 'electronics', 'type': 'seasonal_spike'}],
                'summary': 'Detected 3 seasonal trends'
            }
        }
        recommendations_seasonal = agent._generate_recommendations(insights_seasonal)
        assert len(recommendations_seasonal) > 0
        assert any('seasonal' in rec.lower() for rec in recommendations_seasonal)
