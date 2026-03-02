"""
EventBridge Event Rules Configuration
Defines event patterns and rules for Intelligence Loop orchestration
"""
from typing import Dict, Any, List
from enum import Enum


class EventPattern:
    """EventBridge event pattern definitions"""
    
    @staticmethod
    def loop_start_pattern() -> Dict[str, Any]:
        """Pattern for loop start events"""
        return {
            "source": ["retailmind.intelligence-loop"],
            "detail-type": ["intelligence_loop.start"]
        }
    
    @staticmethod
    def phase_complete_pattern(phase: str = None) -> Dict[str, Any]:
        """Pattern for phase completion events"""
        pattern = {
            "source": ["retailmind.intelligence-loop"],
            "detail-type": ["intelligence_loop.phase_complete"]
        }
        
        if phase:
            pattern["detail"] = {
                "phase": [phase]
            }
        
        return pattern
    
    @staticmethod
    def data_ingested_pattern(source_type: str = None) -> Dict[str, Any]:
        """Pattern for data ingestion events"""
        pattern = {
            "source": ["retailmind.data"],
            "detail-type": ["data.ingested"]
        }
        
        if source_type:
            pattern["detail"] = {
                "data_source": {
                    "type": [source_type]
                }
            }
        
        return pattern
    
    @staticmethod
    def decision_required_pattern() -> Dict[str, Any]:
        """Pattern for decision required events"""
        return {
            "source": ["retailmind.agents"],
            "detail-type": ["decision.required"]
        }
    
    @staticmethod
    def workflow_complete_pattern() -> Dict[str, Any]:
        """Pattern for workflow completion events"""
        return {
            "source": ["retailmind.workflows"],
            "detail-type": ["workflow.complete"]
        }


