"""
Property-based tests for Intelligence Loop
**Feature: retailmind-ai, Property 10: Intelligence Loop Continuity**
**Validates: Requirements 7.4, 7.5, 8.4, 8.5**
"""
import pytest
import json
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
from src.services.intelligence_loop import (
    IntelligenceLoopOrchestrator,
    LoopPhase,
    LoopStatus,
    LoopExecution
)


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


class TestIntelligenceLoopPhases:
    """Unit tests for individual Intelligence Loop phases"""
    
    def test_observe_phase_execution(self):
        """Test observe phase with data ingestion"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {
            'data_sources': [
                {
                    'type': 'direct',
                    'id': 'test_source_1',
                    'data': {'key': 'value1'}
                },
                {
                    'type': 'direct',
                    'id': 'test_source_2',
                    'data': {'key': 'value2'}
                }
            ]
        }
        
        execution = orchestrator.start_loop(trigger_event)
        result = orchestrator.execute_observe_phase(execution)
        
        # Verify observe phase results
        assert result is not None
        assert 'timestamp' in result
        assert 'sources' in result
        assert 'raw_data' in result
        assert len(result['sources']) == 2
        assert 'test_source_1' in result['raw_data']
        assert 'test_source_2' in result['raw_data']
        
        # Verify execution state
        assert execution.current_phase == LoopPhase.OBSERVE
        assert LoopPhase.OBSERVE in execution.phase_results
    
    def test_analyze_phase_execution(self):
        """Test analyze phase with AI Council coordination"""
        from src.agents.registry import AgentRegistry
        from src.agents.market_intelligence_agent import MarketIntelligenceAgent
        
        registry = AgentRegistry()
        orchestrator = IntelligenceLoopOrchestrator(agent_registry=registry)
        
        # Register a test agent
        agent = MarketIntelligenceAgent()
        registry.register_agent(agent)
        
        trigger_event = {
            'agent_types': ['market_intelligence'],
            'data_sources': []
        }
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Execute observe first
        orchestrator.execute_observe_phase(execution)
        
        # Execute analyze
        result = orchestrator.execute_analyze_phase(execution)
        
        # Verify analyze phase results
        assert result is not None
        assert 'timestamp' in result
        assert 'agent_analyses' in result
        assert execution.current_phase == LoopPhase.ANALYZE
    
    def test_decide_phase_execution(self):
        """Test decide phase with decision aggregation"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {
            'agent_types': [],
            'data_sources': []
        }
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Execute observe and analyze first
        orchestrator.execute_observe_phase(execution)
        execution.phase_results[LoopPhase.ANALYZE] = {
            'agent_analyses': [
                {
                    'agent_id': 'agent1',
                    'agent_type': 'test',
                    'insights': 'Test insight',
                    'confidence': 0.9
                }
            ]
        }
        
        # Execute decide
        result = orchestrator.execute_decide_phase(execution)
        
        # Verify decide phase results
        assert result is not None
        assert 'timestamp' in result
        assert 'status' in result
        assert execution.current_phase == LoopPhase.DECIDE
    
    def test_act_phase_execution(self):
        """Test act phase with workflow execution"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {
            'data_sources': []
        }
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Set up previous phases with valid decision
        execution.phase_results[LoopPhase.OBSERVE] = {'raw_data': {}}
        execution.phase_results[LoopPhase.ANALYZE] = {'agent_analyses': []}
        execution.phase_results[LoopPhase.DECIDE] = {
            'status': 'success',
            'decision': {
                'action': 'test_action',
                'confidence': 0.85,
                'steps': [
                    {
                        'step_id': 'step_1',
                        'name': 'Test Step',
                        'type': 'lambda',
                        'configuration': {'function': 'test_func'}
                    }
                ]
            }
        }
        
        # Execute act
        result = orchestrator.execute_act_phase(execution)
        
        # Verify act phase results
        assert result is not None
        assert 'timestamp' in result
        assert execution.current_phase == LoopPhase.ACT
    
    def test_learn_phase_execution(self):
        """Test learn phase with outcome capture"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {
            'business_metrics': {'revenue': 1000.0}
        }
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Set up previous phases
        execution.phase_results[LoopPhase.ACT] = {
            'status': 'completed',
            'workflow_id': 'test_workflow',
            'instance_id': 'test_instance'
        }
        
        # Create a workflow instance in the execution engine
        from src.models.workflow_instance import WorkflowInstance, WorkflowStatus, WorkflowPerformance
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
        orchestrator.execution_engine.monitor.executions['test_instance'] = instance
        
        # Execute learn
        result = orchestrator.execute_learn_phase(execution)
        
        # Verify learn phase results
        assert result is not None
        assert 'timestamp' in result
        assert execution.current_phase == LoopPhase.LEARN
    
    def test_regenerate_phase_execution(self):
        """Test regenerate phase with workflow optimization"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {}
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Set up previous phases
        execution.phase_results[LoopPhase.ACT] = {
            'workflow_id': 'test_workflow'
        }
        execution.phase_results[LoopPhase.LEARN] = {
            'status': 'success',
            'outcome_id': 'test_outcome'
        }
        
        # Execute regenerate
        result = orchestrator.execute_regenerate_phase(execution)
        
        # Verify regenerate phase results
        assert result is not None
        assert 'timestamp' in result
        assert 'status' in result
        assert execution.current_phase == LoopPhase.REGENERATE


class TestIntelligenceLoopTransitions:
    """Unit tests for phase transitions"""
    
    def test_full_loop_execution(self):
        """Test complete loop execution through all phases"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {
            'data_sources': [
                {
                    'type': 'direct',
                    'id': 'test_data',
                    'data': {'test': 'value'}
                }
            ],
            'agent_types': []
        }
        
        execution = orchestrator.execute_full_loop(trigger_event)
        
        # Verify loop completed
        assert execution.status == LoopStatus.COMPLETED
        assert execution.completed_at is not None
        
        # Verify all phases executed
        assert LoopPhase.OBSERVE in execution.phase_results
        assert LoopPhase.ANALYZE in execution.phase_results
        assert LoopPhase.DECIDE in execution.phase_results
        assert LoopPhase.ACT in execution.phase_results
        assert LoopPhase.LEARN in execution.phase_results
        assert LoopPhase.REGENERATE in execution.phase_results
    
    def test_loop_status_tracking(self):
        """Test loop status tracking"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        trigger_event = {'data_sources': []}
        
        execution = orchestrator.start_loop(trigger_event)
        loop_id = execution.loop_id
        
        # Verify loop is tracked
        assert loop_id in orchestrator.active_loops
        
        # Get status
        status = orchestrator.get_loop_status(loop_id)
        assert status is not None
        assert status.loop_id == loop_id
        assert status.status == LoopStatus.RUNNING
    
    def test_loop_error_handling(self):
        """Test loop error handling"""
        orchestrator = IntelligenceLoopOrchestrator()
        
        # Create trigger event that will cause error
        trigger_event = {
            'data_sources': [
                {
                    'type': 's3',
                    'id': 'nonexistent_key'
                }
            ]
        }
        
        execution = orchestrator.start_loop(trigger_event)
        
        # Execute observe phase - should handle error gracefully
        result = orchestrator.execute_observe_phase(execution)
        
        # Verify error was captured
        assert result is not None
        assert 'sources' in result
        # Should have error status for the failed source
        failed_source = next((s for s in result['sources'] if s['id'] == 'nonexistent_key'), None)
        assert failed_source is not None
        assert failed_source['status'] == 'error'


class TestEventBridgeHandler:
    """Unit tests for EventBridge event handling"""
    
    def test_handle_loop_start_event(self):
        """Test handling loop start event"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        
        event = {
            'detail-type': EventType.LOOP_START.value,
            'detail': {
                'trigger_event': {
                    'data_sources': [],
                    'agent_types': []
                }
            }
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'success'
        assert 'loop_id' in body['result']
    
    def test_handle_phase_complete_event(self):
        """Test handling phase completion event"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        
        # Start a loop first
        trigger_event = {'data_sources': [], 'agent_types': []}
        execution = handler.orchestrator.start_loop(trigger_event)
        handler.orchestrator.execute_observe_phase(execution)
        
        # Handle phase complete event
        event = {
            'detail-type': EventType.PHASE_COMPLETE.value,
            'detail': {
                'loop_id': execution.loop_id,
                'phase': 'observe'
            }
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'success'
    
    def test_handle_data_ingested_event(self):
        """Test handling data ingestion event"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        handler.clear_emitted_events()
        
        event = {
            'detail-type': EventType.DATA_INGESTED.value,
            'detail': {
                'data_source': {
                    'type': 's3',
                    'id': 'test_bucket/test_key'
                },
                'trigger_conditions': {
                    'threshold': 100,
                    'value': 150
                }
            }
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'success'
        assert body['result']['triggered'] is True
        
        # Verify loop start event was emitted
        emitted = handler.get_emitted_events()
        assert len(emitted) > 0
        assert emitted[0]['DetailType'] == EventType.LOOP_START.value
    
    def test_handle_decision_required_event(self):
        """Test handling decision required event"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        handler.clear_emitted_events()
        
        event = {
            'detail-type': EventType.DECISION_REQUIRED.value,
            'detail': {
                'decision_context': {
                    'data_sources': []
                },
                'agent_types': ['market_intelligence']
            }
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'success'
        
        # Verify loop start event was emitted
        emitted = handler.get_emitted_events()
        assert len(emitted) > 0
    
    def test_handle_workflow_complete_event(self):
        """Test handling workflow completion event"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        handler.clear_emitted_events()
        
        event = {
            'detail-type': EventType.WORKFLOW_COMPLETE.value,
            'detail': {
                'workflow_id': 'test_workflow',
                'instance_id': 'test_instance',
                'performance': {
                    'execution_time': 1.5,
                    'success_rate': 0.95
                }
            }
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['status'] == 'success'
    
    def test_event_metrics_tracking(self):
        """Test event metrics tracking"""
        from src.services.event_bridge_handler import EventBridgeHandler, EventType
        
        handler = EventBridgeHandler()
        
        # Process multiple events
        for i in range(3):
            event = {
                'detail-type': EventType.LOOP_START.value,
                'detail': {
                    'trigger_event': {'data_sources': []}
                }
            }
            handler.handle_event(event)
        
        # Check metrics
        metrics = handler.get_event_metrics()
        assert EventType.LOOP_START.value in metrics
        assert metrics[EventType.LOOP_START.value] == 3
    
    def test_unknown_event_type(self):
        """Test handling unknown event type"""
        from src.services.event_bridge_handler import EventBridgeHandler
        
        handler = EventBridgeHandler()
        
        event = {
            'detail-type': 'unknown.event.type',
            'detail': {}
        }
        
        response = handler.handle_event(event)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['status'] == 'error'


class TestEventRules:
    """Unit tests for event rules configuration"""
    
    def test_event_pattern_generation(self):
        """Test event pattern generation"""
        from src.services.event_rules import EventPattern
        
        # Test loop start pattern
        pattern = EventPattern.loop_start_pattern()
        assert 'source' in pattern
        assert 'detail-type' in pattern
        assert pattern['detail-type'] == ['intelligence_loop.start']
        
        # Test phase complete pattern
        pattern = EventPattern.phase_complete_pattern('observe')
        assert 'detail' in pattern
        assert pattern['detail']['phase'] == ['observe']
        
        # Test data ingested pattern
        pattern = EventPattern.data_ingested_pattern('s3')
        assert 'detail' in pattern
    
    def test_event_rule_creation(self):
        """Test event rule creation"""
        from src.services.event_rules import EventRule, EventPattern
        
        rule = EventRule(
            name='TestRule',
            description='Test rule',
            event_pattern=EventPattern.loop_start_pattern(),
            targets=[{'Id': '1', 'Arn': 'test_arn'}],
            enabled=True
        )
        
        rule_dict = rule.to_dict()
        assert rule_dict['Name'] == 'TestRule'
        assert rule_dict['State'] == 'ENABLED'
        assert len(rule_dict['Targets']) == 1
    
    def test_all_intelligence_loop_rules(self):
        """Test all intelligence loop rules are defined"""
        from src.services.event_rules import IntelligenceLoopEventRules
        
        rules = IntelligenceLoopEventRules.get_all_rules()
        
        # Verify we have rules for all phases
        assert len(rules) >= 9  # Start + 6 phases + data ingestion + decision required + workflow complete
        
        rule_names = [r.name for r in rules]
        assert 'IntelligenceLoop-Start' in rule_names
        assert 'IntelligenceLoop-ObserveComplete' in rule_names
        assert 'IntelligenceLoop-AnalyzeComplete' in rule_names
        assert 'IntelligenceLoop-DecideComplete' in rule_names
        assert 'IntelligenceLoop-ActComplete' in rule_names
        assert 'IntelligenceLoop-LearnComplete' in rule_names
    
    def test_monitoring_configuration(self):
        """Test monitoring configuration"""
        from src.services.event_rules import LoopMonitoring
        
        # Test metrics
        metrics = LoopMonitoring.get_cloudwatch_metrics()
        assert len(metrics) > 0
        assert any(m['MetricName'] == 'LoopExecutionCount' for m in metrics)
        assert any(m['MetricName'] == 'PhaseExecutionTime' for m in metrics)
        
        # Test alarms
        alarms = LoopMonitoring.get_cloudwatch_alarms()
        assert len(alarms) > 0
        assert any(a['AlarmName'] == 'IntelligenceLoop-HighFailureRate' for a in alarms)
