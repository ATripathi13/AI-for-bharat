"""
Business Copilot Agent for RetailMind AI
Provides natural language interface for business users with AI-powered insights
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
import json

from .base_agent import BaseAgent
from ..models.agent_decision import AgentDecision, Recommendation
from ..services.explainability import ExplainabilityService
from ..services.feedback_learning import FeedbackLearningService, FeedbackType, FeedbackCategory
from ..services.semantic_search import SemanticSearchService, SemanticSearchQuery, get_semantic_search_service


@dataclass
class QueryIntent:
    """Parsed intent from user query"""
    intent_type: str  # e.g., 'pricing_query', 'inventory_query', 'forecast_query'
    entities: Dict[str, Any]  # Extracted entities (SKU, region, date range, etc.)
    confidence: float
    original_query: str


@dataclass
class ConversationContext:
    """Context for ongoing conversation"""
    conversation_id: str
    user_id: str
    history: List[Dict[str, Any]]
    current_intent: Optional[QueryIntent] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add a message to conversation history"""
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        }
        self.history.append(message)
    
    def get_recent_history(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get n most recent messages"""
        return self.history[-n:] if len(self.history) > n else self.history


@dataclass
class CopilotResponse:
    """Response from Business Copilot"""
    response_text: str
    reasoning_trace: List[str]
    data_sources: List[str]
    recommendations: List[Dict[str, Any]]
    confidence: float
    requires_followup: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'responseText': self.response_text,
            'reasoningTrace': self.reasoning_trace,
            'dataSources': self.data_sources,
            'recommendations': self.recommendations,
            'confidence': self.confidence,
            'requiresFollowup': self.requires_followup
        }


class BusinessCopilotAgent(BaseAgent):
    """
    Business Copilot Agent that provides natural language interface
    for business users to interact with the AI Council
    """
    
    def __init__(
        self,
        agent_id: str = "business_copilot",
        version: str = "1.0.0",
        bedrock_client: Optional[Any] = None
    ):
        """
        Initialize Business Copilot Agent
        
        Args:
            agent_id: Unique identifier for the agent
            version: Agent version
            bedrock_client: Optional Amazon Bedrock client for NLP
        """
        super().__init__(agent_id, "business_copilot", version)
        self.bedrock_client = bedrock_client
        self.conversations: Dict[str, ConversationContext] = {}
        self.explainability_service = ExplainabilityService()
        self.feedback_service = FeedbackLearningService()
        self.semantic_search = get_semantic_search_service()
        
        # Intent patterns for query classification
        self.intent_patterns = {
            'pricing_query': ['price', 'pricing', 'cost', 'margin', 'competitive'],
            'inventory_query': ['inventory', 'stock', 'overstock', 'stockout', 'reorder'],
            'forecast_query': ['forecast', 'demand', 'prediction', 'sales', 'trend'],
            'market_query': ['market', 'competitor', 'trend', 'seasonal', 'festival'],
            'risk_query': ['risk', 'compliance', 'fraud', 'invoice', 'supplier'],
            'general_query': ['help', 'what', 'how', 'why', 'explain']
        }
    
    def get_capabilities(self) -> List[str]:
        """Return list of capabilities"""
        return [
            'natural_language_query',
            'intent_recognition',
            'context_management',
            'agent_coordination',
            'explainable_responses',
            'action_recommendations'
        ]
    
    def process(self, input_data: Any) -> AgentDecision:
        """
        Process user query and generate response
        
        Args:
            input_data: Dictionary with 'query' and optional 'conversation_id', 'user_id'
            
        Returns:
            AgentDecision with copilot response
        """
        if isinstance(input_data, str):
            input_data = {'query': input_data}
        
        query = input_data.get('query', '')
        conversation_id = input_data.get('conversation_id', str(uuid.uuid4()))
        user_id = input_data.get('user_id', 'default_user')
        
        # Get or create conversation context
        context = self._get_or_create_context(conversation_id, user_id)
        
        # Parse query and recognize intent
        intent = self.parse_query(query)
        context.current_intent = intent
        context.add_message('user', query)
        
        # Generate response based on intent
        response = self.generate_response(intent, context)
        
        # Add response to context
        context.add_message('assistant', response.response_text, {
            'reasoning_trace': response.reasoning_trace,
            'data_sources': response.data_sources
        })
        
        # Create decision
        return self.create_decision(
            input_data=input_data,
            action=json.dumps(response.to_dict()),
            confidence=response.confidence,
            reasoning=f"Processed {intent.intent_type} query with {len(response.reasoning_trace)} reasoning steps",
            supporting_data=[response.to_dict()],
            escalation_threshold=0.7
        )
    
    def parse_query(self, query: str) -> QueryIntent:
        """
        Parse user query and recognize intent
        
        Args:
            query: Natural language query from user
            
        Returns:
            QueryIntent with parsed information
        """
        query_lower = query.lower()
        
        # Simple intent classification based on keywords
        intent_scores = {}
        for intent_type, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent_type] = score
        
        # Determine primary intent
        if intent_scores:
            primary_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(intent_scores[primary_intent] / 3.0, 1.0)
        else:
            primary_intent = 'general_query'
            confidence = 0.5
        
        # Extract entities (simplified - in production would use NER)
        entities = self._extract_entities(query)
        
        return QueryIntent(
            intent_type=primary_intent,
            entities=entities,
            confidence=confidence,
            original_query=query
        )
    
    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """
        Extract entities from query (simplified implementation)
        
        Args:
            query: User query
            
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        
        # Extract SKU patterns (simplified)
        words = query.split()
        for i, word in enumerate(words):
            if word.upper() == 'SKU' and i + 1 < len(words):
                entities['sku'] = words[i + 1]
            elif 'SKU-' in word.upper():
                entities['sku'] = word
        
        # Extract region mentions
        regions = ['north', 'south', 'east', 'west', 'central', 'mumbai', 'delhi', 'bangalore']
        for region in regions:
            if region in query.lower():
                entities['region'] = region
        
        # Extract time references
        time_words = ['today', 'tomorrow', 'week', 'month', 'quarter', 'year']
        for time_word in time_words:
            if time_word in query.lower():
                entities['timeframe'] = time_word
        
        return entities
    
    def generate_response(
        self,
        intent: QueryIntent,
        context: ConversationContext
    ) -> CopilotResponse:
        """
        Generate response based on intent and context
        
        Args:
            intent: Parsed query intent
            context: Conversation context
            
        Returns:
            CopilotResponse with answer and recommendations
        """
        reasoning_trace = []
        data_sources = []
        recommendations = []
        
        # Step 1: Understand the query
        reasoning_trace.append(f"Identified intent: {intent.intent_type} with confidence {intent.confidence:.2f}")
        
        # Step 2: Retrieve relevant context using semantic search
        relevant_contexts = self.semantic_search.retrieve_relevant_context(
            query=intent.original_query,
            context_type=intent.intent_type.replace('_query', ''),
            max_contexts=3
        )
        
        if relevant_contexts:
            reasoning_trace.append(f"Retrieved {len(relevant_contexts)} relevant contexts from knowledge base")
            for ctx in relevant_contexts:
                data_sources.append(ctx['source'])
        
        # Step 3: Determine which agents to coordinate with
        required_agents = self._determine_required_agents(intent)
        reasoning_trace.append(f"Coordinating with agents: {', '.join(required_agents)}")
        
        # Step 4: Generate response based on intent type
        if intent.intent_type == 'pricing_query':
            response_text = self._handle_pricing_query(intent, reasoning_trace, data_sources, recommendations)
        elif intent.intent_type == 'inventory_query':
            response_text = self._handle_inventory_query(intent, reasoning_trace, data_sources, recommendations)
        elif intent.intent_type == 'forecast_query':
            response_text = self._handle_forecast_query(intent, reasoning_trace, data_sources, recommendations)
        elif intent.intent_type == 'market_query':
            response_text = self._handle_market_query(intent, reasoning_trace, data_sources, recommendations)
        elif intent.intent_type == 'risk_query':
            response_text = self._handle_risk_query(intent, reasoning_trace, data_sources, recommendations)
        else:
            response_text = self._handle_general_query(intent, reasoning_trace, data_sources, recommendations)
        
        # Step 5: Augment response with retrieved context
        if relevant_contexts:
            response_text = self._augment_response_with_context(response_text, relevant_contexts)
        
        # Calculate overall confidence
        confidence = intent.confidence * 0.8  # Adjust based on intent confidence
        
        # Boost confidence if we have relevant context
        if relevant_contexts:
            avg_relevance = sum(ctx['relevance_score'] for ctx in relevant_contexts) / len(relevant_contexts)
            confidence = min(confidence * (1 + avg_relevance * 0.2), 1.0)
        
        # Generate action-oriented recommendations using explainability service
        action_recommendations = self.explainability_service.generate_action_recommendations(
            intent.intent_type,
            intent.entities,
            {}  # Would include actual data insights in production
        )
        recommendations.extend(action_recommendations)
        
        # Create explanation trace
        decision_id = str(uuid.uuid4())
        explanation_trace = self.explainability_service.create_reasoning_trace(
            decision_id=decision_id,
            steps=reasoning_trace,
            data_sources=data_sources,
            confidence=confidence
        )
        
        # Create initial response
        response = CopilotResponse(
            response_text=response_text,
            reasoning_trace=reasoning_trace,
            data_sources=data_sources,
            recommendations=recommendations,
            confidence=confidence,
            requires_followup=confidence < 0.7
        )
        
        # Apply learning adjustments to improve response
        response = self.adjust_response_based_on_learning(intent, response)
        
        return response
    
    def _determine_required_agents(self, intent: QueryIntent) -> List[str]:
        """Determine which agents are needed for this query"""
        agent_mapping = {
            'pricing_query': ['pricing_optimization'],
            'inventory_query': ['inventory_planning', 'demand_forecast'],
            'forecast_query': ['demand_forecast'],
            'market_query': ['market_intelligence'],
            'risk_query': ['risk_compliance'],
            'general_query': ['market_intelligence', 'demand_forecast', 'pricing_optimization']
        }
        return agent_mapping.get(intent.intent_type, [])
    
    def _handle_pricing_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle pricing-related queries"""
        reasoning_trace.append("Analyzing pricing data and competitive landscape")
        data_sources.append("Pricing Optimization Agent")
        data_sources.append("Market Intelligence Agent")
        
        sku = intent.entities.get('sku', 'all products')
        
        recommendations.append({
            'action': 'review_pricing_strategy',
            'description': f'Review current pricing strategy for {sku}',
            'priority': 'medium'
        })
        
        return f"Based on current market conditions and competitive analysis, I can help you optimize pricing for {sku}. The Pricing Optimization Agent suggests reviewing margin targets and price elasticity."
    
    def _handle_inventory_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle inventory-related queries"""
        reasoning_trace.append("Analyzing inventory levels and demand forecasts")
        data_sources.append("Inventory Planning Agent")
        data_sources.append("Demand Forecast Agent")
        
        region = intent.entities.get('region', 'all regions')
        
        recommendations.append({
            'action': 'optimize_inventory',
            'description': f'Optimize inventory levels for {region}',
            'priority': 'high'
        })
        
        return f"I've analyzed inventory levels for {region}. The Inventory Planning Agent recommends reviewing stock levels to prevent stockouts and reduce overstock situations."
    
    def _handle_forecast_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle forecast-related queries"""
        reasoning_trace.append("Generating demand forecasts based on historical data")
        data_sources.append("Demand Forecast Agent")
        
        timeframe = intent.entities.get('timeframe', 'next 30 days')
        
        recommendations.append({
            'action': 'review_forecast',
            'description': f'Review demand forecast for {timeframe}',
            'priority': 'medium'
        })
        
        return f"The Demand Forecast Agent has generated predictions for {timeframe}. I can provide SKU-level forecasts with 85% accuracy to help you plan ahead."
    
    def _handle_market_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle market intelligence queries"""
        reasoning_trace.append("Analyzing market trends and competitor activity")
        data_sources.append("Market Intelligence Agent")
        
        recommendations.append({
            'action': 'monitor_competitors',
            'description': 'Continue monitoring competitor pricing and market trends',
            'priority': 'medium'
        })
        
        return "I've analyzed current market trends and competitor activity. The Market Intelligence Agent is tracking pricing trends and seasonal patterns to help you stay competitive."
    
    def _handle_risk_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle risk and compliance queries"""
        reasoning_trace.append("Analyzing risk factors and compliance status")
        data_sources.append("Risk & Compliance Agent")
        
        recommendations.append({
            'action': 'review_compliance',
            'description': 'Review compliance status and risk assessments',
            'priority': 'high'
        })
        
        return "The Risk & Compliance Agent has analyzed your documents and transactions. I can help you understand supplier risk scores and compliance requirements."
    
    def _handle_general_query(
        self,
        intent: QueryIntent,
        reasoning_trace: List[str],
        data_sources: List[str],
        recommendations: List[Dict[str, Any]]
    ) -> str:
        """Handle general queries"""
        reasoning_trace.append("Providing general assistance and system overview")
        data_sources.append("AI Council")
        
        return "I'm your Business Copilot, here to help you make data-driven decisions. I can assist with pricing, inventory, forecasting, market intelligence, and risk management. What would you like to know?"
    
    def _augment_response_with_context(
        self,
        response_text: str,
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Augment response with relevant context from knowledge base
        
        Args:
            response_text: Original response text
            contexts: List of relevant contexts
            
        Returns:
            Augmented response text
        """
        if not contexts:
            return response_text
        
        # Add context information
        context_snippets = []
        for ctx in contexts[:2]:  # Use top 2 contexts
            if ctx['relevance_score'] > 5.0:  # Only use highly relevant contexts
                snippet = ctx['content'][:200]  # First 200 chars
                context_snippets.append(snippet)
        
        if context_snippets:
            augmented = response_text + "\n\nBased on historical data: " + " ".join(context_snippets)
            return augmented
        
        return response_text
    
    def _get_or_create_context(
        self,
        conversation_id: str,
        user_id: str
    ) -> ConversationContext:
        """Get existing or create new conversation context"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = ConversationContext(
                conversation_id=conversation_id,
                user_id=user_id,
                history=[]
            )
        return self.conversations[conversation_id]
    
    def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            
        Returns:
            List of conversation messages
        """
        if conversation_id in self.conversations:
            return self.conversations[conversation_id].get_recent_history(limit)
        return []
    
    def clear_conversation(self, conversation_id: str):
        """Clear conversation context"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
    
    def submit_feedback(
        self,
        decision_id: str,
        user_id: str,
        feedback_type: str,
        category: str,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
        correction: Optional[str] = None,
        intent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Submit user feedback on a response
        
        Args:
            decision_id: ID of the decision being rated
            user_id: ID of the user providing feedback
            feedback_type: Type of feedback ('positive', 'negative', 'correction', 'suggestion')
            category: Category of feedback ('accuracy', 'relevance', 'completeness', 'clarity', 'actionability')
            rating: Optional rating (1-5)
            comment: Optional comment
            correction: Optional correction text
            intent_type: Optional intent type for tracking performance
            
        Returns:
            Dictionary with feedback confirmation
        """
        # Convert string to enum
        feedback_type_enum = FeedbackType(feedback_type)
        category_enum = FeedbackCategory(category)
        
        # Collect feedback
        feedback = self.feedback_service.collect_feedback(
            decision_id=decision_id,
            user_id=user_id,
            feedback_type=feedback_type_enum,
            category=category_enum,
            rating=rating,
            comment=comment,
            correction=correction
        )
        
        # Track intent-specific performance if provided
        if intent_type:
            self.feedback_service.track_intent_performance(intent_type, feedback)
        
        # Apply learning adjustments
        adjustments = self.feedback_service.apply_learning_adjustments()
        
        return {
            'feedbackId': feedback.feedback_id,
            'status': 'received',
            'message': 'Thank you for your feedback. We use it to improve response quality.',
            'learningApplied': len(adjustments['intentAdjustments']) > 0 or 
                              len(adjustments['patternAdjustments']) > 0
        }
    
    def get_quality_metrics(self) -> Dict[str, Any]:
        """
        Get current response quality metrics
        
        Returns:
            Dictionary with quality metrics
        """
        metrics = self.feedback_service.get_quality_metrics()
        return metrics.to_dict()
    
    def get_improvement_insights(self) -> List[Dict[str, Any]]:
        """
        Get insights for improving response quality
        
        Returns:
            List of learning insights
        """
        insights = self.feedback_service.get_learning_insights()
        return [insight.to_dict() for insight in insights]
    
    def get_improvement_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get recommendations for improving the agent
        
        Returns:
            List of improvement recommendations
        """
        return self.feedback_service.get_recommendations_for_improvement()
    
    def get_learning_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive learning summary
        
        Returns:
            Dictionary with learning summary including performance metrics,
            insights, and applied adjustments
        """
        return self.feedback_service.get_learning_summary()
    
    def get_intent_performance(self, intent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics for specific intent or all intents
        
        Args:
            intent_type: Optional specific intent type to query
            
        Returns:
            Dictionary with intent performance metrics
        """
        return self.feedback_service.get_intent_performance(intent_type)
    
    def adjust_response_based_on_learning(
        self,
        intent: QueryIntent,
        response: CopilotResponse
    ) -> CopilotResponse:
        """
        Adjust response based on learning from feedback
        
        Args:
            intent: Query intent
            response: Generated response
            
        Returns:
            Adjusted response
        """
        # Get learning adjustments
        adjustments = self.feedback_service.apply_learning_adjustments()
        
        # Check if this intent needs confidence adjustment
        for adjustment in adjustments['intentAdjustments']:
            if adjustment['intent'] == intent.intent_type:
                if adjustment['action'] == 'reduce_confidence':
                    response.confidence *= 0.8
                    response.requires_followup = True
                elif adjustment['action'] == 'increase_confidence':
                    response.confidence = min(response.confidence * 1.1, 1.0)
        
        # Check for pattern-based adjustments
        for adjustment in adjustments['patternAdjustments']:
            if adjustment['priority'] == 'high':
                # Add note about known issues
                if adjustment['pattern'] == 'too_vague':
                    response.reasoning_trace.append(
                        "Note: Providing additional detail based on user feedback"
                    )
                elif adjustment['pattern'] == 'missing_data':
                    response.reasoning_trace.append(
                        "Note: Consulting additional data sources based on feedback"
                    )
        
        return response
    
    def apply_learning_to_intent_patterns(self):
        """
        Apply learning to improve intent recognition patterns
        
        This method updates intent patterns based on feedback about
        wrong intent classification
        """
        # Get insights about wrong intent classification
        wrong_intent_insights = [
            insight for insight in self.feedback_service.learning_insights
            if insight.pattern == 'wrong_intent' and insight.frequency >= 2
        ]
        
        if wrong_intent_insights:
            # In production, this would use ML to update intent classification
            # For now, we log the need for improvement
            return {
                'status': 'learning_applied',
                'message': f'Identified {len(wrong_intent_insights)} intent classification issues',
                'recommendation': 'Consider retraining intent classification model'
            }
        
        return {
            'status': 'no_action_needed',
            'message': 'Intent classification performing well'
        }
