"""
Unit tests for Feedback Learning Service
Tests feedback collection and learning mechanisms
"""
import pytest
from src.services.feedback_learning import (
    FeedbackLearningService,
    FeedbackType,
    FeedbackCategory,
    UserFeedback,
    ResponseQualityMetrics,
    LearningInsight
)


def test_collect_feedback():
    """Test collecting user feedback"""
    service = FeedbackLearningService()
    
    feedback = service.collect_feedback(
        decision_id='test-decision-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5,
        comment='Great response!'
    )
    
    assert feedback.feedback_id is not None
    assert feedback.decision_id == 'test-decision-1'
    assert feedback.user_id == 'user-1'
    assert feedback.feedback_type == FeedbackType.POSITIVE
    assert feedback.rating == 5


def test_quality_metrics_update():
    """Test quality metrics are updated correctly"""
    service = FeedbackLearningService()
    
    # Add positive feedback
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5
    )
    
    metrics = service.get_quality_metrics()
    assert metrics.total_responses == 1
    assert metrics.positive_feedback == 1
    assert metrics.negative_feedback == 0
    
    # Add negative feedback
    service.collect_feedback(
        decision_id='test-2',
        user_id='user-1',
        feedback_type=FeedbackType.NEGATIVE,
        category=FeedbackCategory.RELEVANCE,
        rating=2
    )
    
    metrics = service.get_quality_metrics()
    assert metrics.total_responses == 2
    assert metrics.positive_feedback == 1
    assert metrics.negative_feedback == 1


def test_pattern_extraction():
    """Test learning pattern extraction from feedback"""
    service = FeedbackLearningService()
    
    # Submit feedback with pattern
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.NEGATIVE,
        category=FeedbackCategory.CLARITY,
        rating=2,
        comment='The response was too vague and unclear'
    )
    
    insights = service.get_learning_insights()
    assert len(insights) > 0
    
    # Check if pattern was detected
    vague_insights = [i for i in insights if i.pattern == 'too_vague']
    assert len(vague_insights) > 0
    assert vague_insights[0].frequency == 1


def test_correction_processing():
    """Test processing user corrections"""
    service = FeedbackLearningService()
    
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.CORRECTION,
        category=FeedbackCategory.ACCURACY,
        rating=3,
        comment='The data was incorrect',
        correction='The correct price should be $50, not $40'
    )
    
    insights = service.get_learning_insights()
    correction_insights = [i for i in insights if i.pattern == 'user_correction']
    assert len(correction_insights) > 0


def test_intent_performance_tracking():
    """Test tracking performance by intent type"""
    service = FeedbackLearningService()
    
    feedback = service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5
    )
    
    service.track_intent_performance('pricing_query', feedback)
    
    performance = service.get_intent_performance('pricing_query')
    assert performance['intentType'] == 'pricing_query'
    assert performance['metrics'] is not None
    assert performance['metrics']['totalResponses'] == 1


def test_low_performing_intents():
    """Test identification of low-performing intents"""
    service = FeedbackLearningService()
    
    # Add multiple negative feedbacks for an intent
    for i in range(5):
        feedback = service.collect_feedback(
            decision_id=f'test-{i}',
            user_id='user-1',
            feedback_type=FeedbackType.NEGATIVE,
            category=FeedbackCategory.ACCURACY,
            rating=2
        )
        service.track_intent_performance('inventory_query', feedback)
    
    low_performers = service.get_low_performing_intents(threshold=0.6)
    assert len(low_performers) > 0
    assert low_performers[0]['intentType'] == 'inventory_query'


def test_learning_adjustments():
    """Test applying learning adjustments"""
    service = FeedbackLearningService()
    
    # Add feedback to trigger adjustments
    for i in range(6):
        feedback_type = FeedbackType.NEGATIVE if i < 4 else FeedbackType.POSITIVE
        rating = 2 if i < 4 else 5
        
        feedback = service.collect_feedback(
            decision_id=f'test-{i}',
            user_id='user-1',
            feedback_type=feedback_type,
            category=FeedbackCategory.ACCURACY,
            rating=rating
        )
        service.track_intent_performance('forecast_query', feedback)
    
    adjustments = service.apply_learning_adjustments()
    
    assert 'intentAdjustments' in adjustments
    assert 'patternAdjustments' in adjustments
    assert 'confidenceAdjustments' in adjustments


def test_learning_summary():
    """Test getting comprehensive learning summary"""
    service = FeedbackLearningService()
    
    # Add some feedback
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5
    )
    
    summary = service.get_learning_summary()
    
    assert 'overallMetrics' in summary
    assert 'intentPerformance' in summary
    assert 'lowPerformingIntents' in summary
    assert 'topInsights' in summary
    assert 'appliedAdjustments' in summary


def test_satisfaction_rate_calculation():
    """Test satisfaction rate calculation"""
    metrics = ResponseQualityMetrics()
    
    # No feedback
    assert metrics.calculate_satisfaction_rate() == 0.0
    
    # All positive
    metrics.positive_feedback = 5
    metrics.negative_feedback = 0
    assert metrics.calculate_satisfaction_rate() == 1.0
    
    # Mixed
    metrics.positive_feedback = 7
    metrics.negative_feedback = 3
    assert metrics.calculate_satisfaction_rate() == 0.7


def test_improvement_recommendations():
    """Test getting improvement recommendations"""
    service = FeedbackLearningService()
    
    # Add low-rated feedback
    for i in range(5):
        service.collect_feedback(
            decision_id=f'test-{i}',
            user_id='user-1',
            feedback_type=FeedbackType.NEGATIVE,
            category=FeedbackCategory.ACCURACY,
            rating=2
        )
    
    recommendations = service.get_recommendations_for_improvement()
    assert len(recommendations) > 0
    
    # Should recommend improving overall quality
    quality_recs = [r for r in recommendations if r['area'] == 'overall_quality']
    assert len(quality_recs) > 0


def test_feedback_export():
    """Test exporting feedback data"""
    service = FeedbackLearningService()
    
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5
    )
    
    export_data = service.export_feedback_data()
    
    assert 'qualityMetrics' in export_data
    assert 'learningInsights' in export_data
    assert 'totalFeedbackItems' in export_data
    assert 'improvementRecommendations' in export_data


def test_multiple_pattern_detection():
    """Test detecting multiple patterns in feedback"""
    service = FeedbackLearningService()
    
    # Submit feedback with multiple patterns
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.NEGATIVE,
        category=FeedbackCategory.COMPLETENESS,
        rating=2,
        comment='Response was vague and missing important data'
    )
    
    insights = service.get_learning_insights()
    
    # Should detect both 'too_vague' and 'missing_data' patterns
    patterns = [i.pattern for i in insights]
    assert 'too_vague' in patterns
    assert 'missing_data' in patterns


def test_category_scores():
    """Test category-specific scoring"""
    service = FeedbackLearningService()
    
    # Add feedback for different categories
    service.collect_feedback(
        decision_id='test-1',
        user_id='user-1',
        feedback_type=FeedbackType.POSITIVE,
        category=FeedbackCategory.ACCURACY,
        rating=5
    )
    
    service.collect_feedback(
        decision_id='test-2',
        user_id='user-1',
        feedback_type=FeedbackType.NEGATIVE,
        category=FeedbackCategory.RELEVANCE,
        rating=2
    )
    
    metrics = service.get_quality_metrics()
    
    assert 'accuracy' in metrics.category_scores
    assert 'relevance' in metrics.category_scores
    assert metrics.category_scores['accuracy'] > metrics.category_scores['relevance']
