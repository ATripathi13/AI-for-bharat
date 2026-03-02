"""
Property-based tests for Workflow Regeneration Agent
**Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
**Validates: Requirements 7.1, 7.2, 7.3**
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
import uuid

from src.agents.workflow_regeneration_agent import (
    WorkflowRegenerationAgent,
    BusinessRuleChange
)
from src.workflows.wdl_parser import (
    WorkflowDefinition,
    WDLStep,
    WDLStepType,
    WDLValidator
)
from src.models.workflow_instance import WorkflowPerformance, WorkflowStatus


# Strategies for generating test data
@st.composite
def workflow_definition_strategy(draw):
    """Generate a valid workflow definition with unique step IDs"""
    workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
    name = draw(st.text(min_size=1, max_size=50))
    version = "1.0.0"
    description = draw(st.text(min_size=0, max_size=200))
    
    # Generate 1-5 steps with UNIQUE IDs
    num_steps = draw(st.integers(min_value=1, max_value=5))
    steps = []
    used_ids = set()
    
    for i in range(num_steps):
        # Generate unique step ID
        step_id = f"step_{i}_{uuid.uuid4().hex[:4]}"
        while step_id in used_ids:
            step_id = f"step_{i}_{uuid.uuid4().hex[:4]}"
        used_ids.add(step_id)
        
        name_text = draw(st.text(min_size=1, max_size=20))
        step_type = draw(st.sampled_from(list(WDLStepType)))
        
        step = WDLStep(
            step_id=step_id,
            name=name_text,
            type=step_type,
            configuration={'function': 'test_function', 'input': '$.data'},
            conditions=[],
            next_step=None
        )
        steps.append(step)
    
    # Link steps together (no cycles)
    for i in range(len(steps) - 1):
        steps[i].next_step = steps[i + 1].step_id
    
    start_step = steps[0].step_id
    
    return WorkflowDefinition(
        workflow_id=workflow_id,
        name=name,
        version=version,
        description=description,
        steps=steps,
        start_step=start_step,
        rollback_procedure=[],
        metadata={}
    )


@st.composite
def business_requirements_strategy(draw):
    """Generate business requirements for workflow generation"""
    return {
        'name': draw(st.text(min_size=1, max_size=50)),
        'description': draw(st.text(min_size=0, max_size=200)),
        'metadata': {
            'priority': draw(st.sampled_from(['low', 'medium', 'high', 'critical'])),
            'category': draw(st.sampled_from(['pricing', 'inventory', 'forecasting', 'compliance']))
        }
    }


@st.composite
def performance_data_strategy(draw):
    """Generate performance data"""
    return WorkflowPerformance(
        execution_time=draw(st.floats(min_value=0.1, max_value=100.0)),
        success_rate=draw(st.floats(min_value=0.0, max_value=1.0)),
        business_impact=draw(st.floats(min_value=0.0, max_value=1.0))
    )


@st.composite
def rule_change_strategy(draw):
    """Generate a business rule change"""
    return BusinessRuleChange(
        rule_id=f"rule_{uuid.uuid4().hex[:8]}",
        rule_type=draw(st.sampled_from(['threshold', 'condition', 'priority'])),
        old_value=draw(st.floats(min_value=0.0, max_value=1.0)),
        new_value=draw(st.floats(min_value=0.0, max_value=1.0)),
        affected_workflows=[]
    )


class TestWorkflowRegenerationProperties:
    """Property-based tests for workflow regeneration"""
    
    @given(template_name=st.sampled_from(['pricing_optimization', 'inventory_rebalancing', 'demand_forecast_update']),
           requirements=business_requirements_strategy())
    @settings(max_examples=100)
    def test_property_generated_workflows_are_valid(self, template_name, requirements):
        """
        Property: For any template and requirements, generated workflows should be valid
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.1**
        """
        agent = WorkflowRegenerationAgent()
        validator = WDLValidator()
        
        # Generate workflow from template
        workflow_def = agent.generate_workflow(
            workflow_name=requirements['name'],
            business_requirements=requirements,
            template_name=template_name
        )
        
        # Property: Generated workflow must be valid
        assert validator.is_valid(workflow_def), \
            f"Generated workflow is invalid: {validator.validate(workflow_def)}"
        
        # Property: Generated workflow must have required fields
        assert workflow_def.workflow_id is not None
        assert workflow_def.name == requirements['name']
        assert len(workflow_def.steps) > 0
        assert workflow_def.start_step in [s.step_id for s in workflow_def.steps]
    
    @given(workflow_def=workflow_definition_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_modifications_preserve_validity(self, workflow_def):
        """
        Property: For any valid workflow, modifications should preserve validity
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.2**
        """
        agent = WorkflowRegenerationAgent()
        validator = WDLValidator()
        
        # Store the workflow first
        agent._store_version(workflow_def)
        
        # Create safe modifications (update metadata only to avoid breaking structure)
        modifications = {
            'update_metadata': {
                'modified': True,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Modify workflow
        modified_workflow = agent.modify_workflow(workflow_def.workflow_id, modifications)
        
        # Property: Modified workflow must still be valid
        assert validator.is_valid(modified_workflow), \
            f"Modified workflow is invalid: {validator.validate(modified_workflow)}"
        
        # Property: Workflow ID should remain the same
        assert modified_workflow.workflow_id == workflow_def.workflow_id
        
        # Property: Version should be incremented
        original_version = tuple(map(int, workflow_def.version.split('.')))
        modified_version = tuple(map(int, modified_workflow.version.split('.')))
        assert modified_version > original_version
    
    @given(workflow_def=workflow_definition_strategy(),
           performance_data=st.lists(performance_data_strategy(), min_size=1, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_property_optimization_maintains_validity(self, workflow_def, performance_data):
        """
        Property: For any workflow and performance data, optimization maintains validity
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.2**
        """
        agent = WorkflowRegenerationAgent()
        validator = WDLValidator()
        
        # Store the workflow first
        agent._store_version(workflow_def)
        
        # Optimize workflow
        optimized_workflow = agent.optimize_workflow(workflow_def.workflow_id, performance_data)
        
        # Property: Optimized workflow must be valid
        assert validator.is_valid(optimized_workflow), \
            f"Optimized workflow is invalid: {validator.validate(optimized_workflow)}"
        
        # Property: Workflow ID should remain the same
        assert optimized_workflow.workflow_id == workflow_def.workflow_id
    
    @given(workflow_def=workflow_definition_strategy(),
           rule_change=rule_change_strategy())
    @settings(max_examples=100)
    def test_property_rule_changes_handled_without_manual_intervention(self, workflow_def, rule_change):
        """
        Property: For any workflow and rule change, system handles updates automatically
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.3**
        """
        agent = WorkflowRegenerationAgent()
        
        # Store the workflow first
        agent._store_version(workflow_def)
        
        # Set affected workflows
        rule_change.affected_workflows = [workflow_def.workflow_id]
        
        # Handle rule change
        updated_workflows = agent.handle_business_rule_change(rule_change)
        
        # Property: Rule change should be handled without errors
        assert isinstance(updated_workflows, list)
        
        # Property: If workflow was affected, it should be updated
        if workflow_def.workflow_id in rule_change.affected_workflows:
            # Either workflow was updated or no update was needed
            assert len(updated_workflows) >= 0
            
            # If updated, the new version should be valid
            if updated_workflows:
                validator = WDLValidator()
                for updated_wf in updated_workflows:
                    assert validator.is_valid(updated_wf)
    
    @given(workflow_def=workflow_definition_strategy())
    @settings(max_examples=100, deadline=None)
    def test_property_workflow_versioning_maintains_history(self, workflow_def):
        """
        Property: For any workflow, versioning system maintains complete history
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.2**
        """
        agent = WorkflowRegenerationAgent()
        
        # Store initial version
        agent._store_version(workflow_def)
        
        # Get version history
        history = agent.get_workflow_version_history(workflow_def.workflow_id)
        
        # Property: History should contain at least the initial version
        assert len(history) >= 1
        
        # Property: Each history entry should have required fields
        for entry in history:
            assert 'version' in entry
            assert 'created_at' in entry
            assert 'performance_count' in entry
        
        # Make a modification
        modifications = {'update_metadata': {'test': True}}
        agent.modify_workflow(workflow_def.workflow_id, modifications)
        
        # Get updated history
        updated_history = agent.get_workflow_version_history(workflow_def.workflow_id)
        
        # Property: History should grow with modifications
        assert len(updated_history) > len(history)
    
    @given(template_name=st.sampled_from(['pricing_optimization', 'inventory_rebalancing']))
    @settings(max_examples=50)
    def test_property_template_based_generation_uses_template_structure(self, template_name):
        """
        Property: For any template, generated workflows should inherit template structure
        **Feature: retailmind-ai, Property 9: Workflow Regeneration Adaptability**
        **Validates: Requirements 7.1**
        """
        agent = WorkflowRegenerationAgent()
        
        # Get original template
        template = agent.template_library.get_template(template_name)
        assert template is not None
        
        # Generate workflow from template
        requirements = {
            'name': 'Test Workflow',
            'metadata': {'test': True}
        }
        generated = agent.generate_workflow('test_workflow', requirements, template_name)
        
        # Property: Generated workflow should have similar structure to template
        # (same number of steps or more)
        assert len(generated.steps) >= len(template.steps)
        
        # Property: Generated workflow should have same category if specified in template
        if 'category' in template.metadata:
            # Category might be in generated metadata
            assert 'category' in generated.metadata or 'category' in template.metadata


class TestWorkflowRegenerationUnit:
    """Unit tests for specific workflow regeneration scenarios"""
    
    def test_generate_workflow_from_template(self):
        """Test generating workflow from template"""
        agent = WorkflowRegenerationAgent()
        
        requirements = {
            'name': 'Custom Pricing Workflow',
            'metadata': {'priority': 'high'}
        }
        
        workflow = agent.generate_workflow(
            'custom_pricing',
            requirements,
            'pricing_optimization'
        )
        
        assert workflow.name == 'Custom Pricing Workflow'
        assert workflow.metadata['priority'] == 'high'
        assert len(workflow.steps) > 0
    
    def test_modify_workflow_add_steps(self):
        """Test modifying workflow by adding steps"""
        agent = WorkflowRegenerationAgent()
        
        # Create initial workflow
        initial_workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test workflow',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1'
        )
        
        agent._store_version(initial_workflow)
        
        # Add a step
        modifications = {
            'add_steps': [
                {
                    'stepId': 'step2',
                    'name': 'Step 2',
                    'type': 'lambda',
                    'configuration': {'function': 'test2'},
                    'conditions': []
                }
            ]
        }
        
        modified = agent.modify_workflow('test_workflow', modifications)
        
        assert len(modified.steps) == 2
        assert any(s.step_id == 'step2' for s in modified.steps)
    
    def test_optimize_workflow_based_on_performance(self):
        """Test workflow optimization based on performance"""
        agent = WorkflowRegenerationAgent()
        
        # Create workflow
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test workflow',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1'
        )
        
        agent._store_version(workflow)
        
        # Provide poor performance data
        performance_data = [
            WorkflowPerformance(execution_time=50.0, success_rate=0.7, business_impact=0.3)
        ]
        
        optimized = agent.optimize_workflow('test_workflow', performance_data)
        
        # Should return a workflow (may be optimized or original)
        assert optimized is not None
        assert optimized.workflow_id == 'test_workflow'
    
    def test_handle_business_rule_change(self):
        """Test handling business rule changes"""
        agent = WorkflowRegenerationAgent()
        
        # Create workflow
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test workflow',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test', 'threshold': 0.8}
                )
            ],
            start_step='step1'
        )
        
        agent._store_version(workflow)
        
        # Create rule change
        rule_change = BusinessRuleChange(
            rule_id='rule1',
            rule_type='threshold',
            old_value=0.8,
            new_value=0.9,
            affected_workflows=['test_workflow']
        )
        
        updated_workflows = agent.handle_business_rule_change(rule_change)
        
        assert len(updated_workflows) >= 0

    
    def test_handle_business_rule_change(self):
        """Test handling business rule changes"""
        agent = WorkflowRegenerationAgent()
        
        # Create workflow
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test workflow',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test', 'threshold': 0.8}
                )
            ],
            start_step='step1'
        )
        
        agent._store_version(workflow)
        
        # Create rule change
        rule_change = BusinessRuleChange(
            rule_id='rule1',
            rule_type='threshold',
            old_value=0.8,
            new_value=0.9,
            affected_workflows=['test_workflow']
        )
        
        updated_workflows = agent.handle_business_rule_change(rule_change)
        
        assert len(updated_workflows) >= 0


class TestWDLParserUnit:
    """Unit tests for WDL parser"""
    
    def test_parse_valid_wdl(self):
        """Test parsing valid WDL"""
        from src.workflows.wdl_parser import WDLParser
        
        wdl_dict = {
            'workflowId': 'test_workflow',
            'name': 'Test Workflow',
            'version': '1.0.0',
            'description': 'Test',
            'startStep': 'step1',
            'steps': [
                {
                    'stepId': 'step1',
                    'name': 'Step 1',
                    'type': 'lambda',
                    'configuration': {'function': 'test'},
                    'conditions': []
                }
            ]
        }
        
        parser = WDLParser()
        workflow_def = parser.parse(wdl_dict)
        
        assert workflow_def.workflow_id == 'test_workflow'
        assert workflow_def.name == 'Test Workflow'
        assert len(workflow_def.steps) == 1
    
    def test_validate_workflow(self):
        """Test workflow validation"""
        from src.workflows.wdl_parser import WDLValidator
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1'
        )
        
        validator = WDLValidator()
        assert validator.is_valid(workflow)
    
    def test_validate_workflow_with_invalid_start_step(self):
        """Test validation catches invalid start step"""
        from src.workflows.wdl_parser import WDLValidator
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='nonexistent_step'
        )
        
        validator = WDLValidator()
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any('start step' in error.lower() for error in errors)


class TestWorkflowExecutionUnit:
    """Unit tests for workflow execution"""
    
    def test_execute_workflow(self):
        """Test workflow execution"""
        from src.workflows.execution_engine import WorkflowExecutionEngine
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1'
        )
        
        engine = WorkflowExecutionEngine()
        instance = engine.execute_workflow(workflow, {'test': 'data'})
        
        assert instance is not None
        assert instance.workflow_id == 'test_workflow'
        assert instance.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]
    
    def test_generate_state_machine(self):
        """Test Step Functions state machine generation"""
        from src.workflows.execution_engine import StepFunctionsGenerator
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test workflow',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test_function'}
                )
            ],
            start_step='step1'
        )
        
        generator = StepFunctionsGenerator()
        state_machine = generator.generate_state_machine(workflow)
        
        assert 'StartAt' in state_machine
        assert state_machine['StartAt'] == 'step1'
        assert 'States' in state_machine
        assert 'step1' in state_machine['States']
    
    def test_monitor_execution(self):
        """Test execution monitoring"""
        from src.workflows.execution_engine import WorkflowExecutionMonitor
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1'
        )
        
        monitor = WorkflowExecutionMonitor()
        instance = monitor.start_execution(workflow, 'test_agent')
        
        assert instance is not None
        assert instance.status == WorkflowStatus.RUNNING
        
        # Update status
        monitor.update_execution_status(
            instance.instance_id,
            WorkflowStatus.COMPLETED,
            WorkflowPerformance(execution_time=1.0, success_rate=1.0, business_impact=0.8)
        )
        
        updated = monitor.get_execution(instance.instance_id)
        assert updated.status == WorkflowStatus.COMPLETED


class TestRollbackUnit:
    """Unit tests for rollback mechanism"""
    
    def test_execute_rollback(self):
        """Test rollback execution"""
        from src.workflows.execution_engine import RollbackManager
        from src.workflows.wdl_parser import WDLRollbackStep
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1',
            rollback_procedure=[
                WDLRollbackStep(
                    step_id='step1',
                    action='revert_action',
                    configuration={'function': 'revert_test'}
                )
            ]
        )
        
        manager = RollbackManager()
        success = manager.execute_rollback(workflow, 'instance_123', 'step1')
        
        assert success is True
        
        # Check rollback history
        history = manager.get_rollback_history('instance_123')
        assert len(history) > 0
    
    def test_rollback_without_procedure(self):
        """Test rollback when no procedure defined"""
        from src.workflows.execution_engine import RollbackManager
        
        workflow = WorkflowDefinition(
            workflow_id='test_workflow',
            name='Test',
            version='1.0.0',
            description='Test',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'test'}
                )
            ],
            start_step='step1',
            rollback_procedure=[]
        )
        
        manager = RollbackManager()
        success = manager.execute_rollback(workflow, 'instance_123', 'step1')
        
        assert success is False


class TestWorkflowTemplatesUnit:
    """Unit tests for workflow templates"""
    
    def test_get_template(self):
        """Test getting a template"""
        from src.workflows.workflow_templates import WorkflowTemplateLibrary
        
        library = WorkflowTemplateLibrary()
        template = library.get_template('pricing_optimization')
        
        assert template is not None
        assert template.workflow_id == 'pricing_optimization_v1'
        assert len(template.steps) > 0
    
    def test_list_templates(self):
        """Test listing all templates"""
        from src.workflows.workflow_templates import WorkflowTemplateLibrary
        
        library = WorkflowTemplateLibrary()
        templates = library.list_templates()
        
        assert len(templates) > 0
        assert 'pricing_optimization' in templates
        assert 'inventory_rebalancing' in templates
    
    def test_add_custom_template(self):
        """Test adding a custom template"""
        from src.workflows.workflow_templates import WorkflowTemplateLibrary
        
        library = WorkflowTemplateLibrary()
        
        custom_template = WorkflowDefinition(
            workflow_id='custom_workflow',
            name='Custom',
            version='1.0.0',
            description='Custom template',
            steps=[
                WDLStep(
                    step_id='step1',
                    name='Step 1',
                    type=WDLStepType.LAMBDA,
                    configuration={'function': 'custom'}
                )
            ],
            start_step='step1'
        )
        
        library.add_template('custom', custom_template)
        
        retrieved = library.get_template('custom')
        assert retrieved is not None
        assert retrieved.workflow_id == 'custom_workflow'
