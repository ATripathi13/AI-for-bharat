"""
Workflow Execution Engine for RetailMind AI
Executes workflows and generates Step Functions state machines
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid

from ..models.workflow_instance import (
    WorkflowInstance,
    WorkflowStep,
    WorkflowPerformance,
    WorkflowStatus,
    WorkflowStepType
)
from .wdl_parser import WorkflowDefinition, WDLStep, WDLStepType


class StepFunctionsGenerator:
    """
    Generates AWS Step Functions state machine definitions from workflows
    """
    
    def generate_state_machine(self, workflow_def: WorkflowDefinition) -> Dict[str, Any]:
        """
        Generate Step Functions state machine from workflow definition
        
        Args:
            workflow_def: WorkflowDefinition to convert
            
        Returns:
            Step Functions state machine definition
        """
        states = {}
        
        for step in workflow_def.steps:
            state = self._convert_step_to_state(step, workflow_def)
            states[step.step_id] = state
        
        state_machine = {
            "Comment": workflow_def.description,
            "StartAt": workflow_def.start_step,
            "States": states,
            "Version": workflow_def.version
        }
        
        return state_machine
    
    def _convert_step_to_state(
        self,
        step: WDLStep,
        workflow_def: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Convert a WDL step to a Step Functions state"""
        
        if step.type == WDLStepType.LAMBDA:
            return self._create_lambda_state(step)
        elif step.type == WDLStepType.DECISION or step.type == WDLStepType.CHOICE:
            return self._create_choice_state(step, workflow_def)
        elif step.type == WDLStepType.PARALLEL:
            return self._create_parallel_state(step)
        elif step.type == WDLStepType.WAIT:
            return self._create_wait_state(step)
        elif step.type == WDLStepType.MAP:
            return self._create_map_state(step)
        else:
            raise ValueError(f"Unsupported step type: {step.type}")
    
    def _create_lambda_state(self, step: WDLStep) -> Dict[str, Any]:
        """Create a Lambda task state"""
        state = {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
                "FunctionName": step.configuration.get('function', 'unknown'),
                "Payload": {
                    "input.$": step.configuration.get('input', '$')
                }
            }
        }
        
        if step.next_step:
            state["Next"] = step.next_step
        else:
            state["End"] = True
        
        if step.retry_config:
            state["Retry"] = [step.retry_config]
        
        if step.error_handler:
            state["Catch"] = [{
                "ErrorEquals": ["States.ALL"],
                "Next": step.error_handler
            }]
        
        return state
    
    def _create_choice_state(
        self,
        step: WDLStep,
        workflow_def: WorkflowDefinition
    ) -> Dict[str, Any]:
        """Create a Choice state"""
        state = {
            "Type": "Choice",
            "Choices": []
        }
        
        # Convert conditions to Choice rules
        if 'choices' in step.configuration:
            for choice in step.configuration['choices']:
                condition = choice.get('condition', {})
                choice_rule = {
                    "Variable": condition.get('variable', '$.value'),
                    "Next": choice.get('next', step.next_step or workflow_def.steps[-1].step_id)
                }
                
                # Add comparison operator
                operator = condition.get('operator', 'equals')
                if operator == 'greater_than':
                    choice_rule["NumericGreaterThan"] = condition.get('value', 0)
                elif operator == 'less_than':
                    choice_rule["NumericLessThan"] = condition.get('value', 0)
                elif operator == 'greater_equal':
                    choice_rule["NumericGreaterThanEquals"] = condition.get('value', 0)
                elif operator == 'less_equal':
                    choice_rule["NumericLessThanEquals"] = condition.get('value', 0)
                elif operator == 'equals':
                    value = condition.get('value')
                    if isinstance(value, (int, float)):
                        choice_rule["NumericEquals"] = value
                    elif isinstance(value, str):
                        choice_rule["StringEquals"] = value
                    elif isinstance(value, bool):
                        choice_rule["BooleanEquals"] = value
                
                state["Choices"].append(choice_rule)
        
        # Default path
        if step.next_step:
            state["Default"] = step.next_step
        
        return state
    
    def _create_parallel_state(self, step: WDLStep) -> Dict[str, Any]:
        """Create a Parallel state"""
        state = {
            "Type": "Parallel",
            "Branches": step.configuration.get('branches', [])
        }
        
        if step.next_step:
            state["Next"] = step.next_step
        else:
            state["End"] = True
        
        return state
    
    def _create_wait_state(self, step: WDLStep) -> Dict[str, Any]:
        """Create a Wait state"""
        state = {
            "Type": "Wait",
            "Seconds": step.configuration.get('seconds', 1)
        }
        
        if step.next_step:
            state["Next"] = step.next_step
        else:
            state["End"] = True
        
        return state
    
    def _create_map_state(self, step: WDLStep) -> Dict[str, Any]:
        """Create a Map state"""
        state = {
            "Type": "Map",
            "ItemsPath": step.configuration.get('items_path', '$.items'),
            "Iterator": step.configuration.get('iterator', {})
        }
        
        if step.next_step:
            state["Next"] = step.next_step
        else:
            state["End"] = True
        
        return state


