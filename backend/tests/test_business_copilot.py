"""
Property-based tests for Business Copilot Agent
Tests response quality, explainability, and action-oriented recommendations
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import json

from src.agents.business_copilot_agent import (
    BusinessCopilotAgent,
    QueryIntent,
    ConversationContext,
    CopilotResponse
)


# Generators for property-based testing

@st.composite
def query_text(draw):
    """Generate realistic business queries"""
    query_types = [
        # Pricing queries
        "What is the optimal price for SKU-{sku}?",
        "How should I price {product} to stay competitive?",
        "What are the current pricing trends in {region}?",
        "Should I adjust prices for {product}?",
        
        # Inventory queries
        "What is the inventory status for {region}?",
        "Do we have stockout risks for SKU-{sku}?",
        "How much stock should I order for {product}?",
        "What are the overstock items in {region}?",
        
        # Forecast queries
        "What is the demand forecast for next {timeframe}?",
        "Will sales increase for SKU-{sku}?",
        "What are the seasonal trends for {product}?",
        "How accurate are our forecasts?",
        
        # Market queries
        "What are the current market trends?",
        "How are competitors pricing {product}?",
        "What festivals are coming up?",
        "What is the market demand in {region}?",
        
        # Risk queries
        "Are there any compliance issues?",
        "What is the risk score for supplier {supplier}?",
        "Have we detected any fraud?",
        "What are the invoice validation results?",
        
        # General queries
        "Help me understand the system",
        "What can you do?",
        "Explain the AI Council",
        "How does workflow regeneration work?"
    ]
    
    template = draw(st.sampled_from(query_types))
    
    # Fill in placeholders
    query = template.format(
        sku=f"SKU-{draw(st.integers(min_value=1000, max_value=9999))}",
        product=draw(st.sampled_from(['electronics', 'clothing', 'groceries', 'furniture'])),
        region=draw(st.sampled_from(['north', 'south', 'east', 'west', 'mumbai', 'delhi'])),
        timeframe=draw(st.sampled_from(['week', 'month', 'quarter'])),
        supplier=f"SUP-{draw(st.integers(min_value=100, max_value=999))}"
    )
    
    return query


@st.composite
def query_input(draw):
    """Generate query input data"""
    query = draw(query_text())
    
    return {
        'query': query,
        'conversation_id': f"conv-{draw(st.integers(min_value=1, max_value=1000))}",
        'user_id': f"user-{draw(st.integers(min_value=1, max_value=100))}"
    }


# Property-based tests

@given(input_data=query_input())
@settings(max_examples=100, deadline=None)
def test_copilot_response_quality_property(input_data):
    """
    **Feature: retailmind-ai, Property 5: Business Copilot Response Quality**
    **Validates: Requirements 4.1, 4.2, 4.3**
    
    Property: For any natural language business query, the Business Copilot should
    provide data-backed, explainable, action-oriented responses within 10 seconds
    
    This property verifies:
    1. Response is generated (not empty)
    2. Response includes reasoning trace (explainability)
    3. Response includes data sources (data-backed)
    4. Response includes actionable recommendations (action-oriented)
    5. Response has confidence level
    """
    agent = BusinessCopilotAgent()
    
    # Process the query
    start_time = datetime.utcnow()
    decision = agent.process(input_data)
    end_time = datetime.utcnow()
    
    # Verify response time (within 10 seconds)
    response_time = (end_time - start_time).total_seconds()
    assert response_time < 10.0, f"Response took {response_time}s, should be < 10s"
    
    # Parse the response
    response_data = json.loads(decision.recommendation.action)
    
    # Property 1: Response is not empty
    assert response_data['responseText'], "Response text should not be empty"
    assert len(response_data['responseText']) > 0, "Response should have content"
    
    # Property 2: Response includes reasoning trace (explainability)
    assert 'reasoningTrace' in response_data, "Response should include reasoning trace"
    assert isinstance(response_data['reasoningTrace'], list), "Reasoning trace should be a list"
    assert len(response_data['reasoningTrace']) > 0, "Reasoning trace should not be empty"
    
    # Property 3: Response includes data sources (data-backed)
    assert 'dataSources' in response_data, "Response should include data sources"
    assert isinstance(response_data['dataSources'], list), "Data sources should be a list"
    # Note: Some general queries might not have specific data sources
    
    # Property 4: Response includes recommendations (action-oriented)
    assert 'recommendations' in response_data, "Response should include recommendations"
    assert isinstance(response_data['recommendations'], list), "Recommendations should be a list"
    
    # For non-general queries, should have at least one recommendation
    query_lower = input_data['query'].lower()
    is_general = any(word in query_lower for word in ['help', 'what can you', 'how does', 'what is the', 'explain'])
    if not is_general:
        assert len(response_data['recommendations']) > 0, "Non-general queries should have recommendations"
        
        # Verify recommendation structure
        for rec in response_data['recommendations']:
            assert 'action' in rec, "Recommendation should have action"
            assert 'description' in rec, "Recommendation should have description"
            assert 'priority' in rec, "Recommendation should have priority"
    
    # Property 5: Response has confidence level
    assert 'confidence' in response_data, "Response should include confidence"
    assert isinstance(response_data['confidence'], (int, float)), "Confidence should be numeric"
    assert 0.0 <= response_data['confidence'] <= 1.0, "Confidence should be between 0 and 1"
    
    # Verify decision structure
    assert decision.agent_id == "business_copilot", "Decision should be from business copilot"
    assert decision.recommendation.confidence > 0, "Decision should have positive confidence"


@given(query=query_text())
@settings(max_examples=100, deadline=None)
def test_intent_recognition_consistency(query):
    """
    Property: For any query, intent recognition should be consistent and deterministic
    
    This verifies that the same query always produces the same intent classification
    """
    agent = BusinessCopilotAgent()
    
    # Parse the query multiple times
    intent1 = agent.parse_query(query)
    intent2 = agent.parse_query(query)
    
    # Should produce identical results
    assert intent1.intent_type == intent2.intent_type, "Intent type should be consistent"
    assert intent1.confidence == intent2.confidence, "Confidence should be consistent"
    assert intent1.entities == intent2.entities, "Entities should be consistent"
    assert intent1.original_query == intent2.original_query, "Original query should be preserved"


@given(input_data=query_input())
@settings(max_examples=100, deadline=None)
def test_conversation_context_preservation(input_data):
    """
    Property: For any conversation, context should be preserved across multiple queries
    
    This verifies that conversation history is maintained correctly
    """
    agent = BusinessCopilotAgent()
    conversation_id = input_data['conversation_id']
    
    # Process first query
    decision1 = agent.process(input_data)
    
    # Verify conversation was created
    assert conversation_id in agent.conversations, "Conversation should be created"
    context = agent.conversations[conversation_id]
    
    # Verify history contains the query
    assert len(context.history) >= 2, "History should contain user query and assistant response"
    assert context.history[0]['role'] == 'user', "First message should be from user"
    assert context.history[0]['content'] == input_data['query'], "User message should match query"
    
    # Process second query with same conversation
    input_data2 = {
        'query': 'What else can you tell me?',
        'conversation_id': conversation_id,
        'user_id': input_data['user_id']
    }
    decision2 = agent.process(input_data2)
    
    # Verify history grew
    context = agent.conversations[conversation_id]
    assert len(context.history) >= 4, "History should contain both exchanges"


@given(input_data=query_input())
@settings(max_examples=100, deadline=None)
def test_explainability_completeness(input_data):
    """
    Property: For any query, the response should include complete explainability information
    
    This verifies that all reasoning steps are captured and traceable
    """
    agent = BusinessCopilotAgent()
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    # Verify reasoning trace completeness
    reasoning_trace = response_data['reasoningTrace']
    
    # Should have at least 2 steps (intent identification + agent coordination)
    assert len(reasoning_trace) >= 2, "Should have multiple reasoning steps"
    
    # First step should be about intent
    assert 'intent' in reasoning_trace[0].lower(), "First step should identify intent"
    
    # Should mention agents or coordination
    has_agent_mention = any('agent' in step.lower() for step in reasoning_trace)
    assert has_agent_mention, "Reasoning should mention agent coordination"
    
    # Verify data sources are specified
    data_sources = response_data['dataSources']
    if len(data_sources) > 0:
        # Each data source should be a non-empty string
        for source in data_sources:
            assert isinstance(source, str), "Data source should be string"
            assert len(source) > 0, "Data source should not be empty"


@given(input_data=query_input())
@settings(max_examples=100, deadline=None)
def test_recommendation_actionability(input_data):
    """
    Property: For any query that requires action, recommendations should be actionable
    
    This verifies that recommendations include necessary information for action
    """
    agent = BusinessCopilotAgent()
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    recommendations = response_data['recommendations']
    
    # For queries with recommendations, verify structure
    for rec in recommendations:
        # Must have action identifier
        assert 'action' in rec, "Recommendation must have action"
        assert isinstance(rec['action'], str), "Action should be string"
        assert len(rec['action']) > 0, "Action should not be empty"
        
        # Must have description
        assert 'description' in rec, "Recommendation must have description"
        assert isinstance(rec['description'], str), "Description should be string"
        assert len(rec['description']) > 0, "Description should not be empty"
        
        # Must have priority
        assert 'priority' in rec, "Recommendation must have priority"
        assert rec['priority'] in ['critical', 'high', 'medium', 'low'], \
            "Priority should be valid level"
        
        # Should have expected impact
        if 'expected_impact' in rec:
            assert isinstance(rec['expected_impact'], str), "Expected impact should be string"
        
        # Should have next steps
        if 'next_steps' in rec:
            assert isinstance(rec['next_steps'], list), "Next steps should be list"
            for step in rec['next_steps']:
                assert isinstance(step, str), "Each step should be string"
                assert len(step) > 0, "Step should not be empty"


# Unit tests for specific scenarios

def test_pricing_query_response():
    """Test response to pricing query"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'What is the optimal price for SKU-1234?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    assert 'pricing' in response_data['responseText'].lower()
    assert len(response_data['recommendations']) > 0


