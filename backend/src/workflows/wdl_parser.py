"""
Workflow Definition Language (WDL) Parser for RetailMind AI
Parses and validates workflow definitions
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum
import json
import jsonschema


class WDLStepType(str, Enum):
    """Types of workflow steps in WDL"""
    LAMBDA = 'lambda'
    DECISION = 'decision'
    PARALLEL = 'parallel'
    WAIT = 'wait'
    CHOICE = 'choice'
    MAP = 'map'


class WDLConditionOperator(str, Enum):
    """Condition operators for workflow decisions"""
    EQUALS = 'equals'
    NOT_EQUALS = 'not_equals'
    GREATER_THAN = 'greater_than'
    LESS_THAN = 'less_than'
    GREATER_EQUAL = 'greater_equal'
    LESS_EQUAL = 'less_equal'
    CONTAINS = 'contains'


@dataclass
class WDLCondition:
    """Condition for workflow branching"""
    variable: str
    operator: WDLConditionOperator
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'variable': self.variable,
            'operator': self.operator.value,
            'value': self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WDLCondition':
        """Create from dictionary"""
        return cls(
            variable=data['variable'],
            operator=WDLConditionOperator(data['operator']),
            value=data['value']
        )


@dataclass
class WDLStep:
    """Step definition in WDL"""
    step_id: str
    name: str
    type: WDLStepType
    configuration: Dict[str, Any]
    conditions: List[WDLCondition] = field(default_factory=list)
    next_step: Optional[str] = None
    error_handler: Optional[str] = None
    retry_config: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'stepId': self.step_id,
            'name': self.name,
            'type': self.type.value,
            'configuration': self.configuration,
            'conditions': [c.to_dict() for c in self.conditions],
            'nextStep': self.next_step,
            'errorHandler': self.error_handler,
            'retryConfig': self.retry_config
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WDLStep':
        """Create from dictionary"""
        return cls(
            step_id=data['stepId'],
            name=data['name'],
            type=WDLStepType(data['type']),
            configuration=data['configuration'],
            conditions=[WDLCondition.from_dict(c) for c in data.get('conditions', [])],
            next_step=data.get('nextStep'),
            error_handler=data.get('errorHandler'),
            retry_config=data.get('retryConfig')
        )


@dataclass
class WDLRollbackStep:
    """Rollback step definition"""
    step_id: str
    action: str
    configuration: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'stepId': self.step_id,
            'action': self.action,
            'configuration': self.configuration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WDLRollbackStep':
        """Create from dictionary"""
        return cls(
            step_id=data['stepId'],
            action=data['action'],
            configuration=data['configuration']
        )


@dataclass
class WorkflowDefinition:
    """Complete workflow definition in WDL"""
    workflow_id: str
    name: str
    version: str
    description: str
    steps: List[WDLStep]
    start_step: str
    rollback_procedure: List[WDLRollbackStep] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflowId': self.workflow_id,
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'startStep': self.start_step,
            'rollbackProcedure': [r.to_dict() for r in self.rollback_procedure],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowDefinition':
        """Create from dictionary"""
        return cls(
            workflow_id=data['workflowId'],
            name=data['name'],
            version=data['version'],
            description=data['description'],
            steps=[WDLStep.from_dict(s) for s in data['steps']],
            start_step=data['startStep'],
            rollback_procedure=[WDLRollbackStep.from_dict(r) for r in data.get('rollbackProcedure', [])],
            metadata=data.get('metadata', {})
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WorkflowDefinition':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class WDLParser:
    """
    Parser for Workflow Definition Language (WDL)
    Converts WDL JSON/dict to WorkflowDefinition objects
    """
    
    def parse(self, wdl_input: str | Dict[str, Any]) -> WorkflowDefinition:
        """
        Parse WDL input into WorkflowDefinition
        
        Args:
            wdl_input: WDL as JSON string or dictionary
            
        Returns:
            WorkflowDefinition object
            
        Raises:
            WDLParseError: If parsing fails
        """
        try:
            if isinstance(wdl_input, str):
                data = json.loads(wdl_input)
            else:
                data = wdl_input
            
            return WorkflowDefinition.from_dict(data)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise WDLParseError(f"Failed to parse WDL: {str(e)}")
    
    def parse_file(self, file_path: str) -> WorkflowDefinition:
        """
        Parse WDL from a file
        
        Args:
            file_path: Path to WDL file
            
        Returns:
            WorkflowDefinition object
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return self.parse(content)
        except IOError as e:
            raise WDLParseError(f"Failed to read WDL file: {str(e)}")


