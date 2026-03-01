"""
Market Intelligence Agent for RetailMind AI
Tracks pricing trends, competitor analysis, demand patterns, and seasonal trends
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass
import statistics

from .base_agent import BaseAgent
from .registry import AgentRegistry
from .communication import AgentCommunicationInterface, ACPMessage, MessageType
from ..models.agent_decision import AgentDecision
from ..models.business_intelligence import (
    BusinessIntelligence, EntityType, Insights, 
    ActionRecommendation, Priority
)
from ..repositories.dynamodb_repository import BusinessIntelligenceRepository
from ..repositories.s3_repository import S3Repository


@dataclass
class PricingData:
    """Pricing data point"""
    product_id: str
    category: str
    region: str
    price: float
    timestamp: datetime
    competitor_id: Optional[str] = None


@dataclass
class DemandData:
    """Demand data point"""
    product_id: str
    category: str
    region: str
    demand_volume: float
    timestamp: datetime


@dataclass
class MarketIntelligenceInput:
    """Input data for Market Intelligence Agent"""
    pricing_data: List[PricingData]
    demand_data: List[DemandData]
    time_window_days: int = 30


class MarketIntelligenceAgent(BaseAgent):
    """
    Market Intelligence Agent
    Analyzes pricing trends, competitor pricing, demand patterns, and seasonal trends
    """
    
    def __init__(
        self, 
        agent_id: str = "market-intelligence-agent",
        s3_bucket: str = "retailmind-market-intelligence",
        register_with_council: bool = True
    ):
        """
        Initialize Market Intelligence Agent
        
        Args:
            agent_id: Unique identifier for the agent
            s3_bucket: S3 bucket for storing market intelligence data
            register_with_council: Whether to register with AI Council on initialization
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="market_intelligence",
            version="1.0.0"
        )
        
        # Initialize communication and registry
        self.communication = AgentCommunicationInterface()
        self.registry = AgentRegistry()
        
        # Initialize data persistence
        self.bi_repository = BusinessIntelligenceRepository()
        self.s3_repository = S3Repository(s3_bucket)
        
        # Register with AI Council if requested
        if register_with_council:
            self.register()
    
    def register(self):
        """Register this agent with the AI Council"""
        try:
            self.registry.register_agent(self.metadata)
            print(f"Market Intelligence Agent {self.metadata.agent_id} registered successfully")
        except Exception as e:
            print(f"Failed to register Market Intelligence Agent: {str(e)}")
            raise
    
    def unregister(self):
        """Unregister this agent from the AI Council"""
        try:
            self.registry.unregister_agent(self.metadata.agent_id)
            print(f"Market Intelligence Agent {self.metadata.agent_id} unregistered successfully")
        except Exception as e:
            print(f"Failed to unregister Market Intelligence Agent: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "pricing_trend_tracking",
            "competitor_analysis",
            "demand_heatmap_generation",
            "seasonal_trend_detection"
        ]
    
    def process(self, input_data: MarketIntelligenceInput) -> AgentDecision:
        """
        Process market data and generate intelligence
        
        Args:
            input_data: MarketIntelligenceInput with pricing and demand data
            
        Returns:
            AgentDecision with market intelligence recommendations
        """
        # Track pricing trends
        pricing_trends = self.track_pricing_trends(input_data.pricing_data)
        
        # Analyze competitor pricing
        competitor_analysis = self.analyze_competitor_pricing(input_data.pricing_data)
        
        # Generate demand heatmap
        demand_heatmap = self.generate_demand_heatmap(input_data.demand_data)
        
        # Detect seasonal trends
        seasonal_trends = self.detect_seasonal_trends(
            input_data.demand_data,
            input_data.time_window_days
        )
        
        # Aggregate insights
        insights = {
            'pricing_trends': pricing_trends,
            'competitor_analysis': competitor_analysis,
            'demand_heatmap': demand_heatmap,
            'seasonal_trends': seasonal_trends
        }
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(input_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(insights)
        
        # Create decision
        decision = self.create_decision(
            input_data=input_data,
            action="market_intelligence_update",
            confidence=confidence,
            reasoning=f"Analyzed {len(input_data.pricing_data)} pricing points and {len(input_data.demand_data)} demand points",
            supporting_data=[insights, recommendations]
        )
        
        # Persist market intelligence data
        self.persist_intelligence(insights, confidence)
        
        return decision
    
    def handle_message(self, message: ACPMessage) -> Optional[Dict[str, Any]]:
        """
        Handle incoming messages from other agents or AI Council
        
        Args:
            message: ACPMessage to handle
            
        Returns:
            Response payload if applicable
        """
        if message.message_type == MessageType.REQUEST:
            # Handle request for market intelligence
            return self._handle_intelligence_request(message)
        elif message.message_type == MessageType.BROADCAST:
            # Handle broadcast messages (e.g., council decisions)
            return self._handle_broadcast(message)
        elif message.message_type == MessageType.NOTIFICATION:
            # Handle notifications
            return self._handle_notification(message)
        else:
            print(f"Unknown message type: {message.message_type}")
            return None
    
    def _handle_intelligence_request(self, message: ACPMessage) -> Dict[str, Any]:
        """
        Handle request for market intelligence data
        
        Args:
            message: Request message
            
        Returns:
            Market intelligence data
        """
        request_type = message.payload.get('request_type')
        
        if request_type == 'pricing_trends':
            # Retrieve pricing trends from repository
            entities = self.bi_repository.get_by_type(EntityType.PRICING.value, limit=10)
            return {
                'status': 'success',
                'data': [entity.to_dict() for entity in entities]
            }
        elif request_type == 'demand_patterns':
            # Retrieve demand patterns from repository
            entities = self.bi_repository.get_by_type(EntityType.DEMAND.value, limit=10)
            return {
                'status': 'success',
                'data': [entity.to_dict() for entity in entities]
            }
        else:
            return {
                'status': 'error',
                'message': f'Unknown request type: {request_type}'
            }
    
    def _handle_broadcast(self, message: ACPMessage) -> Dict[str, Any]:
        """
        Handle broadcast messages from AI Council
        
        Args:
            message: Broadcast message
            
        Returns:
            Acknowledgment
        """
        # Log the broadcast for audit purposes
        print(f"Received broadcast from {message.agent_id}: {message.payload}")
        
        # Update agent status based on council decisions if needed
        if 'council_decision' in message.payload:
            # Process council decision
            pass
        
        return {'status': 'acknowledged'}
    
    def _handle_notification(self, message: ACPMessage) -> Dict[str, Any]:
        """
        Handle notification messages
        
        Args:
            message: Notification message
            
        Returns:
            Acknowledgment
        """
        print(f"Received notification from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
    
    def persist_intelligence(self, insights: Dict[str, Any], confidence: float):
        """
        Persist market intelligence data to DynamoDB and S3
        
        Args:
            insights: Market intelligence insights
            confidence: Confidence level of the analysis
        """
        timestamp = datetime.now(timezone.utc)
        
        # Persist pricing intelligence
        if 'pricing_trends' in insights and insights['pricing_trends'].get('trends'):
            pricing_entity = BusinessIntelligence(
                entity_type=EntityType.PRICING,
                entity_id=f"pricing-{timestamp.strftime('%Y%m%d-%H%M%S')}",
                insights=Insights(
                    trend=insights['pricing_trends'].get('summary', 'No summary'),
                    prediction=insights['pricing_trends'].get('trends', {}),
                    confidence=confidence,
                    timeframe='30d'
                ),
                recommendations=self._create_recommendations(insights['pricing_trends']),
                data_source=['market_intelligence_agent']
            )
            self.bi_repository.create(pricing_entity)
        
        # Persist demand intelligence
        if 'demand_heatmap' in insights and insights['demand_heatmap'].get('heatmap'):
            demand_entity = BusinessIntelligence(
                entity_type=EntityType.DEMAND,
                entity_id=f"demand-{timestamp.strftime('%Y%m%d-%H%M%S')}",
                insights=Insights(
                    trend=insights['demand_heatmap'].get('summary', 'No summary'),
                    prediction=insights['demand_heatmap'].get('heatmap', {}),
                    confidence=confidence,
                    timeframe='30d'
                ),
                recommendations=self._create_recommendations(insights['demand_heatmap']),
                data_source=['market_intelligence_agent']
            )
            self.bi_repository.create(demand_entity)
        
        # Store detailed insights in S3 for historical analysis
        s3_key = f"market-intelligence/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-insights.json"
        self.s3_repository.upload_json(
            data={
                'timestamp': timestamp.isoformat(),
                'insights': insights,
                'confidence': confidence
            },
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'analysis_date': timestamp.strftime('%Y-%m-%d')
            }
        )
    
    def _create_recommendations(self, insight_data: Dict[str, Any]) -> List[ActionRecommendation]:
        """
        Create action recommendations from insight data
        
        Args:
            insight_data: Insight data dictionary
            
        Returns:
            List of ActionRecommendation objects
        """
        recommendations = []
        summary = insight_data.get('summary', '')
        
        if 'pricing' in summary.lower():
            recommendations.append(ActionRecommendation(
                action='Review pricing strategy based on market trends',
                priority=Priority.HIGH,
                expected_impact='Improved competitive positioning'
            ))
        
        if 'demand' in summary.lower():
            recommendations.append(ActionRecommendation(
                action='Optimize inventory allocation based on demand patterns',
                priority=Priority.MEDIUM,
                expected_impact='Reduced stockouts and overstock'
            ))
        
        if 'seasonal' in summary.lower():
            recommendations.append(ActionRecommendation(
                action='Prepare for upcoming seasonal demand spikes',
                priority=Priority.HIGH,
                expected_impact='Increased sales during peak periods'
            ))
        
        return recommendations if recommendations else [
            ActionRecommendation(
                action='Continue monitoring market conditions',
                priority=Priority.LOW,
                expected_impact='Maintain market awareness'
            )
        ]
    
    def send_intelligence_update(self, correlation_id: str, insights: Dict[str, Any]):
        """
        Send market intelligence update to AI Council
        
        Args:
            correlation_id: Correlation ID for tracking
            insights: Market intelligence insights to broadcast
        """
        payload = {
            'update_type': 'market_intelligence',
            'insights': insights,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self.communication.broadcast(
            from_agent_id=self.metadata.agent_id,
            payload=payload,
            correlation_id=correlation_id
        )
    
    def track_pricing_trends(self, pricing_data: List[PricingData]) -> Dict[str, Any]:
        """
        Track regional and global pricing trends across product categories
        
        Args:
            pricing_data: List of pricing data points
            
        Returns:
            Dictionary with pricing trend analysis
        """
        if not pricing_data:
            return {'trends': {}, 'summary': 'No pricing data available'}
        
        # Group by category and region
        trends = {}
        
        # Global trends by category
        category_prices = {}
        for data in pricing_data:
            if data.category not in category_prices:
                category_prices[data.category] = []
            category_prices[data.category].append(data.price)
        
        for category, prices in category_prices.items():
            trends[f'global_{category}'] = {
                'average_price': statistics.mean(prices),
                'min_price': min(prices),
                'max_price': max(prices),
                'price_variance': statistics.variance(prices) if len(prices) > 1 else 0.0
            }
        
        # Regional trends
        region_category_prices = {}
        for data in pricing_data:
            key = f"{data.region}_{data.category}"
            if key not in region_category_prices:
                region_category_prices[key] = []
            region_category_prices[key].append(data.price)
        
        for key, prices in region_category_prices.items():
            trends[key] = {
                'average_price': statistics.mean(prices),
                'min_price': min(prices),
                'max_price': max(prices),
                'sample_size': len(prices)
            }
        
        return {
            'trends': trends,
            'summary': f'Analyzed {len(pricing_data)} pricing points across {len(category_prices)} categories'
        }
    
    def analyze_competitor_pricing(self, pricing_data: List[PricingData]) -> Dict[str, Any]:
        """
        Analyze and update competitive pricing intelligence
        
        Args:
            pricing_data: List of pricing data points
            
        Returns:
            Dictionary with competitor analysis
        """
        if not pricing_data:
            return {'analysis': {}, 'summary': 'No competitor data available'}
        
        # Filter competitor data
        competitor_data = [p for p in pricing_data if p.competitor_id is not None]
        
        if not competitor_data:
            return {'analysis': {}, 'summary': 'No competitor pricing data found'}
        
        # Group by competitor and category
        competitor_analysis = {}
        
        for data in competitor_data:
            if data.competitor_id not in competitor_analysis:
                competitor_analysis[data.competitor_id] = {}
            
            if data.category not in competitor_analysis[data.competitor_id]:
                competitor_analysis[data.competitor_id][data.category] = []
            
            competitor_analysis[data.competitor_id][data.category].append(data.price)
        
        # Calculate competitor metrics
        analysis_results = {}
        for competitor_id, categories in competitor_analysis.items():
            analysis_results[competitor_id] = {}
            for category, prices in categories.items():
                analysis_results[competitor_id][category] = {
                    'average_price': statistics.mean(prices),
                    'price_range': (min(prices), max(prices)),
                    'data_points': len(prices),
                    'last_updated': max(d.timestamp for d in competitor_data 
                                       if d.competitor_id == competitor_id and d.category == category).isoformat()
                }
        
        return {
            'analysis': analysis_results,
            'summary': f'Analyzed {len(competitor_data)} competitor pricing points from {len(competitor_analysis)} competitors'
        }
    
    def generate_demand_heatmap(self, demand_data: List[DemandData]) -> Dict[str, Any]:
        """
        Generate demand heatmaps by region and product category
        
        Args:
            demand_data: List of demand data points
            
        Returns:
            Dictionary with demand heatmap data
        """
        if not demand_data:
            return {'heatmap': {}, 'summary': 'No demand data available'}
        
        # Group by region and category
        heatmap = {}
        
        for data in demand_data:
            if data.region not in heatmap:
                heatmap[data.region] = {}
            
            if data.category not in heatmap[data.region]:
                heatmap[data.region][data.category] = {
                    'total_demand': 0.0,
                    'data_points': 0
                }
            
            heatmap[data.region][data.category]['total_demand'] += data.demand_volume
            heatmap[data.region][data.category]['data_points'] += 1
        
        # Calculate average demand
        for region in heatmap:
            for category in heatmap[region]:
                total = heatmap[region][category]['total_demand']
                count = heatmap[region][category]['data_points']
                heatmap[region][category]['average_demand'] = total / count if count > 0 else 0.0
        
        return {
            'heatmap': heatmap,
            'summary': f'Generated heatmap from {len(demand_data)} demand points across {len(heatmap)} regions'
        }
    
    def detect_seasonal_trends(
        self, 
        demand_data: List[DemandData],
        time_window_days: int
    ) -> Dict[str, Any]:
        """
        Identify festival-driven and seasonal trends
        
        Args:
            demand_data: List of demand data points
            time_window_days: Time window for trend detection
            
        Returns:
            Dictionary with seasonal trend analysis
        """
        if not demand_data:
            return {'trends': [], 'summary': 'No demand data for seasonal analysis'}
        
        # Sort by timestamp
        sorted_data = sorted(demand_data, key=lambda x: x.timestamp)
        
        if not sorted_data:
            return {'trends': [], 'summary': 'No demand data for seasonal analysis'}
        
        # Calculate time-based demand patterns
        trends = []
        
        # Group by category and time period
        category_time_demand = {}
        for data in sorted_data:
            if data.category not in category_time_demand:
                category_time_demand[data.category] = []
            category_time_demand[data.category].append({
                'timestamp': data.timestamp,
                'demand': data.demand_volume
            })
        
        # Detect trends (simple spike detection)
        for category, time_series in category_time_demand.items():
            if len(time_series) < 2:
                continue
            
            demands = [t['demand'] for t in time_series]
            avg_demand = statistics.mean(demands)
            std_demand = statistics.stdev(demands) if len(demands) > 1 else 0.0
            
            # Detect spikes (demand > avg + 1.5 * std)
            threshold = avg_demand + 1.5 * std_demand if std_demand > 0 else avg_demand * 1.5
            
            for point in time_series:
                if point['demand'] > threshold:
                    # Check if within 7-day advance notice window
                    now = datetime.now(timezone.utc) if point['timestamp'].tzinfo else datetime.utcnow()
                    days_ahead = (now - point['timestamp']).days
                    if -7 <= days_ahead <= 7:
                        trends.append({
                            'category': category,
                            'type': 'seasonal_spike',
                            'timestamp': point['timestamp'].isoformat(),
                            'demand_level': point['demand'],
                            'baseline': avg_demand,
                            'advance_notice_days': max(0, -days_ahead)
                        })
        
        return {
            'trends': trends,
            'summary': f'Detected {len(trends)} seasonal trends across {len(category_time_demand)} categories'
        }
    
    def _calculate_confidence(self, input_data: MarketIntelligenceInput) -> float:
        """Calculate confidence based on data quality"""
        pricing_count = len(input_data.pricing_data)
        demand_count = len(input_data.demand_data)
        
        # Base confidence on data availability
        if pricing_count == 0 and demand_count == 0:
            return 0.0
        
        # Higher confidence with more data points
        total_points = pricing_count + demand_count
        if total_points < 10:
            return 0.5
        elif total_points < 50:
            return 0.7
        elif total_points < 100:
            return 0.85
        else:
            return 0.95
    
    def _generate_recommendations(self, insights: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations from insights"""
        recommendations = []
        
        # Pricing recommendations
        pricing_trends = insights.get('pricing_trends', {}).get('trends', {})
        if pricing_trends:
            recommendations.append("Review pricing strategy based on market trends")
        
        # Competitor recommendations
        competitor_analysis = insights.get('competitor_analysis', {}).get('analysis', {})
        if competitor_analysis:
            recommendations.append("Adjust competitive positioning based on competitor pricing")
        
        # Demand recommendations
        demand_heatmap = insights.get('demand_heatmap', {}).get('heatmap', {})
        if demand_heatmap:
            recommendations.append("Optimize inventory allocation based on regional demand patterns")
        
        # Seasonal recommendations
        seasonal_trends = insights.get('seasonal_trends', {}).get('trends', [])
        if seasonal_trends:
            recommendations.append("Prepare for upcoming seasonal demand spikes")
        
        return recommendations