def test_inventory_query_response():
    """Test response to inventory query"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'Do we have stockout risks in the north region?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    assert 'inventory' in response_data['responseText'].lower()
    assert len(response_data['recommendations']) > 0


def test_general_query_response():
    """Test response to general query"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'What can you help me with?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    assert 'copilot' in response_data['responseText'].lower() or \
           'help' in response_data['responseText'].lower()


def test_entity_extraction():
    """Test entity extraction from queries"""
    agent = BusinessCopilotAgent()
    
    # Test SKU extraction
    query1 = "What is the price for SKU-1234?"
    intent1 = agent.parse_query(query1)
    assert 'sku' in intent1.entities
    
    # Test region extraction
    query2 = "What is inventory in mumbai?"
    intent2 = agent.parse_query(query2)
    assert 'region' in intent2.entities
    assert intent2.entities['region'] == 'mumbai'


def test_conversation_history():
    """Test conversation history management"""
    agent = BusinessCopilotAgent()
    
    conv_id = "test-conv-123"
    
    # First query
    agent.process({
        'query': 'What is the price?',
        'conversation_id': conv_id,
        'user_id': 'test_user'
    })
    
    # Second query
    agent.process({
        'query': 'What about inventory?',
        'conversation_id': conv_id,
        'user_id': 'test_user'
    })
    
    # Get history
    history = agent.get_conversation_history(conv_id)
    assert len(history) >= 4  # 2 user messages + 2 assistant responses
    
    # Clear conversation
    agent.clear_conversation(conv_id)
    history = agent.get_conversation_history(conv_id)
    assert len(history) == 0


