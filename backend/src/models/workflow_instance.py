"""
Workflow Instance data model for RetailMind AI
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Literal
from enum import Enum


class WorkflowStatus(str, Enum):
    """Workflow execution status"""
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    ROLLED_BACK = 'rolled_back'


class WorkflowStepType(str, Enum):
    """Types of workflow steps"""
    LAMBDA = 'lambda'
    DECISION = 'decision'
    PARALLEL = 'parallel'


@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    step_id: str
    type: WorkflowStepType
    configuration: Dict[str, Any]
    conditions: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'stepId': self.step_id,
            'type': self.type.value,
            'configuration': self.configuration,
            'conditions': self.conditions
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowStep':
        """Create from dictionary"""
        return cls(
            step_id=data['stepId'],
            type=WorkflowStepType(data['type']),
            configuration=data['configuration'],
            conditions=data['conditions']
        )


@dataclass
class WorkflowPerformance:
    """Performance metrics for a workflow"""
    execution_time: float
    success_rate: float
    business_impact: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'executionTime': self.execution_time,
            'successRate': self.success_rate,
            'businessImpact': self.business_impact
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowPerformance':
        """Create from dictionary"""
        return cls(
            execution_time=data['executionTime'],
            success_rate=data['successRate'],
            business_impact=data['businessImpact']
        )


@dataclass
class WorkflowInstance:
    """Instance of a workflow execution"""
    workflow_id: str
    instance_id: str
    status: WorkflowStatus
    steps: List[WorkflowStep]
    created_by: Literal['system', 'human']
    generated_by: str
    performance: WorkflowPerformance

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DynamoDB storage"""
        return {
            'workflowId': self.workflow_id,
            'instanceId': self.instance_id,
            'status': self.status.value,
            'steps': [step.to_dict() for step in self.steps],
            'createdBy': self.created_by,
            'generatedBy': self.generated_by,
            'performance': self.performance.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowInstance':
        """Create from dictionary"""
        return cls(
            workflow_id=data['workflowId'],
            instance_id=data['instanceId'],
            status=WorkflowStatus(data['status']),
            steps=[WorkflowStep.from_dict(step) for step in data['steps']],
            created_by=data['createdBy'],
            generated_by=data['generatedBy'],
            performance=WorkflowPerformance.from_dict(data['performance'])
        )
