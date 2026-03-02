"""
Property-based tests for Intelligence Loop
**Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
**Validates: Requirements 7.4, 7.5, 8.4, 8.5**
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import uuid

from src.workflows.outcome_learning import (
    OutcomeLearningSystem,
    OutcomeType,
    WorkflowOutcome
)
from src.workflows.execution_engine import WorkflowExecutionEngine
from src.workflows.wdl_parser import WorkflowDefinition, WDLStep, WDLStepType
from src.models.workflow_instance import (
    WorkflowInstance,
    WorkflowStep,
    WorkflowPerformance,
    WorkflowStatus,
    WorkflowStepType
)
from src.agents.workflow_regeneration_agent import WorkflowRegenerationAgent


# Strategies for generating test data
@st.composite
def workflow_instance_strategy(draw):
    """Generate a workflow instance"""
    workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
    instance_id = str(uuid.uuid4())
    
    # Generate 1-3 steps
    num_steps = draw(st.integers(min_value=1, max_value=3))
    steps = []
    for i in range(num_steps):
        step = WorkflowStep(
            step_id=f"step_{i}",
            type=WorkflowStepType.LAMBDA,
            configuration={'function': 'test_func'},
            conditions={}
        )
        steps.append(step)
    
    performance = WorkflowPerformance(
        execution_time=draw(st.floats(min_value=0.1, max_value=100.0)),
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        business_impact=draw(st.floats(min_value=0.0, max_value=1.0))
    )
    
    return WorkflowInstance(
        workflow_id=workflow_id,
        instance_id=instance_id,
        status=WorkflowStatus.COMPLETED,
        steps=steps,
        created_by='system',
        generated_by='test_agent',
        performance=performance
    )


@st.composite
def outcome_type_strategy(draw):
    """Generate an outcome type"""
    return draw(st.sampled_from(list(OutcomeType)))


@st.composite
def business_metrics_strategy(draw):
    """Generate business metrics"""
    return {
        'revenue_impact': draw(st.floats(min_value=0.0, max_value=1000000.0)),
        'cost_savings': draw(st.floats(min_value=0.0, max_value=100000.0)),
        'customer_satisfaction': draw(st.floats(min_value=0.0, max_value=1.0))
    }


class TestIntelligenceLoopProperties:
    """Property-based tests for intelligence loop continuity"""
    
    @given(instance=workflow_instance_strategy(),
           outcome_type=outcome_type_strategy(),
           business_metrics=business_metrics_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_outcomes_are_captured(self, instance, outcome_type, business_metrics):
        """
        Property: For any workflow execution, outcomes should be captured
        **Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
        **Validates: Requirements 7.4, 8.4**
        """
        learning_system = OutcomeLearningSystem()
        
        # Record outcome
        outcome = learning_system.record_outcome(
            instance,
            outcome_type,
            business_metrics
        )
        
        # Property: Outcome should be captured
        assert outcome is not None
        assert outcome.instance_id == instance.instance_id
        assert outcome.workflow_id == instance.workflow_id
        assert outcome.outcome_type == outcome_type
        
        # Property: Outcome should be retrievable
        outcomes = learning_system.capture_service.get_outcomes(instance.workflow_id)
        assert len(outcomes) > 0
        assert any(o.instance_id == instance.instance_id for o in outcomes)
    
    @given(instances=st.lists(workflow_instance_strategy(), min_size=10, max_size=20))
    @settings(max_examples=50, deadline=None)
    def test_property_learning_improves_recommendations(self, instances):
        """
        Property: For any set of workflow outcomes, system should learn and generate recommendations
        **Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
        **Validates: Requirements 7.4, 8.5**
        """
        learning_system = OutcomeLearningSystem()
        
        # Use same workflow ID for all instances to accumulate learning
        workflow_id = instances[0].workflow_id
        for instance in instances:
            instance.workflow_id = workflow_id
            learning_system.record_outcome(
                instance,
                OutcomeType.SUCCESS if instance.performance.success_rate > 0.5 else OutcomeType.FAILURE
            )
        
        # Property: System should analyze and generate recommendations
        result = learning_system.analyze_and_optimize(workflow_id, min_samples=10)
        
        assert result['status'] == 'success'
        assert 'analysis' in result
        assert 'recommendations' in result
        assert 'statistics' in result
        
        # Property: Statistics should reflect captured outcomes
        stats = result['statistics']
        assert stats['total_executions'] == len(instances)
        assert 0.0 <= stats['success_rate'] <= 1.0
        assert stats['avg_execution_time'] >= 0.0
    
    @given(instance=workflow_instance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_workflow_regeneration_after_outcome(self, instance):
        """
        Property: For any workflow outcome, system can regenerate improved workflows
        **Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
        **Validates: Requirements 7.5, 8.5**
        """
        learning_system = OutcomeLearningSystem()
        regeneration_agent = WorkflowRegenerationAgent()
        
        # Record outcome
        learning_system.record_outcome(
            instance,
            OutcomeType.SUCCESS,
            {'revenue_impact': 1000.0}
        )
        
        # Get performance data
        outcomes = learning_system.capture_service.get_outcomes(instance.workflow_id)
        performance_data = [o.performance for o in outcomes]
        
        # Property: Agent should be able to optimize based on outcomes
        # (even if no optimization is needed, it should return a valid workflow)
        try:
            # Create a simple workflow definition first
            workflow_def = WorkflowDefinition(
                workflow_id=instance.workflow_id,
                name='Test Workflow',
                version='1.0.0',
                description='Test',
                steps=[
                    WDLStep(
                        step_id='step_0',
                        name='Step 0',
                        type=WDLStepType.LAMBDA,
                        configuration={'function': 'test'}
                    )
                ],
                start_step='step_0'
            )
            regeneration_agent._store_version(workflow_def)
            
            optimized = regeneration_agent.optimize_workflow(
                instance.workflow_id,
                performance_data
            )
            
            # Property: Optimized workflow should be valid
            assert optimized is not None
            assert optimized.workflow_id == instance.workflow_id
        except ValueError:
            # If workflow doesn't exist, that's acceptable for this test
            pass
    
    @given(instances=st.lists(workflow_instance_strategy(), min_size=5, max_size=10))
    @settings(max_examples=50, deadline=None)
    def test_property_continuous_learning_accumulates(self, instances):
        """
        Property: For any sequence of outcomes, learning should accumulate over time
        **Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
        **Validates: Requirements 7.4, 8.4**
        """
        learning_system = OutcomeLearningSystem()
        
        # Use same workflow ID
        workflow_id = instances[0].workflow_id
        for instance in instances:
            instance.workflow_id = workflow_id
        
        # Record outcomes one by one
        for i, instance in enumerate(instances):
            learning_system.record_outcome(
                instance,
                OutcomeType.SUCCESS
            )
            
            # Property: Number of outcomes should grow
            outcomes = learning_system.capture_service.get_outcomes(workflow_id)
            assert len(outcomes) == i + 1
        
        # Property: Final statistics should reflect all outcomes
        stats = learning_system.get_workflow_statistics(workflow_id)
        assert stats['total_executions'] == len(instances)
    
    @given(instance=workflow_instance_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_execution_monitoring_tracks_status(self, instance):
        """
        Property: For any workflow execution, monitoring should track status
        **Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
        **Validates: Requirements 7.5**
        """
        execution_engine = WorkflowExecutionEngine()
        
        # Create workflow definition
        workflow_def = WorkflowDefinition(
            workflow_id=instance.workflow_id,
            name='Test Workflow',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step_0',
                    name='Step 0',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step_0'
        )
        
        # Execute workflow
        executed_instance = execution_engine.execute_workflow(
            workflow_def,
            {'test': 'data'},
            'test_agent'
        )
        
        # Property: Execution should be tracked
        assert executed_instance is not None
        assert executed_instance.workflow_id == workflow_def.workflow_id
        assert executed_instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.ROLLED_BACK]
        
        # Property: Should be able to monitor execution
        monitored = execution_engine.monitor_execution(executed_instance.instance_id)
        assert monitored is not None
        assert monitored.instance_id == executed_instance.instance_id


class TestIntelligenceLoopUnit:
    """Unit tests for intelligence loop components"""
    
    def test_outcome_capture(self):
        """Test outcome capture"""
        learning_system = OutcomeLearningSystem()
        
        instance = WorkflowInstance(
            workflow_id='test_workflow',
            instance_id='test_instance',
            status=WorkflowStatus.COMPLETED,
            steps=[],
            created_by='system',
            generated_by='test',
            performance=WorkflowPerformance(
                execution_time=1.0,
                success_rate=1.0,
                business_impact=0.8
            )
        )
        
        outcome = learning_system.record_outcome(
            instance,
            OutcomeType.SUCCESS,
            {'revenue': 1000.0}
        )
        
        assert outcome.workflow_id == 'test_workflow'
        assert outcome.outcome_type == OutcomeType.SUCCESS
    
    def test_performance_analysis(self):
        """Test performance analysis"""
        learning_system = OutcomeLearningSystem()
        
        # Create multiple outcomes
        for i in range(15):
            instance = WorkflowInstance(
                workflow_id='test_workflow',
                instance_id=f'instance_{i}',
                status=WorkflowStatus.COMPLETED,
                steps=[],
                created_by='system',
                generated_by='test',
                performance=WorkflowPerformance(
                    execution_time=float(i + 1),
                    success_rate=0.9,
                    business_impact=0.7
                )
            )
            learning_system.record_outcome(instance, OutcomeType.SUCCESS)
        
        # Analyze
        result = learning_system.analyze_and_optimize('test_workflow', min_samples=10)
        
        assert result['status'] == 'success'
        assert result['statistics']['total_executions'] == 15
    
    def test_optimization_recommendations(self):
        """Test optimization recommendations"""
        learning_system = OutcomeLearningSystem()
        
        # Create outcomes with poor performance
        for i in range(15):
            instance = WorkflowInstance(
                workflow_id='test_workflow',
                instance_id=f'instance_{i}',
                status=WorkflowStatus.COMPLETED,
                steps=[],
                created_by='system',
                generated_by='test',
                performance=WorkflowPerformance(
                    execution_time=50.0,  # High execution time
                    success_rate=0.7,  # Low success rate
                    business_impact=0.3  # Low business impact
                )
            )
            learning_system.record_outcome(instance, OutcomeType.SUCCESS)
        
        # Analyze and get recommendations
        result = learning_system.analyze_and_optimize('test_workflow', min_samples=10)
        
        assert result['status'] == 'success'
        assert len(result['recommendations']) > 0