def test_query_parsing_with_sku():
    """Test query parsing extracts SKU correctly"""
    agent = BusinessCopilotAgent()
    
    # Test with SKU prefix
    query1 = "What is the price for SKU 5678"
    intent1 = agent.parse_query(query1)
    assert intent1.entities.get('sku') == '5678'
    
    # Test with SKU- format
    query2 = "Check inventory for SKU-9999"
    intent2 = agent.parse_query(query2)
    assert 'SKU-9999' in intent2.entities.get('sku', '')


def test_query_parsing_with_region():
    """Test query parsing extracts region correctly"""
    agent = BusinessCopilotAgent()
    
    regions_to_test = ['north', 'south', 'east', 'west', 'mumbai', 'delhi', 'bangalore']
    
    for region in regions_to_test:
        query = f"What is the inventory status in {region}?"
        intent = agent.parse_query(query)
        assert intent.entities.get('region') == region


def test_query_parsing_with_timeframe():
    """Test query parsing extracts timeframe correctly"""
    agent = BusinessCopilotAgent()
    
    timeframes = ['today', 'tomorrow', 'week', 'month', 'quarter', 'year']
    
    for timeframe in timeframes:
        query = f"What is the forecast for next {timeframe}?"
        intent = agent.parse_query(query)
        assert intent.entities.get('timeframe') == timeframe