class WDLValidator:
    """
    Validator for Workflow Definition Language (WDL)
    Validates workflow definitions against schema and business rules
    """
    
    # JSON Schema for WDL validation
    WDL_SCHEMA = {
        "type": "object",
        "required": ["workflowId", "name", "version", "description", "steps", "startStep"],
        "properties": {
            "workflowId": {"type": "string", "minLength": 1},
            "name": {"type": "string", "minLength": 1},
            "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            "description": {"type": "string"},
            "startStep": {"type": "string", "minLength": 1},
            "steps": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["stepId", "name", "type", "configuration"],
                    "properties": {
                        "stepId": {"type": "string", "minLength": 1},
                        "name": {"type": "string", "minLength": 1},
                        "type": {
                            "type": "string",
                            "enum": ["lambda", "decision", "parallel", "wait", "choice", "map"]
                        },
                        "configuration": {"type": "object"},
                        "conditions": {"type": "array"},
                        "nextStep": {"type": ["string", "null"]},
                        "errorHandler": {"type": ["string", "null"]},
                        "retryConfig": {"type": ["object", "null"]}
                    }
                }
            },
            "rollbackProcedure": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["stepId", "action", "configuration"],
                    "properties": {
                        "stepId": {"type": "string"},
                        "action": {"type": "string"},
                        "configuration": {"type": "object"}
                    }
                }
            },
            "metadata": {"type": "object"}
        }
    }
    
    def validate(self, workflow_def: WorkflowDefinition) -> List[str]:
        """
        Validate a workflow definition
        
        Args:
            workflow_def: WorkflowDefinition to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate against JSON schema
        try:
            jsonschema.validate(workflow_def.to_dict(), self.WDL_SCHEMA)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
        
        # Business rule validations
        errors.extend(self._validate_step_references(workflow_def))
        errors.extend(self._validate_start_step(workflow_def))
        errors.extend(self._validate_no_cycles(workflow_def))
        errors.extend(self._validate_rollback_steps(workflow_def))
        
        return errors
    
    def _validate_step_references(self, workflow_def: WorkflowDefinition) -> List[str]:
        """Validate that all step references exist"""
        errors = []
        step_ids = {step.step_id for step in workflow_def.steps}
        
        for step in workflow_def.steps:
            if step.next_step and step.next_step not in step_ids:
                errors.append(f"Step '{step.step_id}' references non-existent next step '{step.next_step}'")
            if step.error_handler and step.error_handler not in step_ids:
                errors.append(f"Step '{step.step_id}' references non-existent error handler '{step.error_handler}'")
        
        return errors
    
    def _validate_start_step(self, workflow_def: WorkflowDefinition) -> List[str]:
        """Validate that start step exists"""
        errors = []
        step_ids = {step.step_id for step in workflow_def.steps}
        
        if workflow_def.start_step not in step_ids:
            errors.append(f"Start step '{workflow_def.start_step}' does not exist in workflow steps")
        
        return errors
    
    def _validate_no_cycles(self, workflow_def: WorkflowDefinition) -> List[str]:
        """Validate that workflow has no infinite cycles"""
        errors = []
        
        # Build adjacency list
        graph = {step.step_id: [] for step in workflow_def.steps}
        for step in workflow_def.steps:
            if step.next_step:
                graph[step.step_id].append(step.next_step)
        
        # Check for cycles using DFS
        visited = set()
        rec_stack = set()
        
        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for step_id in graph:
            if step_id not in visited:
                if has_cycle(step_id):
                    errors.append(f"Workflow contains a cycle involving step '{step_id}'")
                    break
        
        return errors
    
    def _validate_rollback_steps(self, workflow_def: WorkflowDefinition) -> List[str]:
        """Validate rollback procedure references valid steps"""
        errors = []
        step_ids = {step.step_id for step in workflow_def.steps}
        
        for rollback_step in workflow_def.rollback_procedure:
            if rollback_step.step_id not in step_ids:
                errors.append(f"Rollback step references non-existent step '{rollback_step.step_id}'")
        
        return errors
    
    def is_valid(self, workflow_def: WorkflowDefinition) -> bool:
        """
        Check if workflow definition is valid
        
        Args:
            workflow_def: WorkflowDefinition to validate
            
        Returns:
            True if valid, False otherwise
        """
        return len(self.validate(workflow_def)) == 0


class WDLParseError(Exception):
    """Exception raised for WDL parsing errors"""
    pass