class WorkflowExecutionMonitor:
    """
    Monitors workflow execution and tracks performance
    """
    
    def __init__(self):
        """Initialize execution monitor"""
        self.executions: Dict[str, WorkflowInstance] = {}
    
    def start_execution(
        self,
        workflow_def: WorkflowDefinition,
        generated_by: str = "system"
    ) -> WorkflowInstance:
        """
        Start monitoring a workflow execution
        
        Args:
            workflow_def: Workflow definition being executed
            generated_by: ID of agent that generated the workflow
            
        Returns:
            WorkflowInstance
        """
        instance_id = str(uuid.uuid4())
        
        # Convert WDL steps to workflow steps
        steps = [
            WorkflowStep(
                step_id=wdl_step.step_id,
                type=WorkflowStepType(wdl_step.type.value),
                configuration=wdl_step.configuration,
                conditions={}
            )
            for wdl_step in workflow_def.steps
        ]
        
        instance = WorkflowInstance(
            workflow_id=workflow_def.workflow_id,
            instance_id=instance_id,
            status=WorkflowStatus.RUNNING,
            steps=steps,
            created_by='system',
            generated_by=generated_by,
            performance=WorkflowPerformance(
                execution_time=0.0,
                success_rate=0.0,
                business_impact=0.0
            )
        )
        
        self.executions[instance_id] = instance
        return instance
    
    def update_execution_status(
        self,
        instance_id: str,
        status: WorkflowStatus,
        performance: Optional[WorkflowPerformance] = None
    ):
        """
        Update execution status
        
        Args:
            instance_id: Instance ID
            status: New status
            performance: Optional performance metrics
        """
        if instance_id in self.executions:
            self.executions[instance_id].status = status
            if performance:
                self.executions[instance_id].performance = performance
    
    def get_execution(self, instance_id: str) -> Optional[WorkflowInstance]:
        """Get execution instance"""
        return self.executions.get(instance_id)
    
    def get_execution_metrics(self, instance_id: str) -> Optional[WorkflowPerformance]:
        """Get execution performance metrics"""
        instance = self.executions.get(instance_id)
        return instance.performance if instance else None