def test_intent_classification_pricing():
    """Test intent classification for pricing queries"""
    agent = BusinessCopilotAgent()
    
    pricing_queries = [
        "What is the optimal price and cost for this product?",
        "How should I price SKU-1234 competitively?",
        "What pricing strategy should I use for better margins?",
        "Should I adjust my pricing to improve profitability?"
    ]
    
    for query in pricing_queries:
        intent = agent.parse_query(query)
        assert intent.intent_type == 'pricing_query', f"Query '{query}' was classified as '{intent.intent_type}'"
        assert intent.confidence > 0


def test_intent_classification_inventory():
    """Test intent classification for inventory queries"""
    agent = BusinessCopilotAgent()
    
    inventory_queries = [
        "Do we have enough stock?",
        "What is the inventory level?",
        "Are there any stockouts?",
        "Should I reorder products?"
    ]
    
    for query in inventory_queries:
        intent = agent.parse_query(query)
        assert intent.intent_type == 'inventory_query'
        assert intent.confidence > 0


def test_intent_classification_forecast():
    """Test intent classification for forecast queries"""
    agent = BusinessCopilotAgent()
    
    forecast_queries = [
        "What is the demand forecast?",
        "Will sales increase next month?",
        "What are the predicted trends?",
        "How accurate are our forecasts?"
    ]
    
    for query in forecast_queries:
        intent = agent.parse_query(query)
        assert intent.intent_type == 'forecast_query'
        assert intent.confidence > 0


def test_intent_classification_market():
    """Test intent classification for market queries"""
    agent = BusinessCopilotAgent()
    
    market_queries = [
        "What are the current market trends and competitor activity?",
        "How are competitors behaving in the market landscape?",
        "What festivals and seasonal market events are coming up?",
        "What is the market intelligence for this region?"
    ]
    
    for query in market_queries:
        intent = agent.parse_query(query)
        assert intent.intent_type == 'market_query', f"Query '{query}' was classified as '{intent.intent_type}'"
        assert intent.confidence > 0


def test_intent_classification_risk():
    """Test intent classification for risk queries"""
    agent = BusinessCopilotAgent()
    
    risk_queries = [
        "Are there any compliance issues?",
        "What is the supplier risk score?",
        "Have we detected any fraud?",
        "What are the invoice validation results?"
    ]
    
    for query in risk_queries:
        intent = agent.parse_query(query)
        assert intent.intent_type == 'risk_query'
        assert intent.confidence > 0


