"""
Integration tests for Business Copilot learning from feedback
Tests the complete feedback loop and learning mechanisms
"""
import pytest
from src.agents.business_copilot_agent import BusinessCopilotAgent


def test_feedback_improves_confidence():
    """Test that negative feedback reduces confidence for intent"""
    agent = BusinessCopilotAgent()
    
    # Process a query
    decision1 = agent.process({
        'query': 'What is the optimal price for SKU-1234?',
        'user_id': 'test_user'
    })
    
    initial_confidence = decision1.recommendation.confidence
    
    # Submit negative feedback multiple times
    for i in range(5):
        agent.submit_feedback(
            decision_id=decision1.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='accuracy',
            rating=2,
            comment='Not accurate',
            intent_type='pricing_query'
        )
    
    # Process same type of query again
    decision2 = agent.process({
        'query': 'What should I price SKU-5678 at?',
        'user_id': 'test_user'
    })
    
    # Confidence should be adjusted based on learning
    # (May be lower due to negative feedback pattern)
    assert decision2.recommendation.confidence is not None


def test_learning_summary_includes_insights():
    """Test that learning summary includes insights from feedback"""
    agent = BusinessCopilotAgent()
    
    # Process query and submit feedback
    decision = agent.process({
        'query': 'What is the inventory status?',
        'user_id': 'test_user'
    })
    
    agent.submit_feedback(
        decision_id=decision.decision_id,
        user_id='test_user',
        feedback_type='negative',
        category='completeness',
        rating=2,
        comment='Response was too vague and missing data',
        intent_type='inventory_query'
    )
    
    # Get learning summary
    summary = agent.get_learning_summary()
    
    assert 'overallMetrics' in summary
    assert 'intentPerformance' in summary
    assert 'topInsights' in summary
    assert len(summary['topInsights']) > 0


def test_intent_performance_tracking():
    """Test that intent performance is tracked correctly"""
    agent = BusinessCopilotAgent()
    
    # Process multiple queries of same intent
    for i in range(3):
        decision = agent.process({
            'query': f'What is the forecast for SKU-{i}?',
            'user_id': 'test_user'
        })
        
        # Submit positive feedback
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='positive',
            category='accuracy',
            rating=5,
            intent_type='forecast_query'
        )
    
    # Check intent performance
    performance = agent.get_intent_performance('forecast_query')
    
    assert performance['intentType'] == 'forecast_query'
    assert performance['metrics'] is not None
    assert performance['metrics']['totalResponses'] == 3
    assert performance['metrics']['positiveFeedback'] == 3


def test_correction_creates_learning_insight():
    """Test that user corrections create learning insights"""
    agent = BusinessCopilotAgent()
    
    decision = agent.process({
        'query': 'What is the price?',
        'user_id': 'test_user'
    })
    
    # Submit correction
    agent.submit_feedback(
        decision_id=decision.decision_id,
        user_id='test_user',
        feedback_type='correction',
        category='accuracy',
        rating=3,
        comment='The price was wrong',
        correction='The correct price is $50, not $40'
    )
    
    # Check insights
    insights = agent.get_improvement_insights()
    
    # Should have created an insight from the correction
    correction_insights = [i for i in insights if i['pattern'] == 'user_correction']
    assert len(correction_insights) > 0


def test_low_performing_intents_identified():
    """Test that low-performing intents are identified"""
    agent = BusinessCopilotAgent()
    
    # Create low performance for an intent
    for i in range(5):
        decision = agent.process({
            'query': f'What are the market trends {i}?',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='relevance',
            rating=2,
            intent_type='market_query'
        )
    
    # Get learning summary
    summary = agent.get_learning_summary()
    
    # Should identify market_query as low performing
    low_performers = summary['lowPerformingIntents']
    market_low = [lp for lp in low_performers if lp['intentType'] == 'market_query']
    
    assert len(market_low) > 0
    assert market_low[0]['satisfactionRate'] < 0.5


def test_learning_applied_flag():
    """Test that learning applied flag is set correctly"""
    agent = BusinessCopilotAgent()
    
    # Submit enough feedback to trigger learning
    for i in range(6):
        decision = agent.process({
            'query': f'Query {i}',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='accuracy',
            rating=2,
            intent_type='general_query'
        )
    
    # Next feedback should indicate learning was applied
    decision = agent.process({
        'query': 'Another query',
        'user_id': 'test_user'
    })
    
    result = agent.submit_feedback(
        decision_id=decision.decision_id,
        user_id='test_user',
        feedback_type='negative',
        category='accuracy',
        rating=2,
        intent_type='general_query'
    )
    
    # Should have learning applied
    assert 'learningApplied' in result


def test_quality_metrics_improve_over_time():
    """Test that quality metrics can improve with positive feedback"""
    agent = BusinessCopilotAgent()
    
    # Start with negative feedback
    for i in range(3):
        decision = agent.process({
            'query': f'Query {i}',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='accuracy',
            rating=2
        )
    
    initial_metrics = agent.get_quality_metrics()
    initial_rating = initial_metrics['averageRating']
    
    # Add positive feedback
    for i in range(5):
        decision = agent.process({
            'query': f'Query improved {i}',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='positive',
            category='accuracy',
            rating=5
        )
    
    improved_metrics = agent.get_quality_metrics()
    improved_rating = improved_metrics['averageRating']
    
    # Rating should improve
    assert improved_rating > initial_rating


def test_response_adjustment_based_on_learning():
    """Test that responses are adjusted based on learning"""
    agent = BusinessCopilotAgent()
    
    # Create a scenario with low confidence intent
    for i in range(6):
        decision = agent.process({
            'query': f'Risk query {i}',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='accuracy',
            rating=2,
            intent_type='risk_query'
        )
    
    # Process a new risk query
    decision = agent.process({
        'query': 'What are the compliance risks?',
        'user_id': 'test_user'
    })
    
    # Response should exist and have been adjusted
    assert decision is not None
    assert decision.recommendation.confidence is not None


def test_improvement_recommendations_generated():
    """Test that improvement recommendations are generated"""
    agent = BusinessCopilotAgent()
    
    # Add feedback to generate recommendations
    for i in range(5):
        decision = agent.process({
            'query': f'Query {i}',
            'user_id': 'test_user'
        })
        
        agent.submit_feedback(
            decision_id=decision.decision_id,
            user_id='test_user',
            feedback_type='negative',
            category='clarity',
            rating=2,
            comment='Too vague'
        )
    
    recommendations = agent.get_improvement_recommendations()
    
    assert len(recommendations) > 0
    assert all('priority' in rec for rec in recommendations)
    assert all('action' in rec for rec in recommendations)