class EventRule:
    """EventBridge rule definition"""
    
    def __init__(
        self,
        name: str,
        description: str,
        event_pattern: Dict[str, Any],
        targets: List[Dict[str, Any]],
        enabled: bool = True
    ):
        self.name = name
        self.description = description
        self.event_pattern = event_pattern
        self.targets = targets
        self.enabled = enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AWS API"""
        return {
            'Name': self.name,
            'Description': self.description,
            'EventPattern': self.event_pattern,
            'State': 'ENABLED' if self.enabled else 'DISABLED',
            'Targets': self.targets
        }


class IntelligenceLoopEventRules:
    """
    Defines all EventBridge rules for Intelligence Loop orchestration
    """
    
    @staticmethod
    def get_all_rules() -> List[EventRule]:
        """Get all event rules for Intelligence Loop"""
        return [
            IntelligenceLoopEventRules.loop_start_rule(),
            IntelligenceLoopEventRules.observe_complete_rule(),
            IntelligenceLoopEventRules.analyze_complete_rule(),
            IntelligenceLoopEventRules.decide_complete_rule(),
            IntelligenceLoopEventRules.act_complete_rule(),
            IntelligenceLoopEventRules.learn_complete_rule(),
            IntelligenceLoopEventRules.data_ingestion_rule(),
            IntelligenceLoopEventRules.decision_required_rule(),
            IntelligenceLoopEventRules.workflow_complete_rule(),
        ]
    
    @staticmethod
    def loop_start_rule() -> EventRule:
        """Rule for starting intelligence loop"""
        return EventRule(
            name='IntelligenceLoop-Start',
            description='Triggers intelligence loop start handler',
            event_pattern=EventPattern.loop_start_pattern(),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def observe_complete_rule() -> EventRule:
        """Rule for observe phase completion"""
        return EventRule(
            name='IntelligenceLoop-ObserveComplete',
            description='Triggers analyze phase after observe completes',
            event_pattern=EventPattern.phase_complete_pattern('observe'),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def analyze_complete_rule() -> EventRule:
        """Rule for analyze phase completion"""
        return EventRule(
            name='IntelligenceLoop-AnalyzeComplete',
            description='Triggers decide phase after analyze completes',
            event_pattern=EventPattern.phase_complete_pattern('analyze'),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def decide_complete_rule() -> EventRule:
        """Rule for decide phase completion"""
        return EventRule(
            name='IntelligenceLoop-DecideComplete',
            description='Triggers act phase after decide completes',
            event_pattern=EventPattern.phase_complete_pattern('decide'),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def act_complete_rule() -> EventRule:
        """Rule for act phase completion"""
        return EventRule(
            name='IntelligenceLoop-ActComplete',
            description='Triggers learn phase after act completes',
            event_pattern=EventPattern.phase_complete_pattern('act'),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def learn_complete_rule() -> EventRule:
        """Rule for learn phase completion"""
        return EventRule(
            name='IntelligenceLoop-LearnComplete',
            description='Triggers regenerate phase after learn completes',
            event_pattern=EventPattern.phase_complete_pattern('learn'),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def data_ingestion_rule() -> EventRule:
        """Rule for data ingestion events"""
        return EventRule(
            name='IntelligenceLoop-DataIngestion',
            description='Triggers intelligence loop on data ingestion',
            event_pattern=EventPattern.data_ingested_pattern(),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def decision_required_rule() -> EventRule:
        """Rule for decision required events"""
        return EventRule(
            name='IntelligenceLoop-DecisionRequired',
            description='Triggers intelligence loop when decision is required',
            event_pattern=EventPattern.decision_required_pattern(),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )
    
    @staticmethod
    def workflow_complete_rule() -> EventRule:
        """Rule for workflow completion events"""
        return EventRule(
            name='IntelligenceLoop-WorkflowComplete',
            description='Triggers learning on workflow completion',
            event_pattern=EventPattern.workflow_complete_pattern(),
            targets=[
                {
                    'Id': '1',
                    'Arn': 'arn:aws:lambda:region:account:function:intelligence-loop-handler',
                    'RoleArn': 'arn:aws:iam::account:role/EventBridgeInvokeRole'
                }
            ]
        )


class LoopMonitoring:
    """
    Monitoring configuration for Intelligence Loop execution
    """
    
    @staticmethod
    def get_cloudwatch_metrics() -> List[Dict[str, Any]]:
        """Get CloudWatch metric definitions"""
        return [
            {
                'MetricName': 'LoopExecutionCount',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Dimensions': [
                    {'Name': 'LoopType', 'Value': 'Full'}
                ],
                'Unit': 'Count'
            },
            {
                'MetricName': 'PhaseExecutionTime',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Dimensions': [
                    {'Name': 'Phase', 'Value': 'Observe'},
                    {'Name': 'Phase', 'Value': 'Analyze'},
                    {'Name': 'Phase', 'Value': 'Decide'},
                    {'Name': 'Phase', 'Value': 'Act'},
                    {'Name': 'Phase', 'Value': 'Learn'},
                    {'Name': 'Phase', 'Value': 'Regenerate'}
                ],
                'Unit': 'Milliseconds'
            },
            {
                'MetricName': 'LoopSuccessRate',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Unit': 'Percent'
            },
            {
                'MetricName': 'EventProcessingLatency',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Dimensions': [
                    {'Name': 'EventType', 'Value': 'All'}
                ],
                'Unit': 'Milliseconds'
            }
        ]
    
    @staticmethod
    def get_cloudwatch_alarms() -> List[Dict[str, Any]]:
        """Get CloudWatch alarm definitions"""
        return [
            {
                'AlarmName': 'IntelligenceLoop-HighFailureRate',
                'AlarmDescription': 'Alert when loop failure rate exceeds threshold',
                'MetricName': 'LoopSuccessRate',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 2,
                'Threshold': 80.0,
                'ComparisonOperator': 'LessThanThreshold'
            },
            {
                'AlarmName': 'IntelligenceLoop-HighLatency',
                'AlarmDescription': 'Alert when phase execution time is too high',
                'MetricName': 'PhaseExecutionTime',
                'Namespace': 'RetailMind/IntelligenceLoop',
                'Statistic': 'Average',
                'Period': 300,
                'EvaluationPeriods': 2,
                'Threshold': 30000.0,  # 30 seconds
                'ComparisonOperator': 'GreaterThanThreshold'
            }
        ]
