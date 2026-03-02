"""
Feedback Learning Service for RetailMind AI
Collects and processes user feedback to improve response quality
"""
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    """Types of feedback"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"


class FeedbackCategory(Enum):
    """Categories of feedback"""
    ACCURACY = "accuracy"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    ACTIONABILITY = "actionability"


@dataclass
class UserFeedback:
    """User feedback on a response"""
    feedback_id: str
    decision_id: str
    user_id: str
    feedback_type: FeedbackType
    category: FeedbackCategory
    rating: Optional[int] = None  # 1-5 scale
    comment: Optional[str] = None
    correction: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'feedbackId': self.feedback_id,
            'decisionId': self.decision_id,
            'userId': self.user_id,
            'feedbackType': self.feedback_type.value,
            'category': self.category.value,
            'rating': self.rating,
            'comment': self.comment,
            'correction': self.correction,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ResponseQualityMetrics:
    """Metrics for response quality"""
    total_responses: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    average_rating: float = 0.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    improvement_rate: float = 0.0
    
    def calculate_satisfaction_rate(self) -> float:
        """Calculate user satisfaction rate"""
        total_feedback = self.positive_feedback + self.negative_feedback
        if total_feedback == 0:
            return 0.0
        return self.positive_feedback / total_feedback
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'totalResponses': self.total_responses,
            'positiveFeedback': self.positive_feedback,
            'negativeFeedback': self.negative_feedback,
            'averageRating': self.average_rating,
            'categoryScores': self.category_scores,
            'improvementRate': self.improvement_rate,
            'satisfactionRate': self.calculate_satisfaction_rate()
        }


@dataclass
class LearningInsight:
    """Insight learned from feedback"""
    insight_id: str
    pattern: str
    frequency: int
    impact_score: float
    recommended_action: str
    examples: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'insightId': self.insight_id,
            'pattern': self.pattern,
            'frequency': self.frequency,
            'impactScore': self.impact_score,
            'recommendedAction': self.recommended_action,
            'examples': self.examples
        }


class FeedbackLearningService:
    """
    Service for collecting user feedback and improving response quality
    """
    
    def __init__(self):
        """Initialize feedback learning service"""
        self.feedback_store: Dict[str, List[UserFeedback]] = {}
        self.quality_metrics = ResponseQualityMetrics()
        self.learning_insights: List[LearningInsight] = []
        self.intent_performance: Dict[str, ResponseQualityMetrics] = {}
    
    def collect_feedback(
        self,
        decision_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        category: FeedbackCategory,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        correction: Optional[str] = None
    ) -> UserFeedback:
        """
        Collect feedback from user
        
        Args:
            decision_id: ID of the decision being rated
            user_id: ID of the user providing feedback
            feedback_type: Type of feedback
            category: Category of feedback
            rating: Optional rating (1-5)
            comment: Optional comment
            correction: Optional correction text
            
        Returns:
            UserFeedback object
        """
        import uuid
        
        feedback = UserFeedback(
            feedback_id=str(uuid.uuid4()),
            decision_id=decision_id,
            user_id=user_id,
            feedback_type=feedback_type,
            category=category,
            rating=rating,
            comment=comment,
            correction=correction
        )
        
        # Store feedback
        if decision_id not in self.feedback_store:
            self.feedback_store[decision_id] = []
        self.feedback_store[decision_id].append(feedback)
        
        # Update metrics
        self._update_metrics(feedback)
        
        # Analyze for learning
        self._analyze_feedback(feedback)
        
        return feedback
    
    def _update_metrics(self, feedback: UserFeedback):
        """Update quality metrics based on feedback"""
        self.quality_metrics.total_responses += 1
        
        if feedback.feedback_type == FeedbackType.POSITIVE:
            self.quality_metrics.positive_feedback += 1
        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            self.quality_metrics.negative_feedback += 1
        
        # Update average rating
        if feedback.rating is not None:
            total_ratings = (
                self.quality_metrics.positive_feedback +
                self.quality_metrics.negative_feedback
            )
            if total_ratings > 0:
                current_total = self.quality_metrics.average_rating * (total_ratings - 1)
                self.quality_metrics.average_rating = (
                    (current_total + feedback.rating) / total_ratings
                )
        
        # Update category scores
        category_name = feedback.category.value
        if category_name not in self.quality_metrics.category_scores:
            self.quality_metrics.category_scores[category_name] = 0.0
        
        # Simple moving average for category scores
        if feedback.rating is not None:
            current_score = self.quality_metrics.category_scores[category_name]
            self.quality_metrics.category_scores[category_name] = (
                (current_score * 0.9) + (feedback.rating / 5.0 * 0.1)
            )
    
    def _analyze_feedback(self, feedback: UserFeedback):
        """Analyze feedback for learning insights"""
        # Look for patterns in negative feedback
        if feedback.feedback_type == FeedbackType.NEGATIVE and feedback.comment:
            self._extract_learning_patterns(feedback)
        
        # Process corrections
        if feedback.correction:
            self._process_correction(feedback)
    
    def _extract_learning_patterns(self, feedback: UserFeedback):
        """Extract learning patterns from feedback"""
        comment_lower = feedback.comment.lower() if feedback.comment else ""
        
        # Common patterns to look for
        patterns = {
            'too_vague': ['vague', 'unclear', 'not specific', 'ambiguous'],
            'missing_data': ['missing', 'no data', 'incomplete', 'need more'],
            'wrong_intent': ['wrong', 'misunderstood', 'not what i asked'],
            'poor_recommendations': ['bad recommendation', 'not helpful', 'irrelevant'],
            'slow_response': ['slow', 'took too long', 'timeout']
        }
        
        for pattern_name, keywords in patterns.items():
            if any(keyword in comment_lower for keyword in keywords):
                self._record_pattern(pattern_name, feedback)
    
    def _record_pattern(self, pattern_name: str, feedback: UserFeedback):
        """Record a detected pattern"""
        import uuid
        
        # Find existing insight or create new one
        existing_insight = None
        for insight in self.learning_insights:
            if insight.pattern == pattern_name:
                existing_insight = insight
                break
        
        if existing_insight:
            existing_insight.frequency += 1
            if feedback.comment:
                existing_insight.examples.append(feedback.comment[:100])
        else:
            # Create new insight
            recommended_actions = {
                'too_vague': 'Provide more specific details and concrete examples',
                'missing_data': 'Ensure all relevant data sources are consulted',
                'wrong_intent': 'Improve intent recognition accuracy',
                'poor_recommendations': 'Enhance recommendation relevance scoring',
                'slow_response': 'Optimize query processing pipeline'
            }
            
            insight = LearningInsight(
                insight_id=str(uuid.uuid4()),
                pattern=pattern_name,
                frequency=1,
                impact_score=0.5,  # Will be updated based on frequency
                recommended_action=recommended_actions.get(
                    pattern_name,
                    'Review and improve response generation'
                ),
                examples=[feedback.comment[:100]] if feedback.comment else []
            )
            self.learning_insights.append(insight)
    
    def _process_correction(self, feedback: UserFeedback):
        """Process user correction to improve future responses"""
        if not feedback.correction:
            return
        
        # Store correction for future reference
        import uuid
        
        # Create a learning insight from the correction
        insight = LearningInsight(
            insight_id=str(uuid.uuid4()),
            pattern='user_correction',
            frequency=1,
            impact_score=0.8,  # Corrections have high impact
            recommended_action=f'Update response logic based on correction: {feedback.correction[:100]}',
            examples=[feedback.correction[:100]]
        )
        
        # Check if similar correction exists
        similar_found = False
        for existing_insight in self.learning_insights:
            if existing_insight.pattern == 'user_correction':
                # Check for similarity (simplified - would use NLP in production)
                if any(word in feedback.correction.lower() 
                       for example in existing_insight.examples 
                       for word in example.lower().split()[:5]):
                    existing_insight.frequency += 1
                    existing_insight.examples.append(feedback.correction[:100])
                    similar_found = True
                    break
        
        if not similar_found:
            self.learning_insights.append(insight)
    
    def get_quality_metrics(self) -> ResponseQualityMetrics:
        """Get current quality metrics"""
        return self.quality_metrics
    
    def get_learning_insights(
        self,
        min_frequency: int = 1,
        sort_by_impact: bool = True
    ) -> List[LearningInsight]:
        """
        Get learning insights
        
        Args:
            min_frequency: Minimum frequency to include
            sort_by_impact: Whether to sort by impact score
            
        Returns:
            List of learning insights
        """
        insights = [
            insight for insight in self.learning_insights
            if insight.frequency >= min_frequency
        ]
        
        if sort_by_impact:
            insights.sort(key=lambda x: x.impact_score * x.frequency, reverse=True)
        
        return insights
    
    def get_feedback_for_decision(
        self,
        decision_id: str
    ) -> List[UserFeedback]:
        """
        Get all feedback for a specific decision
        
        Args:
            decision_id: ID of the decision
            
        Returns:
            List of feedback items
        """
        return self.feedback_store.get(decision_id, [])
    
    def calculate_improvement_rate(
        self,
        time_window_days: int = 30
    ) -> float:
        """
        Calculate improvement rate over time
        
        Args:
            time_window_days: Time window to analyze
            
        Returns:
            Improvement rate (positive means improving)
        """
        # Simplified implementation - would use time-series analysis in production
        current_satisfaction = self.quality_metrics.calculate_satisfaction_rate()
        
        # Calculate trend (simplified)
        if self.quality_metrics.total_responses > 10:
            improvement = (current_satisfaction - 0.5) * 100  # Baseline of 50%
            self.quality_metrics.improvement_rate = improvement
            return improvement
        
        return 0.0
    
    def get_recommendations_for_improvement(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for improving response quality
        
        Returns:
            List of improvement recommendations
        """
        recommendations = []
        
        # Analyze quality metrics
        if self.quality_metrics.average_rating < 3.0:
            recommendations.append({
                'priority': 'high',
                'area': 'overall_quality',
                'issue': 'Low average rating',
                'action': 'Review response generation logic and data sources'
            })
        
        # Analyze category scores
        for category, score in self.quality_metrics.category_scores.items():
            if score < 0.6:
                recommendations.append({
                    'priority': 'medium',
                    'area': category,
                    'issue': f'Low score in {category}',
                    'action': f'Improve {category} of responses'
                })
        
        # Analyze learning insights
        high_impact_insights = [
            insight for insight in self.learning_insights
            if insight.frequency >= 3
        ]
        
        for insight in high_impact_insights:
            recommendations.append({
                'priority': 'high' if insight.frequency >= 5 else 'medium',
                'area': insight.pattern,
                'issue': f'Pattern detected {insight.frequency} times',
                'action': insight.recommended_action
            })
        
        return recommendations
    
    def export_feedback_data(self) -> Dict[str, Any]:
        """
        Export all feedback data for analysis
        
        Returns:
            Dictionary with all feedback data
        """
        return {
            'qualityMetrics': self.quality_metrics.to_dict(),
            'learningInsights': [
                insight.to_dict() for insight in self.learning_insights
            ],
            'totalFeedbackItems': sum(
                len(items) for items in self.feedback_store.values()
            ),
            'improvementRecommendations': self.get_recommendations_for_improvement()
        }
    
    def track_intent_performance(
        self,
        intent_type: str,
        feedback: UserFeedback
    ):
        """
        Track performance metrics for specific intent types
        
        Args:
            intent_type: Type of intent (e.g., 'pricing_query', 'inventory_query')
            feedback: User feedback for this intent
        """
        if intent_type not in self.intent_performance:
            self.intent_performance[intent_type] = ResponseQualityMetrics()
        
        metrics = self.intent_performance[intent_type]
        metrics.total_responses += 1
        
        if feedback.feedback_type == FeedbackType.POSITIVE:
            metrics.positive_feedback += 1
        elif feedback.feedback_type == FeedbackType.NEGATIVE:
            metrics.negative_feedback += 1
        
        # Update average rating for this intent
        if feedback.rating is not None:
            total_ratings = metrics.positive_feedback + metrics.negative_feedback
            if total_ratings > 0:
                current_total = metrics.average_rating * (total_ratings - 1)
                metrics.average_rating = (current_total + feedback.rating) / total_ratings
    
    def get_intent_performance(
        self,
        intent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get performance metrics for specific intent or all intents
        
        Args:
            intent_type: Optional specific intent type to query
            
        Returns:
            Dictionary with intent performance metrics
        """
        if intent_type:
            if intent_type in self.intent_performance:
                return {
                    'intentType': intent_type,
                    'metrics': self.intent_performance[intent_type].to_dict()
                }
            return {'intentType': intent_type, 'metrics': None}
        
        # Return all intent performance
        return {
            intent: metrics.to_dict()
            for intent, metrics in self.intent_performance.items()
        }
    
    def get_low_performing_intents(
        self,
        threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Identify intent types with low performance
        
        Args:
            threshold: Satisfaction rate threshold (0-1)
            
        Returns:
            List of low-performing intents with recommendations
        """
        low_performers = []
        
        for intent_type, metrics in self.intent_performance.items():
            satisfaction = metrics.calculate_satisfaction_rate()
            
            if satisfaction < threshold and metrics.total_responses >= 3:
                low_performers.append({
                    'intentType': intent_type,
                    'satisfactionRate': satisfaction,
                    'averageRating': metrics.average_rating,
                    'totalResponses': metrics.total_responses,
                    'recommendation': f'Improve response quality for {intent_type} queries'
                })
        
        # Sort by satisfaction rate (lowest first)
        low_performers.sort(key=lambda x: x['satisfactionRate'])
        
        return low_performers
    
    def apply_learning_adjustments(self) -> Dict[str, Any]:
        """
        Apply learning from feedback to improve future responses
        
        Returns:
            Dictionary with applied adjustments
        """
        adjustments = {
            'intentAdjustments': [],
            'patternAdjustments': [],
            'confidenceAdjustments': []
        }
        
        # Adjust based on intent performance
        for intent_type, metrics in self.intent_performance.items():
            if metrics.total_responses >= 5:
                satisfaction = metrics.calculate_satisfaction_rate()
                
                if satisfaction < 0.5:
                    adjustments['intentAdjustments'].append({
                        'intent': intent_type,
                        'action': 'reduce_confidence',
                        'reason': f'Low satisfaction rate: {satisfaction:.2%}'
                    })
                elif satisfaction > 0.8:
                    adjustments['intentAdjustments'].append({
                        'intent': intent_type,
                        'action': 'increase_confidence',
                        'reason': f'High satisfaction rate: {satisfaction:.2%}'
                    })
        
        # Adjust based on learning patterns
        high_frequency_patterns = [
            insight for insight in self.learning_insights
            if insight.frequency >= 3
        ]
        
        for insight in high_frequency_patterns:
            adjustments['patternAdjustments'].append({
                'pattern': insight.pattern,
                'frequency': insight.frequency,
                'action': insight.recommended_action,
                'priority': 'high' if insight.frequency >= 5 else 'medium'
            })
        
        # Calculate confidence adjustments based on category scores
        for category, score in self.quality_metrics.category_scores.items():
            if score < 0.5:
                adjustments['confidenceAdjustments'].append({
                    'category': category,
                    'currentScore': score,
                    'action': 'improve_category',
                    'recommendation': f'Focus on improving {category} in responses'
                })
        
        return adjustments
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive learning summary
        
        Returns:
            Dictionary with learning summary
        """
        return {
            'overallMetrics': self.quality_metrics.to_dict(),
            'intentPerformance': self.get_intent_performance(),
            'lowPerformingIntents': self.get_low_performing_intents(),
            'topInsights': [
                insight.to_dict() 
                for insight in sorted(
                    self.learning_insights,
                    key=lambda x: x.frequency * x.impact_score,
                    reverse=True
                )[:5]
            ],
            'appliedAdjustments': self.apply_learning_adjustments(),
            'improvementRate': self.calculate_improvement_rate()
        }
