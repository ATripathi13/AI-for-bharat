"""
Explainability Service for RetailMind AI
Provides decision explainability and reasoning trace generation
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ReasoningStep:
    """A single step in the reasoning process"""
    step_number: int
    description: str
    data_used: List[str]
    confidence_impact: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'stepNumber': self.step_number,
            'description': self.description,
            'dataUsed': self.data_used,
            'confidenceImpact': self.confidence_impact,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class ExplanationTrace:
    """Complete explanation trace for a decision"""
    decision_id: str
    reasoning_steps: List[ReasoningStep]
    data_sources: List[str]
    contributing_factors: Dict[str, float]
    final_confidence: float
    explanation_summary: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'decisionId': self.decision_id,
            'reasoningSteps': [step.to_dict() for step in self.reasoning_steps],
            'dataSources': self.data_sources,
            'contributingFactors': self.contributing_factors,
            'finalConfidence': self.final_confidence,
            'explanationSummary': self.explanation_summary
        }


class ExplainabilityService:
    """
    Service for generating explanations and reasoning traces
    for AI decisions
    """
    
    def __init__(self):
        """Initialize explainability service"""
        self.explanation_cache: Dict[str, ExplanationTrace] = {}
    
    def create_reasoning_trace(
        self,
        decision_id: str,
        steps: List[str],
        data_sources: List[str],
        confidence: float
    ) -> ExplanationTrace:
        """
        Create a reasoning trace for a decision
        
        Args:
            decision_id: ID of the decision
            steps: List of reasoning step descriptions
            data_sources: List of data sources used
            confidence: Final confidence level
            
        Returns:
            ExplanationTrace object
        """
        reasoning_steps = []
        for i, step_desc in enumerate(steps, 1):
            step = ReasoningStep(
                step_number=i,
                description=step_desc,
                data_used=data_sources,
                confidence_impact=confidence / len(steps),
                timestamp=datetime.utcnow()
            )
            reasoning_steps.append(step)
        
        # Generate contributing factors (simplified)
        contributing_factors = self._analyze_contributing_factors(
            reasoning_steps,
            data_sources
        )
        
        # Generate summary
        summary = self._generate_summary(reasoning_steps, confidence)
        
        trace = ExplanationTrace(
            decision_id=decision_id,
            reasoning_steps=reasoning_steps,
            data_sources=data_sources,
            contributing_factors=contributing_factors,
            final_confidence=confidence,
            explanation_summary=summary
        )
        
        # Cache the trace
        self.explanation_cache[decision_id] = trace
        
        return trace
    
    def _analyze_contributing_factors(
        self,
        steps: List[ReasoningStep],
        data_sources: List[str]
    ) -> Dict[str, float]:
        """
        Analyze contributing factors to the decision
        
        Args:
            steps: List of reasoning steps
            data_sources: List of data sources
            
        Returns:
            Dictionary mapping factor names to importance scores
        """
        factors = {}
        
        # Analyze data sources
        for source in data_sources:
            factors[source] = 1.0 / len(data_sources)
        
        # Analyze reasoning steps
        for step in steps:
            if 'market' in step.description.lower():
                factors['market_conditions'] = factors.get('market_conditions', 0) + 0.2
            if 'demand' in step.description.lower():
                factors['demand_patterns'] = factors.get('demand_patterns', 0) + 0.2
            if 'price' in step.description.lower() or 'pricing' in step.description.lower():
                factors['pricing_strategy'] = factors.get('pricing_strategy', 0) + 0.2
            if 'inventory' in step.description.lower():
                factors['inventory_levels'] = factors.get('inventory_levels', 0) + 0.2
            if 'risk' in step.description.lower():
                factors['risk_assessment'] = factors.get('risk_assessment', 0) + 0.2
        
        # Normalize factors
        total = sum(factors.values())
        if total > 0:
            factors = {k: v / total for k, v in factors.items()}
        
        return factors
    
    def _generate_summary(
        self,
        steps: List[ReasoningStep],
        confidence: float
    ) -> str:
        """
        Generate a human-readable summary of the reasoning
        
        Args:
            steps: List of reasoning steps
            confidence: Final confidence level
            
        Returns:
            Summary string
        """
        num_steps = len(steps)
        confidence_level = "high" if confidence > 0.8 else "medium" if confidence > 0.6 else "low"
        
        summary = f"This decision was made through {num_steps} reasoning steps with {confidence_level} confidence ({confidence:.2%}). "
        
        if num_steps > 0:
            summary += f"The process began with: {steps[0].description}. "
        
        if num_steps > 2:
            summary += f"Key intermediate steps included analyzing multiple data sources and coordinating with relevant agents. "
        
        if num_steps > 0:
            summary += f"The final step was: {steps[-1].description}."
        
        return summary
    
    def get_explanation(self, decision_id: str) -> Optional[ExplanationTrace]:
        """
        Get explanation trace for a decision
        
        Args:
            decision_id: ID of the decision
            
        Returns:
            ExplanationTrace if found, None otherwise
        """
        return self.explanation_cache.get(decision_id)
    
    def generate_action_recommendations(
        self,
        intent_type: str,
        entities: Dict[str, Any],
        data_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate action-oriented recommendations
        
        Args:
            intent_type: Type of query intent
            entities: Extracted entities from query
            data_insights: Insights from data analysis
            
        Returns:
            List of actionable recommendations
        """
        recommendations = []
        
        if intent_type == 'pricing_query':
            recommendations.extend(self._pricing_recommendations(entities, data_insights))
        elif intent_type == 'inventory_query':
            recommendations.extend(self._inventory_recommendations(entities, data_insights))
        elif intent_type == 'forecast_query':
            recommendations.extend(self._forecast_recommendations(entities, data_insights))
        elif intent_type == 'market_query':
            recommendations.extend(self._market_recommendations(entities, data_insights))
        elif intent_type == 'risk_query':
            recommendations.extend(self._risk_recommendations(entities, data_insights))
        
        return recommendations
    
    def _pricing_recommendations(
        self,
        entities: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate pricing-specific recommendations"""
        return [
            {
                'action': 'review_competitive_pricing',
                'description': 'Review competitor pricing and adjust strategy',
                'priority': 'high',
                'expected_impact': 'Maintain market competitiveness',
                'next_steps': [
                    'Analyze competitor price changes',
                    'Calculate optimal price points',
                    'Implement gradual price adjustments'
                ]
            },
            {
                'action': 'optimize_margins',
                'description': 'Optimize pricing for target margins',
                'priority': 'medium',
                'expected_impact': 'Improve profitability',
                'next_steps': [
                    'Review current margin performance',
                    'Identify low-margin products',
                    'Adjust pricing strategy'
                ]
            }
        ]
    
    def _inventory_recommendations(
        self,
        entities: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate inventory-specific recommendations"""
        return [
            {
                'action': 'rebalance_inventory',
                'description': 'Rebalance stock levels across regions',
                'priority': 'high',
                'expected_impact': 'Reduce stockouts and overstock',
                'next_steps': [
                    'Identify overstock locations',
                    'Identify stockout risks',
                    'Initiate stock transfers'
                ]
            },
            {
                'action': 'adjust_reorder_points',
                'description': 'Update reorder points based on demand',
                'priority': 'medium',
                'expected_impact': 'Optimize inventory costs',
                'next_steps': [
                    'Review demand forecasts',
                    'Calculate optimal reorder quantities',
                    'Update inventory policies'
                ]
            }
        ]
    
    def _forecast_recommendations(
        self,
        entities: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate forecast-specific recommendations"""
        return [
            {
                'action': 'prepare_for_demand_surge',
                'description': 'Prepare inventory for predicted demand increase',
                'priority': 'high',
                'expected_impact': 'Prevent stockouts during peak demand',
                'next_steps': [
                    'Review forecast accuracy',
                    'Increase safety stock',
                    'Coordinate with suppliers'
                ]
            }
        ]
    
    def _market_recommendations(
        self,
        entities: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate market intelligence recommendations"""
        return [
            {
                'action': 'monitor_market_trends',
                'description': 'Continue monitoring market and competitor activity',
                'priority': 'medium',
                'expected_impact': 'Stay ahead of market changes',
                'next_steps': [
                    'Set up automated alerts',
                    'Review weekly trend reports',
                    'Adjust strategy as needed'
                ]
            }
        ]
    
    def _risk_recommendations(
        self,
        entities: Dict[str, Any],
        insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate risk and compliance recommendations"""
        return [
            {
                'action': 'address_compliance_issues',
                'description': 'Address identified compliance violations',
                'priority': 'critical',
                'expected_impact': 'Ensure regulatory compliance',
                'next_steps': [
                    'Review compliance violations',
                    'Implement corrective actions',
                    'Document remediation'
                ]
            },
            {
                'action': 'review_supplier_risks',
                'description': 'Review and mitigate supplier risks',
                'priority': 'high',
                'expected_impact': 'Reduce supply chain disruptions',
                'next_steps': [
                    'Analyze supplier risk scores',
                    'Diversify supplier base',
                    'Implement monitoring'
                ]
            }
        ]
    
    def format_explanation_for_user(
        self,
        trace: ExplanationTrace,
        include_technical_details: bool = False
    ) -> str:
        """
        Format explanation trace for user display
        
        Args:
            trace: Explanation trace to format
            include_technical_details: Whether to include technical details
            
        Returns:
            Formatted explanation string
        """
        output = []
        
        output.append("=== Decision Explanation ===\n")
        output.append(f"Summary: {trace.explanation_summary}\n")
        
        output.append("\nReasoning Process:")
        for step in trace.reasoning_steps:
            output.append(f"  {step.step_number}. {step.description}")
        
        output.append("\nData Sources Used:")
        for source in trace.data_sources:
            output.append(f"  - {source}")
        
        output.append("\nKey Contributing Factors:")
        for factor, importance in sorted(
            trace.contributing_factors.items(),
            key=lambda x: x[1],
            reverse=True
        ):
            output.append(f"  - {factor}: {importance:.1%}")
        
        if include_technical_details:
            output.append(f"\nFinal Confidence: {trace.final_confidence:.2%}")
            output.append(f"Decision ID: {trace.decision_id}")
        
        return "\n".join(output)
