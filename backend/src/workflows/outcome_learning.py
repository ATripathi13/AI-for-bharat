"""
Outcome Feedback and Learning System for RetailMind AI
Captures workflow outcomes and optimizes future executions
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from ..models.workflow_instance import WorkflowInstance, WorkflowPerformance
from .wdl_parser import WorkflowDefinition


class OutcomeType(str, Enum):
    """Types of workflow outcomes"""
    SUCCESS = 'success'
    FAILURE = 'failure'
    PARTIAL_SUCCESS = 'partial_success'
    TIMEOUT = 'timeout'
    ROLLED_BACK = 'rolled_back'


@dataclass
class WorkflowOutcome:
    """Represents the outcome of a workflow execution"""
    instance_id: str
    workflow_id: str
    outcome_type: OutcomeType
    performance: WorkflowPerformance
    timestamp: datetime
    metadata: Dict[str, Any]
    business_metrics: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'instanceId': self.instance_id,
            'workflowId': self.workflow_id,
            'outcomeType': self.outcome_type.value,
            'performance': self.performance.to_dict(),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'businessMetrics': self.business_metrics
        }


@dataclass
class OptimizationRecommendation:
    """Recommendation for workflow optimization"""
    workflow_id: str
    recommendation_type: str
    description: str
    expected_improvement: float
    confidence: float
    suggested_changes: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflowId': self.workflow_id,
            'recommendationType': self.recommendation_type,
            'description': self.description,
            'expectedImprovement': self.expected_improvement,
            'confidence': self.confidence,
            'suggestedChanges': self.suggested_changes
        }


class OutcomeCaptureService:
    """
    Captures and stores workflow execution outcomes
    """
    
    def __init__(self):
        """Initialize outcome capture service"""
        self.outcomes: Dict[str, List[WorkflowOutcome]] = {}
    
    def capture_outcome(
        self,
        instance: WorkflowInstance,
        outcome_type: OutcomeType,
        business_metrics: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowOutcome:
        """
        Capture workflow execution outcome
        
        Args:
            instance: WorkflowInstance that completed
            outcome_type: Type of outcome
            business_metrics: Business impact metrics
            metadata: Additional metadata
            
        Returns:
            WorkflowOutcome
        """
        outcome = WorkflowOutcome(
            instance_id=instance.instance_id,
            workflow_id=instance.workflow_id,
            outcome_type=outcome_type,
            performance=instance.performance,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            business_metrics=business_metrics or {}
        )
        
        # Store outcome
        if instance.workflow_id not in self.outcomes:
            self.outcomes[instance.workflow_id] = []
        self.outcomes[instance.workflow_id].append(outcome)
        
        return outcome
    
    def get_outcomes(
        self,
        workflow_id: str,
        limit: Optional[int] = None
    ) -> List[WorkflowOutcome]:
        """
        Get outcomes for a workflow
        
        Args:
            workflow_id: Workflow ID
            limit: Optional limit on number of outcomes
            
        Returns:
            List of WorkflowOutcome
        """
        outcomes = self.outcomes.get(workflow_id, [])
        if limit:
            return outcomes[-limit:]
        return outcomes
    
    def get_outcome_statistics(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get statistical summary of outcomes
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Dictionary of statistics
        """
        outcomes = self.outcomes.get(workflow_id, [])
        
        if not outcomes:
            return {
                'total_executions': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'avg_business_impact': 0.0
            }
        
        total = len(outcomes)
        successes = sum(1 for o in outcomes if o.outcome_type == OutcomeType.SUCCESS)
        
        avg_exec_time = sum(o.performance.execution_time for o in outcomes) / total
        avg_business_impact = sum(o.performance.business_impact for o in outcomes) / total
        
        return {
            'total_executions': total,
            'success_rate': successes / total,
            'avg_execution_time': avg_exec_time,
            'avg_business_impact': avg_business_impact,
            'outcome_distribution': self._get_outcome_distribution(outcomes)
        }
    
    def _get_outcome_distribution(
        self,
        outcomes: List[WorkflowOutcome]
    ) -> Dict[str, int]:
        """Get distribution of outcome types"""
        distribution = {}
        for outcome in outcomes:
            outcome_type = outcome.outcome_type.value
            distribution[outcome_type] = distribution.get(outcome_type, 0) + 1
        return distribution


