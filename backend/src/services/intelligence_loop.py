"""
Intelligence Loop Orchestrator
Implements the Observe → Analyze → Decide → Act → Learn → Regenerate cycle
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum
import uuid

from ..agents.registry import AgentRegistry
from ..agents.communication import ACPMessage, MessageType
from ..services.ai_council import AICouncil
from ..workflows.execution_engine import WorkflowExecutionEngine
from ..workflows.outcome_learning import OutcomeLearningSystem, OutcomeType
from ..workflows.wdl_parser import WorkflowDefinition
from ..agents.workflow_regeneration_agent import WorkflowRegenerationAgent
from ..repositories.dynamodb_repository import AgentDecisionRepository
from ..repositories.s3_repository import S3Repository


class LoopPhase(Enum):
    """Intelligence Loop phases"""
    OBSERVE = "observe"
    ANALYZE = "analyze"
    DECIDE = "decide"
    ACT = "act"
    LEARN = "learn"
    REGENERATE = "regenerate"


class LoopStatus(Enum):
    """Loop execution status"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class LoopExecution:
    """Represents a single execution of the intelligence loop"""
    
    def __init__(self, loop_id: str, trigger_event: Dict[str, Any]):
        self.loop_id = loop_id
        self.trigger_event = trigger_event
        self.status = LoopStatus.RUNNING
        self.current_phase = LoopPhase.OBSERVE
        self.phase_results: Dict[LoopPhase, Any] = {}
        self.started_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'loop_id': self.loop_id,
            'trigger_event': self.trigger_event,
            'status': self.status.value,
            'current_phase': self.current_phase.value,
            'phase_results': {k.value: v for k, v in self.phase_results.items()},
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error': self.error
        }


