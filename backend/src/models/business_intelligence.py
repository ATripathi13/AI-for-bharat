"""
Business Intelligence data model for RetailMind AI
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal
from enum import Enum


class EntityType(str, Enum):
    """Types of business entities"""
    PRICING = 'pricing'
    DEMAND = 'demand'
    INVENTORY = 'inventory'
    RISK = 'risk'


class Priority(str, Enum):
    """Priority levels for recommendations"""
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


@dataclass
class ActionRecommendation:
    """Action recommendation from business intelligence"""
    action: str
    priority: Priority
    expected_impact: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'action': self.action,
            'priority': self.priority.value,
            'expectedImpact': self.expected_impact
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActionRecommendation':
        """Create from dictionary"""
        return cls(
            action=data['action'],
            priority=Priority(data['priority']),
            expected_impact=data['expectedImpact']
        )


@dataclass
class Insights:
    """Insights from business intelligence analysis"""
    trend: str
    prediction: Any
    confidence: float
    timeframe: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'trend': self.trend,
            'prediction': self.prediction,
            'confidence': self.confidence,
            'timeframe': self.timeframe
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Insights':
        """Create from dictionary"""
        return cls(
            trend=data['trend'],
            prediction=data['prediction'],
            confidence=data['confidence'],
            timeframe=data['timeframe']
        )


@dataclass
class BusinessIntelligence:
    """Business intelligence entity"""
    entity_type: EntityType
    entity_id: str
    insights: Insights
    recommendations: List[ActionRecommendation]
    data_source: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'entityType': self.entity_type.value,
            'entityId': self.entity_id,
            'insights': self.insights.to_dict(),
            'recommendations': [rec.to_dict() for rec in self.recommendations],
            'dataSource': self.data_source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BusinessIntelligence':
        """Create from dictionary"""
        return cls(
            entity_type=EntityType(data['entityType']),
            entity_id=data['entityId'],
            insights=Insights.from_dict(data['insights']),
            recommendations=[ActionRecommendation.from_dict(rec) for rec in data['recommendations']],
            data_source=data['dataSource']
        )