class WorkflowPerformanceAnalyzer:
    """
    Analyzes workflow performance and identifies optimization opportunities
    """
    
    def __init__(self):
        """Initialize performance analyzer"""
        self.analysis_cache: Dict[str, Dict[str, Any]] = {}
    
    def analyze_performance(
        self,
        workflow_id: str,
        outcomes: List[WorkflowOutcome]
    ) -> Dict[str, Any]:
        """
        Analyze workflow performance
        
        Args:
            workflow_id: Workflow ID
            outcomes: List of outcomes to analyze
            
        Returns:
            Analysis results
        """
        if not outcomes:
            return {'error': 'No outcomes to analyze'}
        
        analysis = {
            'workflow_id': workflow_id,
            'sample_size': len(outcomes),
            'performance_metrics': self._analyze_metrics(outcomes),
            'bottlenecks': self._identify_bottlenecks(outcomes),
            'failure_patterns': self._analyze_failures(outcomes),
            'business_impact_trends': self._analyze_business_impact(outcomes)
        }
        
        self.analysis_cache[workflow_id] = analysis
        return analysis
    
    def _analyze_metrics(self, outcomes: List[WorkflowOutcome]) -> Dict[str, Any]:
        """Analyze performance metrics"""
        exec_times = [o.performance.execution_time for o in outcomes]
        success_rates = [o.performance.success_rate for o in outcomes]
        business_impacts = [o.performance.business_impact for o in outcomes]
        
        return {
            'execution_time': {
                'min': min(exec_times),
                'max': max(exec_times),
                'avg': sum(exec_times) / len(exec_times),
                'median': sorted(exec_times)[len(exec_times) // 2]
            },
            'success_rate': {
                'min': min(success_rates),
                'max': max(success_rates),
                'avg': sum(success_rates) / len(success_rates)
            },
            'business_impact': {
                'min': min(business_impacts),
                'max': max(business_impacts),
                'avg': sum(business_impacts) / len(business_impacts)
            }
        }
    
    def _identify_bottlenecks(self, outcomes: List[WorkflowOutcome]) -> List[str]:
        """Identify performance bottlenecks"""
        bottlenecks = []
        
        # Check for slow execution times
        avg_exec_time = sum(o.performance.execution_time for o in outcomes) / len(outcomes)
        if avg_exec_time > 30.0:
            bottlenecks.append('High average execution time')
        
        # Check for low success rates
        avg_success_rate = sum(o.performance.success_rate for o in outcomes) / len(outcomes)
        if avg_success_rate < 0.9:
            bottlenecks.append('Low success rate')
        
        # Check for low business impact
        avg_business_impact = sum(o.performance.business_impact for o in outcomes) / len(outcomes)
        if avg_business_impact < 0.5:
            bottlenecks.append('Low business impact')
        
        return bottlenecks
    
    def _analyze_failures(self, outcomes: List[WorkflowOutcome]) -> Dict[str, Any]:
        """Analyze failure patterns"""
        failures = [o for o in outcomes if o.outcome_type in [OutcomeType.FAILURE, OutcomeType.TIMEOUT]]
        
        if not failures:
            return {'failure_count': 0, 'failure_rate': 0.0}
        
        return {
            'failure_count': len(failures),
            'failure_rate': len(failures) / len(outcomes),
            'common_failure_types': self._get_failure_types(failures)
        }
    
    def _get_failure_types(self, failures: List[WorkflowOutcome]) -> Dict[str, int]:
        """Get distribution of failure types"""
        types = {}
        for failure in failures:
            failure_type = failure.outcome_type.value
            types[failure_type] = types.get(failure_type, 0) + 1
        return types
    
    def _analyze_business_impact(self, outcomes: List[WorkflowOutcome]) -> Dict[str, Any]:
        """Analyze business impact trends"""
        if len(outcomes) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend (simple linear)
        impacts = [o.performance.business_impact for o in outcomes]
        first_half_avg = sum(impacts[:len(impacts)//2]) / (len(impacts)//2)
        second_half_avg = sum(impacts[len(impacts)//2:]) / (len(impacts) - len(impacts)//2)
        
        if second_half_avg > first_half_avg * 1.1:
            trend = 'improving'
        elif second_half_avg < first_half_avg * 0.9:
            trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'first_half_avg': first_half_avg,
            'second_half_avg': second_half_avg,
            'change_percentage': ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        }


class WorkflowOptimizationService:
    """
    Generates optimization recommendations based on performance analysis
    """
    
    def __init__(self):
        """Initialize optimization service"""
        self.recommendations: Dict[str, List[OptimizationRecommendation]] = {}
    
    def generate_recommendations(
        self,
        workflow_id: str,
        analysis: Dict[str, Any]
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations
        
        Args:
            workflow_id: Workflow ID
            analysis: Performance analysis results
            
        Returns:
            List of OptimizationRecommendation
        """
        recommendations = []
        
        # Check for execution time optimization
        if 'High average execution time' in analysis.get('bottlenecks', []):
            recommendations.append(
                OptimizationRecommendation(
                    workflow_id=workflow_id,
                    recommendation_type='parallelization',
                    description='Add parallel execution for independent steps',
                    expected_improvement=0.3,
                    confidence=0.8,
                    suggested_changes={
                        'add_parallel_steps': True,
                        'target_steps': ['data_processing', 'validation']
                    }
                )
            )
        
        # Check for success rate optimization
        if 'Low success rate' in analysis.get('bottlenecks', []):
            recommendations.append(
                OptimizationRecommendation(
                    workflow_id=workflow_id,
                    recommendation_type='retry_logic',
                    description='Add retry logic for transient failures',
                    expected_improvement=0.15,
                    confidence=0.9,
                    suggested_changes={
                        'add_retry_config': True,
                        'max_attempts': 3,
                        'backoff_rate': 2.0
                    }
                )
            )
        
        # Check for business impact optimization
        if 'Low business impact' in analysis.get('bottlenecks', []):
            recommendations.append(
                OptimizationRecommendation(
                    workflow_id=workflow_id,
                    recommendation_type='threshold_adjustment',
                    description='Adjust decision thresholds for better outcomes',
                    expected_improvement=0.2,
                    confidence=0.7,
                    suggested_changes={
                        'adjust_thresholds': True,
                        'confidence_threshold': 0.85
                    }
                )
            )
        
        # Store recommendations
        self.recommendations[workflow_id] = recommendations
        return recommendations
    
    def get_recommendations(self, workflow_id: str) -> List[OptimizationRecommendation]:
        """Get recommendations for a workflow"""
        return self.recommendations.get(workflow_id, [])


class OutcomeLearningSystem:
    """
    Main outcome learning system
    Coordinates outcome capture, analysis, and optimization
    """
    
    def __init__(self):
        """Initialize outcome learning system"""
        self.capture_service = OutcomeCaptureService()
        self.analyzer = WorkflowPerformanceAnalyzer()
        self.optimizer = WorkflowOptimizationService()
    
    def record_outcome(
        self,
        instance: WorkflowInstance,
        outcome_type: OutcomeType,
        business_metrics: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WorkflowOutcome:
        """
        Record workflow outcome
        
        Args:
            instance: WorkflowInstance
            outcome_type: Type of outcome
            business_metrics: Business metrics
            metadata: Additional metadata
            
        Returns:
            WorkflowOutcome
        """
        return self.capture_service.capture_outcome(
            instance,
            outcome_type,
            business_metrics,
            metadata
        )
    
    def analyze_and_optimize(
        self,
        workflow_id: str,
        min_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze workflow performance and generate optimization recommendations
        
        Args:
            workflow_id: Workflow ID
            min_samples: Minimum number of outcomes required for analysis
            
        Returns:
            Dictionary containing analysis and recommendations
        """
        # Get outcomes
        outcomes = self.capture_service.get_outcomes(workflow_id)
        
        if len(outcomes) < min_samples:
            return {
                'status': 'insufficient_data',
                'message': f'Need at least {min_samples} outcomes, have {len(outcomes)}'
            }
        
        # Analyze performance
        analysis = self.analyzer.analyze_performance(workflow_id, outcomes)
        
        # Generate recommendations
        recommendations = self.optimizer.generate_recommendations(workflow_id, analysis)
        
        return {
            'status': 'success',
            'analysis': analysis,
            'recommendations': [r.to_dict() for r in recommendations],
            'statistics': self.capture_service.get_outcome_statistics(workflow_id)
        }
    
    def get_workflow_statistics(self, workflow_id: str) -> Dict[str, Any]:
        """Get statistics for a workflow"""
        return self.capture_service.get_outcome_statistics(workflow_id)
    
    def get_optimization_recommendations(
        self,
        workflow_id: str
    ) -> List[OptimizationRecommendation]:
        """Get optimization recommendations for a workflow"""
        return self.optimizer.get_recommendations(workflow_id)