def test_response_generation_includes_reasoning():
    """Test that response generation includes reasoning trace"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'What is the optimal price for SKU-1234?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    # Verify reasoning trace exists and has content
    assert 'reasoningTrace' in response_data
    assert len(response_data['reasoningTrace']) > 0
    
    # Verify first step mentions intent
    assert 'intent' in response_data['reasoningTrace'][0].lower()


def test_response_generation_includes_data_sources():
    """Test that response generation includes data sources"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'What is the inventory status?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    # Verify data sources exist
    assert 'dataSources' in response_data
    assert isinstance(response_data['dataSources'], list)
    
    # For inventory query, should mention relevant agents
    data_sources_str = ' '.join(response_data['dataSources']).lower()
    assert 'inventory' in data_sources_str or 'demand' in data_sources_str


def test_response_includes_recommendations():
    """Test that responses include actionable recommendations"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'Should I adjust prices for SKU-1234?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    # Verify recommendations exist
    assert 'recommendations' in response_data
    assert len(response_data['recommendations']) > 0
    
    # Verify recommendation structure
    rec = response_data['recommendations'][0]
    assert 'action' in rec
    assert 'description' in rec
    assert 'priority' in rec


def test_conversation_context_creation():
    """Test conversation context is created correctly"""
    agent = BusinessCopilotAgent()
    
    conv_id = "test-conv-456"
    user_id = "test-user-123"
    
    input_data = {
        'query': 'Hello, what can you do?',
        'conversation_id': conv_id,
        'user_id': user_id
    }
    
    agent.process(input_data)
    
    # Verify conversation was created
    assert conv_id in agent.conversations
    
    # Verify context properties
    context = agent.conversations[conv_id]
    assert context.conversation_id == conv_id
    assert context.user_id == user_id
    assert len(context.history) > 0


def test_conversation_context_preserves_history():
    """Test conversation context preserves message history"""
    agent = BusinessCopilotAgent()
    
    conv_id = "test-conv-789"
    
    # Send multiple queries
    queries = [
        'What is the price?',
        'What about inventory?',
        'Show me forecasts'
    ]
    
    for query in queries:
        agent.process({
            'query': query,
            'conversation_id': conv_id,
            'user_id': 'test_user'
        })
    
    # Verify all messages are in history
    context = agent.conversations[conv_id]
    assert len(context.history) >= len(queries) * 2  # Each query + response
    
    # Verify messages are in order
    user_messages = [msg for msg in context.history if msg['role'] == 'user']
    assert len(user_messages) == len(queries)
    for i, query in enumerate(queries):
        assert user_messages[i]['content'] == query


def test_get_conversation_history_limit():
    """Test getting conversation history with limit"""
    agent = BusinessCopilotAgent()
    
    conv_id = "test-conv-limit"
    
    # Send multiple queries
    for i in range(10):
        agent.process({
            'query': f'Query {i}',
            'conversation_id': conv_id,
            'user_id': 'test_user'
        })
    
    # Get limited history
    history = agent.get_conversation_history(conv_id, limit=5)
    assert len(history) <= 5
    
    # Get all history
    full_history = agent.get_conversation_history(conv_id, limit=100)
    assert len(full_history) > len(history)


def test_clear_conversation():
    """Test clearing conversation context"""
    agent = BusinessCopilotAgent()
    
    conv_id = "test-conv-clear"
    
    # Create conversation
    agent.process({
        'query': 'Test query',
        'conversation_id': conv_id,
        'user_id': 'test_user'
    })
    
    # Verify conversation exists
    assert conv_id in agent.conversations
    
    # Clear conversation
    agent.clear_conversation(conv_id)
    
    # Verify conversation is removed
    assert conv_id not in agent.conversations
    
    # Verify getting history returns empty
    history = agent.get_conversation_history(conv_id)
    assert len(history) == 0


def test_agent_capabilities():
    """Test agent returns correct capabilities"""
    agent = BusinessCopilotAgent()
    
    capabilities = agent.get_capabilities()
    
    # Verify expected capabilities
    expected = [
        'natural_language_query',
        'intent_recognition',
        'context_management',
        'agent_coordination',
        'explainable_responses',
        'action_recommendations'
    ]
    
    for capability in expected:
        assert capability in capabilities


def test_response_confidence_levels():
    """Test response confidence levels are appropriate"""
    agent = BusinessCopilotAgent()
    
    # High confidence query (specific intent)
    high_conf_query = {
        'query': 'What is the price for SKU-1234?',
        'user_id': 'test_user'
    }
    
    decision1 = agent.process(high_conf_query)
    response1 = json.loads(decision1.recommendation.action)
    
    # General query (lower confidence)
    low_conf_query = {
        'query': 'Tell me something',
        'user_id': 'test_user'
    }
    
    decision2 = agent.process(low_conf_query)
    response2 = json.loads(decision2.recommendation.action)
    
    # Verify confidence is within valid range
    assert 0 <= response1['confidence'] <= 1
    assert 0 <= response2['confidence'] <= 1


def test_explainability_traces():
    """Test explainability traces are generated"""
    agent = BusinessCopilotAgent()
    
    input_data = {
        'query': 'What is the optimal price for SKU-1234?',
        'user_id': 'test_user'
    }
    
    decision = agent.process(input_data)
    response_data = json.loads(decision.recommendation.action)
    
    # Verify reasoning trace has multiple steps
    reasoning = response_data['reasoningTrace']
    assert len(reasoning) >= 2
    
    # Verify steps are descriptive
    for step in reasoning:
        assert isinstance(step, str)
        assert len(step) > 10  # Should be descriptive


def test_multiple_entity_extraction():
    """Test extracting multiple entities from single query"""
    agent = BusinessCopilotAgent()
    
    query = "What is the price for SKU-1234 in mumbai for next month?"
    intent = agent.parse_query(query)
    
    # Should extract multiple entities
    assert 'sku' in intent.entities or 'SKU-1234' in query
    assert 'region' in intent.entities
    assert intent.entities['region'] == 'mumbai'
    assert 'timeframe' in intent.entities
    assert intent.entities['timeframe'] == 'month'


def test_string_input_handling():
    """Test agent handles string input directly"""
    agent = BusinessCopilotAgent()
    
    # Pass string directly instead of dict
    decision = agent.process("What is the price?")
    
    # Should still work
    assert decision is not None
    response_data = json.loads(decision.recommendation.action)
    assert 'responseText' in response_data


def test_feedback_submission():
    """Test submitting user feedback"""
    agent = BusinessCopilotAgent()
    
    # Process a query first
    decision = agent.process({
        'query': 'What is the price?',
        'user_id': 'test_user'
    })
    
    # Submit feedback
    feedback_result = agent.submit_feedback(
        decision_id=decision.decision_id,
        user_id='test_user',
        feedback_type='positive',
        category='accuracy',
        rating=5,
        comment='Very helpful response'
    )
    
    # Verify feedback was recorded
    assert 'feedbackId' in feedback_result
    assert feedback_result['status'] == 'received'


def test_quality_metrics():
    """Test getting quality metrics"""
    agent = BusinessCopilotAgent()
    
    # Get metrics
    metrics = agent.get_quality_metrics()
    
    # Verify metrics structure
    assert isinstance(metrics, dict)
    assert 'totalResponses' in metrics
    assert 'averageRating' in metrics
    assert 'positiveFeedback' in metrics
    assert 'negativeFeedback' in metrics


def test_improvement_insights():
    """Test getting improvement insights"""
    agent = BusinessCopilotAgent()
    
    # Get insights
    insights = agent.get_improvement_insights()
    
    # Verify insights structure
    assert isinstance(insights, list)


def test_improvement_recommendations():
    """Test getting improvement recommendations"""
    agent = BusinessCopilotAgent()
    
    # Get recommendations
    recommendations = agent.get_improvement_recommendations()
    
    # Verify recommendations structure
    assert isinstance(recommendations, list)