class RollbackManager:
    """
    Manages workflow rollback operations
    """
    
    def __init__(self):
        """Initialize rollback manager"""
        self.rollback_history: Dict[str, List[Dict[str, Any]]] = {}
    
    def execute_rollback(
        self,
        workflow_def: WorkflowDefinition,
        instance_id: str,
        failed_step_id: str
    ) -> bool:
        """
        Execute rollback procedure for a failed workflow
        
        Args:
            workflow_def: Workflow definition
            instance_id: Instance ID that failed
            failed_step_id: ID of step that failed
            
        Returns:
            True if rollback successful, False otherwise
        """
        if not workflow_def.rollback_procedure:
            return False
        
        rollback_actions = []
        
        # Find rollback steps for the failed step
        for rollback_step in workflow_def.rollback_procedure:
            if rollback_step.step_id == failed_step_id:
                # Execute rollback action
                action_result = self._execute_rollback_action(
                    rollback_step.action,
                    rollback_step.configuration
                )
                rollback_actions.append({
                    'step_id': rollback_step.step_id,
                    'action': rollback_step.action,
                    'result': action_result,
                    'timestamp': datetime.utcnow().isoformat()
                })
        
        # Store rollback history
        if instance_id not in self.rollback_history:
            self.rollback_history[instance_id] = []
        self.rollback_history[instance_id].extend(rollback_actions)
        
        return len(rollback_actions) > 0
    
    def _execute_rollback_action(
        self,
        action: str,
        configuration: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a single rollback action
        
        Args:
            action: Action to execute
            configuration: Action configuration
            
        Returns:
            Result of action execution
        """
        # In a real implementation, this would call the actual rollback function
        # For now, we simulate the execution
        return {
            'success': True,
            'action': action,
            'message': f"Rollback action '{action}' executed successfully"
        }
    
    def get_rollback_history(self, instance_id: str) -> List[Dict[str, Any]]:
        """Get rollback history for an instance"""
        return self.rollback_history.get(instance_id, [])


class WorkflowExecutionEngine:
    """
    Main workflow execution engine
    Coordinates workflow execution, monitoring, and rollback
    """
    
    def __init__(self):
        """Initialize execution engine"""
        self.generator = StepFunctionsGenerator()
        self.monitor = WorkflowExecutionMonitor()
        self.rollback_manager = RollbackManager()
    
    def execute_workflow(
        self,
        workflow_def: WorkflowDefinition,
        input_data: Dict[str, Any],
        generated_by: str = "system"
    ) -> WorkflowInstance:
        """
        Execute a workflow
        
        Args:
            workflow_def: Workflow definition to execute
            input_data: Input data for workflow
            generated_by: ID of agent that generated the workflow
            
        Returns:
            WorkflowInstance
        """
        # Start monitoring
        instance = self.monitor.start_execution(workflow_def, generated_by)
        
        try:
            # Generate Step Functions state machine
            state_machine = self.generator.generate_state_machine(workflow_def)
            
            # In a real implementation, this would submit to AWS Step Functions
            # For now, we simulate successful execution
            
            # Update status to completed
            performance = WorkflowPerformance(
                execution_time=1.0,
                success_rate=1.0,
                business_impact=0.8
            )
            self.monitor.update_execution_status(
                instance.instance_id,
                WorkflowStatus.COMPLETED,
                performance
            )
            
        except Exception as e:
            # Handle failure
            self.monitor.update_execution_status(
                instance.instance_id,
                WorkflowStatus.FAILED
            )
            
            # Attempt rollback
            rollback_success = self.rollback_manager.execute_rollback(
                workflow_def,
                instance.instance_id,
                workflow_def.start_step
            )
            
            if rollback_success:
                self.monitor.update_execution_status(
                    instance.instance_id,
                    WorkflowStatus.ROLLED_BACK
                )
        
        return self.monitor.get_execution(instance.instance_id)
    
    def get_state_machine_definition(
        self,
        workflow_def: WorkflowDefinition
    ) -> str:
        """
        Get Step Functions state machine definition as JSON
        
        Args:
            workflow_def: Workflow definition
            
        Returns:
            JSON string of state machine definition
        """
        state_machine = self.generator.generate_state_machine(workflow_def)
        return json.dumps(state_machine, indent=2)
    
    def monitor_execution(self, instance_id: str) -> Optional[WorkflowInstance]:
        """
        Get current status of workflow execution
        
        Args:
            instance_id: Instance ID to monitor
            
        Returns:
            WorkflowInstance or None if not found
        """
        return self.monitor.get_execution(instance_id)
    
    def rollback_workflow(
        self,
        workflow_def: WorkflowDefinition,
        instance_id: str,
        failed_step_id: str
    ) -> bool:
        """
        Rollback a failed workflow
        
        Args:
            workflow_def: Workflow definition
            instance_id: Instance ID
            failed_step_id: ID of failed step
            
        Returns:
            True if rollback successful
        """
        return self.rollback_manager.execute_rollback(
            workflow_def,
            instance_id,
            failed_step_id
        )