class IntelligenceLoopOrchestrator:
    """
    Orchestrates the end-to-end Intelligence Loop:
    Observe → Analyze → Decide → Act → Learn → Regenerate
    """
    
    def __init__(
        self,
        agent_registry: Optional[AgentRegistry] = None,
        ai_council: Optional[AICouncil] = None,
        execution_engine: Optional[WorkflowExecutionEngine] = None,
        learning_system: Optional[OutcomeLearningSystem] = None,
        regeneration_agent: Optional[WorkflowRegenerationAgent] = None,
        dynamodb_repo: Optional[AgentDecisionRepository] = None,
        s3_repo: Optional[S3Repository] = None
    ):
        self.agent_registry = agent_registry or AgentRegistry()
        self.ai_council = ai_council or AICouncil(self.agent_registry)
        self.execution_engine = execution_engine or WorkflowExecutionEngine()
        self.learning_system = learning_system or OutcomeLearningSystem()
        self.regeneration_agent = regeneration_agent or WorkflowRegenerationAgent()
        self.dynamodb_repo = dynamodb_repo or AgentDecisionRepository('intelligence_loops')
        self.s3_repo = s3_repo or S3Repository('intelligence-loop-data')
        
        # Track active loops
        self.active_loops: Dict[str, LoopExecution] = {}
    
    def start_loop(self, trigger_event: Dict[str, Any]) -> LoopExecution:
        """
        Start a new intelligence loop execution
        
        Args:
            trigger_event: Event that triggered the loop
            
        Returns:
            LoopExecution instance
        """
        loop_id = str(uuid.uuid4())
        execution = LoopExecution(loop_id, trigger_event)
        self.active_loops[loop_id] = execution
        
        # Persist loop start
        loop_data = {
            'agentId': 'intelligence_loop',  # Using as partition key
            'decisionId': loop_id,  # Using as sort key
            'timestamp': execution.started_at.isoformat(),
            'status': execution.status.value,
            'trigger_event': trigger_event,
            'escalationRequired': False,
            'recommendation': {
                'action': 'loop_started',
                'confidence': 1.0,
                'reasoning': 'Intelligence loop initiated',
                'supportingData': []
            }
        }
        
        try:
            from ..models.agent_decision import AgentDecision, Recommendation
            decision = AgentDecision(
                agent_id='intelligence_loop',
                decision_id=loop_id,
                timestamp=execution.started_at,
                input_data=trigger_event,
                recommendation=Recommendation(
                    action='loop_started',
                    confidence=1.0,
                    reasoning='Intelligence loop initiated',
                    supporting_data=[]
                ),
                escalation_required=False
            )
            self.dynamodb_repo.create(decision)
        except Exception as e:
            # Log error but don't fail loop start
            pass
        
        return execution
    
    def execute_observe_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Observe Phase: Ingest data from multiple sources
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Observed data
        """
        execution.current_phase = LoopPhase.OBSERVE
        
        # Extract data sources from trigger event
        data_sources = execution.trigger_event.get('data_sources', [])
        
        observed_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'sources': [],
            'raw_data': {}
        }
        
        # Ingest from each data source
        for source in data_sources:
            source_type = source.get('type')
            source_id = source.get('id')
            
            try:
                if source_type == 's3':
                    # Read from S3
                    try:
                        data = self.s3_repo.download_json(source_id)
                        observed_data['raw_data'][source_id] = data
                        observed_data['sources'].append({
                            'type': source_type,
                            'id': source_id,
                            'status': 'success'
                        })
                    except Exception as e:
                        observed_data['sources'].append({
                            'type': source_type,
                            'id': source_id,
                            'status': 'error',
                            'error': str(e)
                        })
                elif source_type == 'dynamodb':
                    # Read from DynamoDB - skip for now as it requires specific keys
                    observed_data['sources'].append({
                        'type': source_type,
                        'id': source_id,
                        'status': 'skipped',
                        'reason': 'DynamoDB read requires specific keys'
                    })
                else:
                    # Direct data
                    observed_data['raw_data'][source_id] = source.get('data', {})
                    observed_data['sources'].append({
                        'type': 'direct',
                        'id': source_id,
                        'status': 'success'
                    })
            except Exception as e:
                observed_data['sources'].append({
                    'type': source.get('type', 'unknown'),
                    'id': source.get('id', 'unknown'),
                    'status': 'error',
                    'error': str(e)
                })
        
        execution.phase_results[LoopPhase.OBSERVE] = observed_data
        return observed_data
    
    def execute_analyze_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Analyze Phase: AI Council analyzes observed data
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Analysis results
        """
        execution.current_phase = LoopPhase.ANALYZE
        
        observed_data = execution.phase_results.get(LoopPhase.OBSERVE, {})
        
        # Determine which agents should analyze
        agent_types = execution.trigger_event.get('agent_types', [])
        
        analysis_results = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_analyses': []
        }
        
        # Get each agent's analysis
        for agent_type in agent_types:
            try:
                agents = self.agent_registry.get_agents_by_type(agent_type)
                if agents:
                    agent = agents[0]
                    
                    # Create analysis message
                    message = ACPMessage(
                        agent_id=agent.metadata.agent_id,
                        message_type=MessageType.REQUEST,
                        payload={
                            'action': 'analyze',
                            'data': observed_data['raw_data']
                        },
                        timestamp=datetime.utcnow(),
                        correlation_id=execution.loop_id
                    )
                    
                    # Get agent analysis (simplified - in production would use actual agent methods)
                    analysis = {
                        'agent_id': agent.metadata.agent_id,
                        'agent_type': agent_type,
                        'insights': f"Analysis from {agent_type}",
                        'confidence': 0.85
                    }
                    
                    analysis_results['agent_analyses'].append(analysis)
            except Exception as e:
                analysis_results['agent_analyses'].append({
                    'agent_type': agent_type,
                    'status': 'error',
                    'error': str(e)
                })
        
        execution.phase_results[LoopPhase.ANALYZE] = analysis_results
        return analysis_results
    
    def execute_decide_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Decide Phase: AI Council makes coordinated decision
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Decision results
        """
        execution.current_phase = LoopPhase.DECIDE
        
        analysis_results = execution.phase_results.get(LoopPhase.ANALYZE, {})
        
        # Extract agent analyses
        agent_analyses = analysis_results.get('agent_analyses', [])
        
        # Use AI Council to coordinate decision
        decision_context = {
            'loop_id': execution.loop_id,
            'analyses': agent_analyses,
            'trigger_event': execution.trigger_event
        }
        
        try:
            # Make coordinated decision
            council_decision = self.ai_council.coordinate_decision(
                decision_context,
                [a['agent_id'] for a in agent_analyses if 'agent_id' in a]
            )
            
            decision_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'decision': council_decision.to_dict(),
                'status': 'success'
            }
        except Exception as e:
            decision_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
        
        execution.phase_results[LoopPhase.DECIDE] = decision_results
        return decision_results
    
    def execute_act_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Act Phase: Execute workflow based on decision
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Action results
        """
        execution.current_phase = LoopPhase.ACT
        
        decision_results = execution.phase_results.get(LoopPhase.DECIDE, {})
        
        if decision_results.get('status') != 'success':
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'skipped',
                'reason': 'No valid decision to act on'
            }
        
        decision = decision_results.get('decision', {})
        
        # Get or generate workflow
        workflow_id = execution.trigger_event.get('workflow_id')
        
        if workflow_id:
            # Use existing workflow
            try:
                workflow_def = self.regeneration_agent.get_workflow(workflow_id)
            except ValueError:
                # Generate new workflow if not found
                workflow_def = self.regeneration_agent.generate_workflow(
                    f"workflow_{execution.loop_id}",
                    decision
                )
        else:
            # Generate new workflow
            workflow_def = self.regeneration_agent.generate_workflow(
                f"workflow_{execution.loop_id}",
                decision
            )
        
        # Execute workflow
        try:
            workflow_instance = self.execution_engine.execute_workflow(
                workflow_def,
                decision,
                'intelligence_loop'
            )
            
            action_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'workflow_id': workflow_def.workflow_id,
                'instance_id': workflow_instance.instance_id,
                'status': workflow_instance.status.value,
                'performance': workflow_instance.performance.to_dict()
            }
        except Exception as e:
            action_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
        
        execution.phase_results[LoopPhase.ACT] = action_results
        return action_results
    
    def execute_learn_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Learn Phase: Capture outcomes and learn from execution
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Learning results
        """
        execution.current_phase = LoopPhase.LEARN
        
        action_results = execution.phase_results.get(LoopPhase.ACT, {})
        
        if action_results.get('status') not in ['completed', 'success']:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'skipped',
                'reason': 'No successful action to learn from'
            }
        
        # Get workflow instance
        instance_id = action_results.get('instance_id')
        workflow_id = action_results.get('workflow_id')
        
        if not instance_id or not workflow_id:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'skipped',
                'reason': 'Missing workflow information'
            }
        
        # Retrieve workflow instance
        try:
            workflow_instance = self.execution_engine.monitor_execution(instance_id)
            
            # Determine outcome type
            if workflow_instance.status.value == 'completed':
                outcome_type = OutcomeType.SUCCESS
            elif workflow_instance.status.value == 'failed':
                outcome_type = OutcomeType.FAILURE
            else:
                outcome_type = OutcomeType.PARTIAL_SUCCESS
            
            # Record outcome
            outcome = self.learning_system.record_outcome(
                workflow_instance,
                outcome_type,
                execution.trigger_event.get('business_metrics', {})
            )
            
            learning_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'outcome_id': outcome.outcome_id,
                'outcome_type': outcome_type.value,
                'status': 'success'
            }
        except Exception as e:
            learning_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
        
        execution.phase_results[LoopPhase.LEARN] = learning_results
        return learning_results
    
    def execute_regenerate_phase(self, execution: LoopExecution) -> Dict[str, Any]:
        """
        Regenerate Phase: Optimize workflows based on learning
        
        Args:
            execution: Loop execution instance
            
        Returns:
            Regeneration results
        """
        execution.current_phase = LoopPhase.REGENERATE
        
        learning_results = execution.phase_results.get(LoopPhase.LEARN, {})
        action_results = execution.phase_results.get(LoopPhase.ACT, {})
        
        if learning_results.get('status') != 'success':
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'skipped',
                'reason': 'No learning data to regenerate from'
            }
        
        workflow_id = action_results.get('workflow_id')
        
        if not workflow_id:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'skipped',
                'reason': 'No workflow to regenerate'
            }
        
        # Check if we have enough data to optimize
        try:
            result = self.learning_system.analyze_and_optimize(
                workflow_id,
                min_samples=5  # Lower threshold for testing
            )
            
            if result['status'] == 'success' and result.get('should_optimize', False):
                # Get performance data
                outcomes = self.learning_system.capture_service.get_outcomes(workflow_id)
                performance_data = [o.performance for o in outcomes]
                
                # Optimize workflow
                optimized_workflow = self.regeneration_agent.optimize_workflow(
                    workflow_id,
                    performance_data
                )
                
                regeneration_results = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'workflow_id': workflow_id,
                    'new_version': optimized_workflow.version,
                    'optimizations_applied': result.get('recommendations', []),
                    'status': 'optimized'
                }
            else:
                regeneration_results = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'workflow_id': workflow_id,
                    'status': 'no_optimization_needed',
                    'reason': result.get('message', 'Insufficient data or no improvements needed')
                }
        except Exception as e:
            regeneration_results = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'error',
                'error': str(e)
            }
        
        execution.phase_results[LoopPhase.REGENERATE] = regeneration_results
        return regeneration_results
    
    def execute_full_loop(self, trigger_event: Dict[str, Any]) -> LoopExecution:
        """
        Execute complete intelligence loop
        
        Args:
            trigger_event: Event that triggers the loop
            
        Returns:
            Completed loop execution
        """
        execution = self.start_loop(trigger_event)
        
        try:
            # Execute each phase in sequence
            self.execute_observe_phase(execution)
            self.execute_analyze_phase(execution)
            self.execute_decide_phase(execution)
            self.execute_act_phase(execution)
            self.execute_learn_phase(execution)
            self.execute_regenerate_phase(execution)
            
            # Mark as completed
            execution.status = LoopStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            
        except Exception as e:
            execution.status = LoopStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
        
        finally:
            # Persist final state
            try:
                from ..models.agent_decision import AgentDecision, Recommendation
                decision = AgentDecision(
                    agent_id='intelligence_loop',
                    decision_id=execution.loop_id,
                    timestamp=datetime.utcnow(),
                    input_data=execution.trigger_event,
                    recommendation=Recommendation(
                        action='loop_completed',
                        confidence=1.0,
                        reasoning=f'Loop completed with status: {execution.status.value}',
                        supporting_data=[]
                    ),
                    escalation_required=False
                )
                self.dynamodb_repo.update(decision)
            except Exception:
                pass
            
            # Remove from active loops
            if execution.loop_id in self.active_loops:
                del self.active_loops[execution.loop_id]
        
        return execution
    
    def get_loop_status(self, loop_id: str) -> Optional[LoopExecution]:
        """Get status of a loop execution"""
        if loop_id in self.active_loops:
            return self.active_loops[loop_id]
        
        # Try to retrieve from storage
        try:
            decision = self.dynamodb_repo.get('intelligence_loop', loop_id)
            if decision:
                # Reconstruct execution (simplified)
                execution = LoopExecution(loop_id, decision.input_data)
                execution.status = LoopStatus.COMPLETED  # Assume completed if not in active loops
                return execution
        except Exception:
            pass
        
        return None
