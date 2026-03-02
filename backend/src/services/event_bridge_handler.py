"""
EventBridge Handler for Intelligence Loop
Implements event-driven triggers for loop phase transitions
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum
import json
import logging

from .intelligence_loop import IntelligenceLoopOrchestrator, LoopPhase

logger = logging.getLogger(__name__)


class EventType(Enum):
    """EventBridge event types"""
    LOOP_START = "intelligence_loop.start"
    PHASE_COMPLETE = "intelligence_loop.phase_complete"
    LOOP_COMPLETE = "intelligence_loop.complete"
    LOOP_FAILED = "intelligence_loop.failed"
    DATA_INGESTED = "data.ingested"
    DECISION_REQUIRED = "decision.required"
    WORKFLOW_COMPLETE = "workflow.complete"


class EventBridgeHandler:
    """
    Handles EventBridge events for Intelligence Loop orchestration
    Implements Lambda handlers for phase transitions
    """
    
    def __init__(self, orchestrator: Optional[IntelligenceLoopOrchestrator] = None):
        self.orchestrator = orchestrator or IntelligenceLoopOrchestrator()
        self.event_handlers: Dict[str, Callable] = {
            EventType.LOOP_START.value: self.handle_loop_start,
            EventType.PHASE_COMPLETE.value: self.handle_phase_complete,
            EventType.DATA_INGESTED.value: self.handle_data_ingested,
            EventType.DECISION_REQUIRED.value: self.handle_decision_required,
            EventType.WORKFLOW_COMPLETE.value: self.handle_workflow_complete,
        }
        
        # Track event metrics
        self.event_metrics: Dict[str, int] = {}
    
    def handle_event(self, event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
        """
        Main Lambda handler for EventBridge events
        
        Args:
            event: EventBridge event
            context: Lambda context
            
        Returns:
            Response dictionary
        """
        try:
            # Extract event details
            detail_type = event.get('detail-type', '')
            detail = event.get('detail', {})
            
            logger.info(f"Handling event: {detail_type}")
            
            # Track metrics
            self.event_metrics[detail_type] = self.event_metrics.get(detail_type, 0) + 1
            
            # Route to appropriate handler
            handler = self.event_handlers.get(detail_type)
            
            if handler:
                result = handler(detail, event)
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'status': 'success',
                        'event_type': detail_type,
                        'result': result
                    })
                }
            else:
                logger.warning(f"No handler for event type: {detail_type}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'status': 'error',
                        'message': f'Unknown event type: {detail_type}'
                    })
                }
        
        except Exception as e:
            logger.error(f"Error handling event: {str(e)}", exc_info=True)
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'status': 'error',
                    'message': str(e)
                })
            }
    
    def handle_loop_start(self, detail: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle loop start event
        Triggers a new intelligence loop execution
        
        Args:
            detail: Event detail
            event: Full event
            
        Returns:
            Result dictionary
        """
        trigger_event = detail.get('trigger_event', {})
        
        # Start loop execution
        execution = self.orchestrator.start_loop(trigger_event)
        
        # Execute observe phase
        observe_result = self.orchestrator.execute_observe_phase(execution)
        
        # Emit phase complete event
        self.emit_event(
            EventType.PHASE_COMPLETE,
            {
                'loop_id': execution.loop_id,
                'phase': LoopPhase.OBSERVE.value,
                'result': observe_result
            }
        )
        
        return {
            'loop_id': execution.loop_id,
            'status': execution.status.value,
            'current_phase': execution.current_phase.value
        }
    
    def handle_phase_complete(self, detail: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle phase completion event
        Triggers next phase in the loop
        
        Args:
            detail: Event detail
            event: Full event
            
        Returns:
            Result dictionary
        """
        loop_id = detail.get('loop_id')
        completed_phase = detail.get('phase')
        
        if not loop_id:
            raise ValueError("Missing loop_id in event detail")
        
        # Get loop execution
        execution = self.orchestrator.get_loop_status(loop_id)
        
        if not execution:
            raise ValueError(f"Loop execution not found: {loop_id}")
        
        # Determine next phase and execute
        phase_enum = LoopPhase(completed_phase)
        
        if phase_enum == LoopPhase.OBSERVE:
            # Execute analyze phase
            result = self.orchestrator.execute_analyze_phase(execution)
            next_phase = LoopPhase.ANALYZE
        
        elif phase_enum == LoopPhase.ANALYZE:
            # Execute decide phase
            result = self.orchestrator.execute_decide_phase(execution)
            next_phase = LoopPhase.DECIDE
        
        elif phase_enum == LoopPhase.DECIDE:
            # Execute act phase
            result = self.orchestrator.execute_act_phase(execution)
            next_phase = LoopPhase.ACT
        
        elif phase_enum == LoopPhase.ACT:
            # Execute learn phase
            result = self.orchestrator.execute_learn_phase(execution)
            next_phase = LoopPhase.LEARN
        
        elif phase_enum == LoopPhase.LEARN:
            # Execute regenerate phase
            result = self.orchestrator.execute_regenerate_phase(execution)
            next_phase = LoopPhase.REGENERATE
        
        elif phase_enum == LoopPhase.REGENERATE:
            # Loop complete
            self.emit_event(
                EventType.LOOP_COMPLETE,
                {
                    'loop_id': loop_id,
                    'completed_at': datetime.utcnow().isoformat(),
                    'phase_results': {k.value: v for k, v in execution.phase_results.items()}
                }
            )
            return {
                'loop_id': loop_id,
                'status': 'completed'
            }
        
        else:
            raise ValueError(f"Unknown phase: {completed_phase}")
        
        # Emit next phase complete event
        self.emit_event(
            EventType.PHASE_COMPLETE,
            {
                'loop_id': loop_id,
                'phase': next_phase.value,
                'result': result
            }
        )
        
        return {
            'loop_id': loop_id,
            'completed_phase': completed_phase,
            'next_phase': next_phase.value,
            'result': result
        }
    
    def handle_data_ingested(self, detail: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle data ingestion event
        Triggers intelligence loop if conditions are met
        
        Args:
            detail: Event detail
            event: Full event
            
        Returns:
            Result dictionary
        """
        data_source = detail.get('data_source', {})
        trigger_conditions = detail.get('trigger_conditions', {})
        
        # Check if we should trigger a loop
        should_trigger = self._evaluate_trigger_conditions(trigger_conditions)
        
        if should_trigger:
            # Emit loop start event
            self.emit_event(
                EventType.LOOP_START,
                {
                    'trigger_event': {
                        'type': 'data_ingestion',
                        'data_sources': [data_source],
                        'agent_types': trigger_conditions.get('agent_types', []),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            )
            
            return {
                'triggered': True,
                'reason': 'Trigger conditions met'
            }
        
        return {
            'triggered': False,
            'reason': 'Trigger conditions not met'
        }
    
    def handle_decision_required(self, detail: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle decision required event
        Triggers intelligence loop for decision-making
        
        Args:
            detail: Event detail
            event: Full event
            
        Returns:
            Result dictionary
        """
        decision_context = detail.get('decision_context', {})
        agent_types = detail.get('agent_types', [])
        
        # Emit loop start event
        self.emit_event(
            EventType.LOOP_START,
            {
                'trigger_event': {
                    'type': 'decision_required',
                    'data_sources': decision_context.get('data_sources', []),
                    'agent_types': agent_types,
                    'decision_context': decision_context,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        )
        
        return {
            'triggered': True,
            'decision_context': decision_context
        }
    
    def handle_workflow_complete(self, detail: Dict[str, Any], event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle workflow completion event
        Can trigger learning and regeneration phases
        
        Args:
            detail: Event detail
            event: Full event
            
        Returns:
            Result dictionary
        """
        workflow_id = detail.get('workflow_id')
        instance_id = detail.get('instance_id')
        performance = detail.get('performance', {})
        
        # Check if this is part of an active loop
        loop_id = detail.get('loop_id')
        
        if loop_id:
            # Part of active loop - phase transition will handle it
            return {
                'loop_id': loop_id,
                'workflow_id': workflow_id,
                'status': 'acknowledged'
            }
        
        # Standalone workflow completion - trigger learning
        self.emit_event(
            EventType.LOOP_START,
            {
                'trigger_event': {
                    'type': 'workflow_complete',
                    'workflow_id': workflow_id,
                    'instance_id': instance_id,
                    'data_sources': [],
                    'agent_types': [],
                    'business_metrics': performance,
                    'timestamp': datetime.utcnow().isoformat()
                }
            }
        )
        
        return {
            'triggered': True,
            'workflow_id': workflow_id
        }
    
    def emit_event(self, event_type: EventType, detail: Dict[str, Any]) -> None:
        """
        Emit an EventBridge event
        
        Args:
            event_type: Type of event
            detail: Event detail
        """
        # In production, this would use boto3 to put events to EventBridge
        # For now, we'll log and store for testing
        event_data = {
            'Source': 'retailmind.intelligence-loop',
            'DetailType': event_type.value,
            'Detail': json.dumps(detail),
            'Time': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Emitting event: {event_type.value}")
        logger.debug(f"Event data: {event_data}")
        
        # Store for testing/monitoring
        if not hasattr(self, '_emitted_events'):
            self._emitted_events = []
        self._emitted_events.append(event_data)
    
    def _evaluate_trigger_conditions(self, conditions: Dict[str, Any]) -> bool:
        """
        Evaluate whether trigger conditions are met
        
        Args:
            conditions: Trigger conditions
            
        Returns:
            True if conditions are met
        """
        # Simple evaluation logic
        if not conditions:
            return True
        
        # Check threshold conditions
        threshold = conditions.get('threshold')
        value = conditions.get('value')
        
        if threshold is not None and value is not None:
            return value >= threshold
        
        # Check time-based conditions
        schedule = conditions.get('schedule')
        if schedule:
            # In production, would check against schedule
            return True
        
        return True
    
    def get_event_metrics(self) -> Dict[str, int]:
        """Get event processing metrics"""
        return self.event_metrics.copy()
    
    def get_emitted_events(self) -> list:
        """Get list of emitted events (for testing)"""
        return getattr(self, '_emitted_events', [])
    
    def clear_emitted_events(self) -> None:
        """Clear emitted events (for testing)"""
        self._emitted_events = []


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for EventBridge events
    
    Args:
        event: EventBridge event
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    handler = EventBridgeHandler()
    return handler.handle_event(event, context)
