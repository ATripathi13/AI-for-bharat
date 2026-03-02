"""
Workflow Regeneration Agent for RetailMind AI
Dynamically generates, modifies, and optimizes business workflows
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import copy

from .base_agent import BaseAgent
from ..models.agent_decision import AgentDecision
from ..models.workflow_instance import WorkflowInstance, WorkflowStep, WorkflowPerformance, WorkflowStatus, WorkflowStepType
from ..workflows.wdl_parser import (
    WorkflowDefinition,
    WDLStep,
    WDLStepType,
    WDLCondition,
    WDLConditionOperator,
    WDLRollbackStep,
    WDLValidator
)
from ..workflows.workflow_templates import WorkflowTemplateLibrary


class WorkflowVersion:
    """Tracks workflow versions"""
    def __init__(self, workflow_id: str, version: str, definition: WorkflowDefinition, created_at: datetime):
        self.workflow_id = workflow_id
        self.version = version
        self.definition = definition
        self.created_at = created_at
        self.performance_history: List[WorkflowPerformance] = []
    
    def add_performance(self, performance: WorkflowPerformance):
        """Add performance metrics"""
        self.performance_history.append(performance)
    
    def get_average_performance(self) -> Optional[WorkflowPerformance]:
        """Calculate average performance"""
        if not self.performance_history:
            return None
        
        avg_exec_time = sum(p.execution_time for p in self.performance_history) / len(self.performance_history)
        avg_success_rate = sum(p.success_rate for p in self.performance_history) / len(self.performance_history)
        avg_business_impact = sum(p.business_impact for p in self.performance_history) / len(self.performance_history)
        
        return WorkflowPerformance(
            execution_time=avg_exec_time,
            success_rate=avg_success_rate,
            business_impact=avg_business_impact
        )


class BusinessRuleChange:
    """Represents a change in business rules"""
    def __init__(
        self,
        rule_id: str,
        rule_type: str,
        old_value: Any,
        new_value: Any,
        affected_workflows: List[str]
    ):
        self.rule_id = rule_id
        self.rule_type = rule_type
        self.old_value = old_value
        self.new_value = new_value
        self.affected_workflows = affected_workflows
        self.timestamp = datetime.utcnow()


class WorkflowRegenerationAgent(BaseAgent):
    """
    Workflow Regeneration Agent
    Dynamically generates and optimizes workflows based on business conditions
    """
    
    def __init__(self, agent_id: str = "workflow_regeneration_agent"):
        """Initialize Workflow Regeneration Agent"""
        super().__init__(agent_id, "workflow_regeneration", "1.0.0")
        self.template_library = WorkflowTemplateLibrary()
        self.validator = WDLValidator()
        self.workflow_versions: Dict[str, List[WorkflowVersion]] = {}
        self.business_rules: Dict[str, Any] = {}
    
    def get_capabilities(self) -> list[str]:
        """Return agent capabilities"""
        return [
            'workflow_generation',
            'workflow_modification',
            'workflow_optimization',
            'business_rule_handling',
            'workflow_versioning'
        ]
    
    def process(self, input_data: Any) -> AgentDecision:
        """
        Process workflow regeneration request
        
        Args:
            input_data: Request data containing action and parameters
            
        Returns:
            AgentDecision with workflow recommendation
        """
        action_type = input_data.get('action')
        
        if action_type == 'generate':
            return self._handle_generation(input_data)
        elif action_type == 'modify':
            return self._handle_modification(input_data)
        elif action_type == 'optimize':
            return self._handle_optimization(input_data)
        elif action_type == 'handle_rule_change':
            return self._handle_rule_change(input_data)
        else:
            return self.create_decision(
                input_data=input_data,
                action='error',
                confidence=0.0,
                reasoning=f"Unknown action type: {action_type}"
            )
    
    def generate_workflow(
        self,
        workflow_name: str,
        business_requirements: Dict[str, Any],
        template_name: Optional[str] = None
    ) -> WorkflowDefinition:
        """
        Generate a new workflow dynamically
        
        Args:
            workflow_name: Name for the new workflow
            business_requirements: Business requirements for the workflow
            template_name: Optional template to base workflow on
            
        Returns:
            WorkflowDefinition
        """
        if template_name:
            # Start from template
            template = self.template_library.get_template(template_name)
            if not template:
                raise ValueError(f"Template '{template_name}' not found")
            
            # Customize template based on requirements
            workflow_def = self._customize_template(template, business_requirements)
        else:
            # Generate from scratch
            workflow_def = self._generate_from_requirements(workflow_name, business_requirements)
        
        # Validate generated workflow
        errors = self.validator.validate(workflow_def)
        if errors:
            raise ValueError(f"Generated workflow is invalid: {errors}")
        
        # Store version
        self._store_version(workflow_def)
        
        return workflow_def
    
    def modify_workflow(
        self,
        workflow_id: str,
        modifications: Dict[str, Any]
    ) -> WorkflowDefinition:
        """
        Modify an existing workflow
        
        Args:
            workflow_id: ID of workflow to modify
            modifications: Modifications to apply
            
        Returns:
            Modified WorkflowDefinition
        """
        # Get current version
        current_version = self._get_latest_version(workflow_id)
        if not current_version:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # Create modified copy
        modified_def = copy.deepcopy(current_version.definition)
        
        # Apply modifications
        if 'add_steps' in modifications:
            for step_data in modifications['add_steps']:
                new_step = WDLStep.from_dict(step_data)
                modified_def.steps.append(new_step)
        
        if 'remove_steps' in modifications:
            step_ids_to_remove = set(modifications['remove_steps'])
            modified_def.steps = [s for s in modified_def.steps if s.step_id not in step_ids_to_remove]
        
        if 'update_steps' in modifications:
            for step_id, updates in modifications['update_steps'].items():
                for step in modified_def.steps:
                    if step.step_id == step_id:
                        for key, value in updates.items():
                            setattr(step, key, value)
        
        if 'update_metadata' in modifications:
            modified_def.metadata.update(modifications['update_metadata'])
        
        # Increment version
        version_parts = modified_def.version.split('.')
        version_parts[-1] = str(int(version_parts[-1]) + 1)
        modified_def.version = '.'.join(version_parts)
        
        # Validate modified workflow
        errors = self.validator.validate(modified_def)
        if errors:
            raise ValueError(f"Modified workflow is invalid: {errors}")
        
        # Store new version
        self._store_version(modified_def)
        
        return modified_def
    
    def optimize_workflow(
        self,
        workflow_id: str,
        performance_data: List[WorkflowPerformance]
    ) -> WorkflowDefinition:
        """
        Optimize workflow based on performance data
        
        Args:
            workflow_id: ID of workflow to optimize
            performance_data: Historical performance metrics
            
        Returns:
            Optimized WorkflowDefinition
        """
        current_version = self._get_latest_version(workflow_id)
        if not current_version:
            raise ValueError(f"Workflow '{workflow_id}' not found")
        
        # Add performance data
        for perf in performance_data:
            current_version.add_performance(perf)
        
        # Analyze performance
        avg_perf = current_version.get_average_performance()
        if not avg_perf:
            return current_version.definition
        
        # Determine optimizations
        optimizations = {}
        
        # If success rate is low, add retry logic
        if avg_perf.success_rate < 0.9:
            optimizations['add_retry'] = True
        
        # If execution time is high, look for parallelization opportunities
        if avg_perf.execution_time > 30.0:
            optimizations['parallelize'] = True
        
        # If business impact is low, adjust decision thresholds
        if avg_perf.business_impact < 0.5:
            optimizations['adjust_thresholds'] = True
        
        # Apply optimizations
        if optimizations:
            return self.modify_workflow(workflow_id, self._create_optimization_modifications(optimizations))
        
        return current_version.definition
    
    def handle_business_rule_change(
        self,
        rule_change: BusinessRuleChange
    ) -> List[WorkflowDefinition]:
        """
        Handle business rule changes and update affected workflows
        
        Args:
            rule_change: BusinessRuleChange object
            
        Returns:
            List of updated WorkflowDefinitions
        """
        updated_workflows = []
        
        for workflow_id in rule_change.affected_workflows:
            current_version = self._get_latest_version(workflow_id)
            if not current_version:
                continue
            
            # Determine modifications based on rule change
            modifications = self._determine_rule_modifications(
                current_version.definition,
                rule_change
            )
            
            if modifications:
                try:
                    updated_workflow = self.modify_workflow(workflow_id, modifications)
                    updated_workflows.append(updated_workflow)
                except ValueError as e:
                    print(f"Failed to update workflow {workflow_id}: {str(e)}")
        
        return updated_workflows
    
    def _handle_generation(self, input_data: Dict[str, Any]) -> AgentDecision:
        """Handle workflow generation request"""
        try:
            workflow_name = input_data.get('workflow_name')
            requirements = input_data.get('requirements', {})
            template_name = input_data.get('template_name')
            
            workflow_def = self.generate_workflow(workflow_name, requirements, template_name)
            
            return self.create_decision(
                input_data=input_data,
                action='workflow_generated',
                confidence=0.9,
                reasoning=f"Generated workflow '{workflow_name}' based on requirements",
                supporting_data=[workflow_def.to_dict()]
            )
        except Exception as e:
            return self.create_decision(
                input_data=input_data,
                action='generation_failed',
                confidence=0.0,
                reasoning=f"Failed to generate workflow: {str(e)}"
            )
    
    def _handle_modification(self, input_data: Dict[str, Any]) -> AgentDecision:
        """Handle workflow modification request"""
        try:
            workflow_id = input_data.get('workflow_id')
            modifications = input_data.get('modifications', {})
            
            modified_workflow = self.modify_workflow(workflow_id, modifications)
            
            return self.create_decision(
                input_data=input_data,
                action='workflow_modified',
                confidence=0.85,
                reasoning=f"Modified workflow '{workflow_id}' successfully",
                supporting_data=[modified_workflow.to_dict()]
            )
        except Exception as e:
            return self.create_decision(
                input_data=input_data,
                action='modification_failed',
                confidence=0.0,
                reasoning=f"Failed to modify workflow: {str(e)}"
            )
    
    def _handle_optimization(self, input_data: Dict[str, Any]) -> AgentDecision:
        """Handle workflow optimization request"""
        try:
            workflow_id = input_data.get('workflow_id')
            performance_data = [
                WorkflowPerformance.from_dict(p) for p in input_data.get('performance_data', [])
            ]
            
            optimized_workflow = self.optimize_workflow(workflow_id, performance_data)
            
            return self.create_decision(
                input_data=input_data,
                action='workflow_optimized',
                confidence=0.8,
                reasoning=f"Optimized workflow '{workflow_id}' based on performance data",
                supporting_data=[optimized_workflow.to_dict()]
            )
        except Exception as e:
            return self.create_decision(
                input_data=input_data,
                action='optimization_failed',
                confidence=0.0,
                reasoning=f"Failed to optimize workflow: {str(e)}"
            )
    
    def _handle_rule_change(self, input_data: Dict[str, Any]) -> AgentDecision:
        """Handle business rule change"""
        try:
            rule_change = BusinessRuleChange(
                rule_id=input_data.get('rule_id'),
                rule_type=input_data.get('rule_type'),
                old_value=input_data.get('old_value'),
                new_value=input_data.get('new_value'),
                affected_workflows=input_data.get('affected_workflows', [])
            )
            
            updated_workflows = self.handle_business_rule_change(rule_change)
            
            return self.create_decision(
                input_data=input_data,
                action='rule_change_handled',
                confidence=0.85,
                reasoning=f"Updated {len(updated_workflows)} workflows for rule change",
                supporting_data=[w.to_dict() for w in updated_workflows]
            )
        except Exception as e:
            return self.create_decision(
                input_data=input_data,
                action='rule_change_failed',
                confidence=0.0,
                reasoning=f"Failed to handle rule change: {str(e)}"
            )
    
    def _customize_template(
        self,
        template: WorkflowDefinition,
        requirements: Dict[str, Any]
    ) -> WorkflowDefinition:
        """Customize a template based on requirements"""
        customized = copy.deepcopy(template)
        
        # Update workflow ID and name
        customized.workflow_id = f"{template.workflow_id}_{uuid.uuid4().hex[:8]}"
        if 'name' in requirements:
            customized.name = requirements['name']
        
        # Update metadata
        if 'metadata' in requirements:
            customized.metadata.update(requirements['metadata'])
        
        # Customize steps based on requirements
        if 'step_customizations' in requirements:
            for step_id, customization in requirements['step_customizations'].items():
                for step in customized.steps:
                    if step.step_id == step_id:
                        step.configuration.update(customization)
        
        return customized
    
    def _generate_from_requirements(
        self,
        workflow_name: str,
        requirements: Dict[str, Any]
    ) -> WorkflowDefinition:
        """Generate workflow from scratch based on requirements"""
        workflow_id = f"custom_{uuid.uuid4().hex[:8]}"
        
        # Create basic steps based on requirements
        steps = []
        step_sequence = requirements.get('steps', [])
        
        for i, step_req in enumerate(step_sequence):
            step = WDLStep(
                step_id=step_req.get('id', f"step_{i}"),
                name=step_req.get('name', f"Step {i}"),
                type=WDLStepType(step_req.get('type', 'lambda')),
                configuration=step_req.get('configuration', {}),
                next_step=step_req.get('next_step')
            )
            steps.append(step)
        
        return WorkflowDefinition(
            workflow_id=workflow_id,
            name=workflow_name,
            version='1.0.0',
            description=requirements.get('description', 'Custom generated workflow'),
            steps=steps,
            start_step=steps[0].step_id if steps else 'start',
            rollback_procedure=[],
            metadata=requirements.get('metadata', {})
        )
    
    def _store_version(self, workflow_def: WorkflowDefinition):
        """Store a workflow version"""
        workflow_id = workflow_def.workflow_id
        
        if workflow_id not in self.workflow_versions:
            self.workflow_versions[workflow_id] = []
        
        version = WorkflowVersion(
            workflow_id=workflow_id,
            version=workflow_def.version,
            definition=workflow_def,
            created_at=datetime.utcnow()
        )
        
        self.workflow_versions[workflow_id].append(version)
    
    def _get_latest_version(self, workflow_id: str) -> Optional[WorkflowVersion]:
        """Get the latest version of a workflow"""
        versions = self.workflow_versions.get(workflow_id, [])
        return versions[-1] if versions else None
    
    def _create_optimization_modifications(self, optimizations: Dict[str, bool]) -> Dict[str, Any]:
        """Create modification dict based on optimization needs"""
        modifications = {}
        
        if optimizations.get('add_retry'):
            modifications['update_metadata'] = {'retry_enabled': True}
        
        if optimizations.get('parallelize'):
            modifications['update_metadata'] = {'parallelization_enabled': True}
        
        if optimizations.get('adjust_thresholds'):
            modifications['update_metadata'] = {'threshold_adjusted': True}
        
        return modifications
    
    def _determine_rule_modifications(
        self,
        workflow_def: WorkflowDefinition,
        rule_change: BusinessRuleChange
    ) -> Dict[str, Any]:
        """Determine modifications needed for a rule change"""
        modifications = {}
        
        # Update metadata to reflect rule change
        modifications['update_metadata'] = {
            'last_rule_update': rule_change.timestamp.isoformat(),
            'rule_version': rule_change.rule_id
        }
        
        # If rule affects thresholds, update step configurations
        if rule_change.rule_type == 'threshold':
            step_updates = {}
            for step in workflow_def.steps:
                if 'threshold' in step.configuration:
                    step_updates[step.step_id] = {
                        'configuration': {
                            **step.configuration,
                            'threshold': rule_change.new_value
                        }
                    }
            if step_updates:
                modifications['update_steps'] = step_updates
        
        return modifications
    
    def get_workflow_version_history(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get version history for a workflow"""
        versions = self.workflow_versions.get(workflow_id, [])
        return [
            {
                'version': v.version,
                'created_at': v.created_at.isoformat(),
                'performance_count': len(v.performance_history)
            }
            for v in versions
        ]
