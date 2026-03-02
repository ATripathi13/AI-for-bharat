"""
Pricing Optimization Agent for RetailMind AI
Handles margin-aware pricing, competitive analysis, and price elasticity modeling
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
    sku: str
    current_price: float
    cost: float
    competitor_prices: List[float]
    sales_volume: float
    region: str
    timestamp: datetime


@dataclass
class PriceRecommendation:
    """Price recommendation result"""
    sku: str
    region: str
    current_price: float
    recommended_price: float
    expected_margin: float
    competitive_position: str  # 'below', 'at', 'above' market
    elasticity_impact: Dict[str, float]  # demand and revenue impact
    confidence: float


@dataclass
class PricingOptimizationInput:
    """Input data for Pricing Optimization Agent"""
    pricing_data: List[PricingData]
    target_margin: Optional[float] = None  # Target profit margin (e.g., 0.25 for 25%)
    region_filter: Optional[str] = None
    sku_filter: Optional[str] = None


class PricingOptimizationAgent(BaseAgent):
    """
    Pricing Optimization Agent
    Generates margin-aware pricing recommendations with competitive analysis
    """
    
    def __init__(
        self, 
        agent_id: str = "pricing-optimization-agent",
        s3_bucket: str = "retailmind-pricing-data",
        register_with_council: bool = True
    ):
        """
        Initialize Pricing Optimization Agent
        
        Args:
            agent_id: Unique identifier for the agent
            s3_bucket: S3 bucket for storing pricing data
            register_with_council: Whether to register with AI Council on initialization
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="pricing_optimization",
            version="1.0.0"
        )
        
        # Initialize communication and registry
        self.communication = AgentCommunicationInterface()
        self.registry = AgentRegistry()
        
        # Initialize data persistence
        self.bi_repository = BusinessIntelligenceRepository()
        self.s3_repository = S3Repository(s3_bucket)
        
        # Pricing performance tracking
        self.performance_history: List[Dict[str, Any]] = []
        
        # Register with AI Council if requested
        if register_with_council:
            self.register()
    
    def register(self):
        """Register this agent with the AI Council"""
        try:
            self.registry.register_agent(self.metadata)
            print(f"Pricing Optimization Agent {self.metadata.agent_id} registered successfully")
        except Exception as e:
            print(f"Failed to register Pricing Optimization Agent: {str(e)}")
            raise
    
    def unregister(self):
        """Unregister this agent from the AI Council"""
        try:
            self.registry.unregister_agent(self.metadata.agent_id)
            print(f"Pricing Optimization Agent {self.metadata.agent_id} unregistered successfully")
        except Exception as e:
            print(f"Failed to unregister Pricing Optimization Agent: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "margin_aware_pricing",
            "competitive_pricing_analysis",
            "price_elasticity_modeling",
            "pricing_performance_tracking"
        ]
    
    def process(self, input_data: PricingOptimizationInput) -> AgentDecision:
        """
        Process pricing data and generate optimization recommendations
        
        Args:
            input_data: PricingOptimizationInput with pricing data
            
        Returns:
            AgentDecision with pricing recommendations
        """
        # Generate margin-aware pricing recommendations
        price_recommendations = self.generate_price_recommendations(
            input_data.pricing_data,
            input_data.target_margin,
            input_data.sku_filter,
            input_data.region_filter
        )
        
        # Perform competitive analysis
        competitive_analysis = self.analyze_competitive_pricing(
            input_data.pricing_data,
            input_data.sku_filter,
            input_data.region_filter
        )
        
        # Simulate price elasticity impacts
        elasticity_simulations = self.simulate_price_elasticity(
            input_data.pricing_data,
            price_recommendations
        )
        
        # Aggregate results
        pricing_results = {
            'price_recommendations': price_recommendations,
            'competitive_analysis': competitive_analysis,
            'elasticity_simulations': elasticity_simulations
        }
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(input_data.pricing_data, price_recommendations)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(pricing_results)
        
        # Create decision
        decision = self.create_decision(
            input_data=input_data,
            action="pricing_optimization_update",
            confidence=confidence,
            reasoning=f"Generated pricing recommendations for {len(price_recommendations)} SKUs",
            supporting_data=[pricing_results, recommendations]
        )
        
        # Persist pricing data
        self.persist_pricing_data(pricing_results, confidence)
        
        return decision

    def generate_price_recommendations(
        self,
        pricing_data: List[PricingData],
        target_margin: Optional[float] = None,
        sku_filter: Optional[str] = None,
        region_filter: Optional[str] = None
    ) -> List[PriceRecommendation]:
        """
        Generate margin-aware pricing recommendations
        
        Args:
            pricing_data: List of pricing data points
            target_margin: Target profit margin (e.g., 0.25 for 25%)
            sku_filter: Optional SKU filter
            region_filter: Optional region filter
            
        Returns:
            List of PriceRecommendation objects
        """
        if not pricing_data:
            return []
        
        # Filter data
        filtered_data = pricing_data
        if sku_filter:
            filtered_data = [p for p in filtered_data if p.sku == sku_filter]
        if region_filter:
            filtered_data = [p for p in filtered_data if p.region == region_filter]
        
        # Group by SKU and region
        sku_region_data = {}
        for price_point in filtered_data:
            key = (price_point.sku, price_point.region)
            if key not in sku_region_data:
                sku_region_data[key] = []
            sku_region_data[key].append(price_point)
        
        # Generate recommendations for each SKU-region combination
        recommendations = []
        for (sku, region), data_points in sku_region_data.items():
            recommendation = self._calculate_optimal_price(
                sku=sku,
                region=region,
                data_points=data_points,
                target_margin=target_margin
            )
            if recommendation:
                recommendations.append(recommendation)
        
        return recommendations
    
    def _calculate_optimal_price(
        self,
        sku: str,
        region: str,
        data_points: List[PricingData],
        target_margin: Optional[float] = None
    ) -> Optional[PriceRecommendation]:
        """
        Calculate optimal price for a SKU-region combination
        
        Args:
            sku: SKU identifier
            region: Region identifier
            data_points: Pricing data points
            target_margin: Target profit margin
            
        Returns:
            PriceRecommendation object or None
        """
        if not data_points:
            return None
        
        # Get most recent data point
        latest_data = max(data_points, key=lambda x: x.timestamp)
        
        # Calculate margin-aware price
        if target_margin is not None:
            # Price = Cost / (1 - Target Margin)
            margin_based_price = latest_data.cost / (1 - target_margin)
        else:
            # Use current price as baseline
            margin_based_price = latest_data.current_price
        
        # Analyze competitive position
        if latest_data.competitor_prices:
            avg_competitor_price = statistics.mean(latest_data.competitor_prices)
            
            # Determine competitive position
            if latest_data.current_price < avg_competitor_price * 0.95:
                competitive_position = 'below'
            elif latest_data.current_price > avg_competitor_price * 1.05:
                competitive_position = 'above'
            else:
                competitive_position = 'at'
            
            # Adjust price based on competitive position
            # If we're below market and have good margin, we can increase
            # If we're above market, consider competitive pricing
            if competitive_position == 'below' and margin_based_price > latest_data.current_price:
                recommended_price = min(margin_based_price, avg_competitor_price * 0.98)
            elif competitive_position == 'above':
                recommended_price = max(margin_based_price, avg_competitor_price * 1.02)
            else:
                recommended_price = margin_based_price
        else:
            competitive_position = 'unknown'
            recommended_price = margin_based_price
        
        # Calculate expected margin
        expected_margin = (recommended_price - latest_data.cost) / recommended_price if recommended_price > 0 else 0
        
        # Estimate elasticity impact
        price_change_pct = (recommended_price - latest_data.current_price) / latest_data.current_price if latest_data.current_price > 0 else 0
        elasticity_impact = self._estimate_elasticity_impact(
            price_change_pct,
            latest_data.sales_volume,
            recommended_price
        )
        
        # Calculate confidence based on data quality
        confidence = self._calculate_recommendation_confidence(
            data_points,
            latest_data.competitor_prices
        )
        
        return PriceRecommendation(
            sku=sku,
            region=region,
            current_price=latest_data.current_price,
            recommended_price=recommended_price,
            expected_margin=expected_margin,
            competitive_position=competitive_position,
            elasticity_impact=elasticity_impact,
            confidence=confidence
        )
    
    def _estimate_elasticity_impact(
        self,
        price_change_pct: float,
        current_sales_volume: float,
        new_price: float
    ) -> Dict[str, float]:
        """
        Estimate demand and revenue impact based on price elasticity
        
        Args:
            price_change_pct: Percentage change in price
            current_sales_volume: Current sales volume
            new_price: New recommended price
            
        Returns:
            Dictionary with demand and revenue impact estimates
        """
        # Assume price elasticity of -1.5 (typical for retail)
        # This means 1% price increase leads to 1.5% demand decrease
        elasticity = -1.5
        
        # Estimate demand change
        demand_change_pct = elasticity * price_change_pct
        estimated_demand = current_sales_volume * (1 + demand_change_pct)
        
        # Estimate revenue impact
        current_revenue = current_sales_volume * (new_price / (1 + price_change_pct))
        estimated_revenue = estimated_demand * new_price
        revenue_change_pct = (estimated_revenue - current_revenue) / current_revenue if current_revenue > 0 else 0
        
        return {
            'demand_change_pct': demand_change_pct,
            'estimated_demand': max(0, estimated_demand),
            'revenue_change_pct': revenue_change_pct,
            'estimated_revenue': max(0, estimated_revenue)
        }
    
    def _calculate_recommendation_confidence(
        self,
        data_points: List[PricingData],
        competitor_prices: List[float]
    ) -> float:
        """
        Calculate confidence level for price recommendation
        
        Args:
            data_points: Historical pricing data points
            competitor_prices: Competitor price data
            
        Returns:
            Confidence level (0.0 to 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Increase confidence with more data points
        if len(data_points) >= 10:
            confidence += 0.2
        elif len(data_points) >= 5:
            confidence += 0.1
        
        # Increase confidence with competitor data
        if competitor_prices and len(competitor_prices) >= 3:
            confidence += 0.2
        elif competitor_prices and len(competitor_prices) >= 1:
            confidence += 0.1
        
        # Cap at 0.95
        return min(confidence, 0.95)
    
    def analyze_competitive_pricing(
        self,
        pricing_data: List[PricingData],
        sku_filter: Optional[str] = None,
        region_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze competitive pricing landscape
        
        Args:
            pricing_data: List of pricing data points
            sku_filter: Optional SKU filter
            region_filter: Optional region filter
            
        Returns:
            Dictionary with competitive analysis results
        """
        if not pricing_data:
            return {}
        
        # Filter data
        filtered_data = pricing_data
        if sku_filter:
            filtered_data = [p for p in filtered_data if p.sku == sku_filter]
        if region_filter:
            filtered_data = [p for p in filtered_data if p.region == region_filter]
        
        # Analyze competitive position for each SKU
        competitive_analysis = {}
        
        for price_point in filtered_data:
            if not price_point.competitor_prices:
                continue
            
            avg_competitor_price = statistics.mean(price_point.competitor_prices)
            min_competitor_price = min(price_point.competitor_prices)
            max_competitor_price = max(price_point.competitor_prices)
            
            price_position = (price_point.current_price - avg_competitor_price) / avg_competitor_price if avg_competitor_price > 0 else 0
            
            competitive_analysis[f"{price_point.sku}_{price_point.region}"] = {
                'sku': price_point.sku,
                'region': price_point.region,
                'our_price': price_point.current_price,
                'avg_competitor_price': avg_competitor_price,
                'min_competitor_price': min_competitor_price,
                'max_competitor_price': max_competitor_price,
                'price_position_pct': price_position * 100,
                'competitive_advantage': 'price_leader' if price_position < -0.05 else 'premium' if price_position > 0.05 else 'competitive',
                'competitor_count': len(price_point.competitor_prices)
            }
        
        return competitive_analysis
    
    def simulate_price_elasticity(
        self,
        pricing_data: List[PricingData],
        price_recommendations: List[PriceRecommendation]
    ) -> Dict[str, Any]:
        """
        Simulate price elasticity impacts for recommended prices
        
        Args:
            pricing_data: List of pricing data points
            price_recommendations: List of price recommendations
            
        Returns:
            Dictionary with elasticity simulation results
        """
        simulations = {}
        
        for recommendation in price_recommendations:
            # Find corresponding pricing data
            matching_data = [
                p for p in pricing_data 
                if p.sku == recommendation.sku and p.region == recommendation.region
            ]
            
            if not matching_data:
                continue
            
            latest_data = max(matching_data, key=lambda x: x.timestamp)
            
            # Simulate different price points
            price_scenarios = []
            base_price = latest_data.current_price
            
            for price_multiplier in [0.90, 0.95, 1.00, 1.05, 1.10]:
                scenario_price = base_price * price_multiplier
                price_change_pct = (scenario_price - base_price) / base_price if base_price > 0 else 0
                
                impact = self._estimate_elasticity_impact(
                    price_change_pct,
                    latest_data.sales_volume,
                    scenario_price
                )
                
                price_scenarios.append({
                    'price': scenario_price,
                    'price_change_pct': price_change_pct * 100,
                    'demand_impact': impact['demand_change_pct'] * 100,
                    'revenue_impact': impact['revenue_change_pct'] * 100,
                    'estimated_demand': impact['estimated_demand'],
                    'estimated_revenue': impact['estimated_revenue']
                })
            
            simulations[f"{recommendation.sku}_{recommendation.region}"] = {
                'sku': recommendation.sku,
                'region': recommendation.region,
                'current_price': base_price,
                'recommended_price': recommendation.recommended_price,
                'scenarios': price_scenarios
            }
        
        return simulations

    def track_pricing_performance(
        self,
        sku: str,
        region: str,
        recommended_price: float,
        actual_price_used: float,
        actual_sales_volume: float,
        actual_revenue: float
    ) -> Dict[str, Any]:
        """
        Track pricing performance based on actual outcomes
        
        Args:
            sku: SKU identifier
            region: Region identifier
            recommended_price: Price that was recommended
            actual_price_used: Actual price that was used
            actual_sales_volume: Actual sales volume achieved
            actual_revenue: Actual revenue achieved
            
        Returns:
            Dictionary with performance tracking results
        """
        performance_record = {
            'sku': sku,
            'region': region,
            'recommended_price': recommended_price,
            'actual_price_used': actual_price_used,
            'actual_sales_volume': actual_sales_volume,
            'actual_revenue': actual_revenue,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'recommendation_followed': abs(actual_price_used - recommended_price) / recommended_price < 0.02 if recommended_price > 0 else False
        }
        
        # Store in performance history
        self.performance_history.append(performance_record)
        
        # Store in S3 for analysis
        self._store_performance_feedback(performance_record)
        
        return performance_record
    
    def _store_performance_feedback(self, performance_record: Dict[str, Any]):
        """
        Store pricing performance feedback for continuous learning
        
        Args:
            performance_record: Performance record data
        """
        timestamp = datetime.now(timezone.utc)
        s3_key = f"pricing-performance/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-performance.json"
        
        self.s3_repository.upload_json(
            data=performance_record,
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'feedback_type': 'pricing_performance',
                'sku': performance_record['sku'],
                'region': performance_record['region']
            }
        )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get pricing performance monitoring metrics
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.performance_history:
            return {
                'status': 'no_data',
                'message': 'No performance history available'
            }
        
        # Calculate metrics
        total_recommendations = len(self.performance_history)
        followed_recommendations = sum(1 for p in self.performance_history if p['recommendation_followed'])
        
        # Calculate revenue impact for followed recommendations
        followed_records = [p for p in self.performance_history if p['recommendation_followed']]
        
        if followed_records:
            avg_revenue = statistics.mean([p['actual_revenue'] for p in followed_records])
            total_revenue = sum([p['actual_revenue'] for p in followed_records])
        else:
            avg_revenue = 0.0
            total_revenue = 0.0
        
        return {
            'status': 'active',
            'total_recommendations': total_recommendations,
            'followed_recommendations': followed_recommendations,
            'follow_rate': followed_recommendations / total_recommendations if total_recommendations > 0 else 0.0,
            'avg_revenue': avg_revenue,
            'total_revenue': total_revenue,
            'last_updated': self.performance_history[-1]['timestamp'] if self.performance_history else None
        }
    
    def optimize_recommendations_from_outcomes(
        self,
        sku: str,
        region: str,
        current_recommendation: PriceRecommendation
    ) -> PriceRecommendation:
        """
        Optimize pricing recommendations based on historical performance outcomes
        
        Args:
            sku: SKU identifier
            region: Region identifier
            current_recommendation: Current price recommendation
            
        Returns:
            Optimized PriceRecommendation
        """
        # Filter performance history for this SKU-region
        relevant_history = [
            p for p in self.performance_history
            if p['sku'] == sku and p['region'] == region and p['recommendation_followed']
        ]
        
        if not relevant_history or len(relevant_history) < 3:
            # Not enough data to optimize, return current recommendation
            return current_recommendation
        
        # Analyze performance patterns
        avg_actual_revenue = statistics.mean([p['actual_revenue'] for p in relevant_history])
        avg_actual_volume = statistics.mean([p['actual_sales_volume'] for p in relevant_history])
        
        # Calculate price-revenue correlation
        prices = [p['actual_price_used'] for p in relevant_history]
        revenues = [p['actual_revenue'] for p in relevant_history]
        
        # Find optimal price point based on historical performance
        best_performance = max(relevant_history, key=lambda x: x['actual_revenue'])
        best_price = best_performance['actual_price_used']
        
        # Adjust recommendation based on historical best performance
        # If historical best price is significantly different, adjust towards it
        price_diff = abs(best_price - current_recommendation.recommended_price)
        if price_diff / current_recommendation.recommended_price > 0.10:  # More than 10% difference
            # Gradually adjust towards historical best (50% adjustment)
            optimized_price = current_recommendation.recommended_price + (best_price - current_recommendation.recommended_price) * 0.5
            
            # Recalculate expected margin
            # Find cost from pricing data
            matching_data = [
                p for p in self.performance_history
                if p['sku'] == sku and p['region'] == region
            ]
            
            if matching_data:
                # Estimate cost from historical data (price - margin * price)
                # Assume average margin from current recommendation
                estimated_cost = current_recommendation.current_price * (1 - current_recommendation.expected_margin)
                optimized_margin = (optimized_price - estimated_cost) / optimized_price if optimized_price > 0 else 0
                
                # Update recommendation
                optimized_recommendation = PriceRecommendation(
                    sku=sku,
                    region=region,
                    current_price=current_recommendation.current_price,
                    recommended_price=optimized_price,
                    expected_margin=optimized_margin,
                    competitive_position=current_recommendation.competitive_position,
                    elasticity_impact=current_recommendation.elasticity_impact,
                    confidence=min(current_recommendation.confidence + 0.1, 0.95)  # Increase confidence with historical data
                )
                
                return optimized_recommendation
        
        # No significant optimization needed
        return current_recommendation
    
    def get_pricing_insights_from_performance(self) -> Dict[str, Any]:
        """
        Generate insights from pricing performance history
        
        Returns:
            Dictionary with pricing insights and recommendations
        """
        if not self.performance_history:
            return {
                'insights': [],
                'recommendations': ['Collect more pricing performance data']
            }
        
        insights = []
        recommendations = []
        
        # Analyze follow rate
        metrics = self.get_performance_metrics()
        follow_rate = metrics.get('follow_rate', 0.0)
        
        if follow_rate < 0.5:
            insights.append({
                'type': 'low_follow_rate',
                'message': f'Only {follow_rate*100:.1f}% of pricing recommendations are being followed',
                'severity': 'medium'
            })
            recommendations.append('Review pricing recommendation accuracy and adjust algorithms')
        
        # Analyze revenue performance by SKU-region
        sku_region_performance = {}
        for record in self.performance_history:
            if record['recommendation_followed']:
                key = f"{record['sku']}_{record['region']}"
                if key not in sku_region_performance:
                    sku_region_performance[key] = []
                sku_region_performance[key].append(record['actual_revenue'])
        
        # Identify top and bottom performers
        if sku_region_performance:
            avg_revenues = {k: statistics.mean(v) for k, v in sku_region_performance.items()}
            
            if len(avg_revenues) >= 3:
                sorted_performers = sorted(avg_revenues.items(), key=lambda x: x[1], reverse=True)
                top_performer = sorted_performers[0]
                bottom_performer = sorted_performers[-1]
                
                insights.append({
                    'type': 'performance_variance',
                    'message': f'Top performer: {top_performer[0]} (avg revenue: {top_performer[1]:.2f})',
                    'severity': 'info'
                })
                
                insights.append({
                    'type': 'performance_variance',
                    'message': f'Bottom performer: {bottom_performer[0]} (avg revenue: {bottom_performer[1]:.2f})',
                    'severity': 'info'
                })
                
                recommendations.append(f'Analyze pricing strategy for {bottom_performer[0]} to improve performance')
        
        # Analyze price deviation
        price_deviations = []
        for record in self.performance_history:
            if record['recommended_price'] > 0:
                deviation = abs(record['actual_price_used'] - record['recommended_price']) / record['recommended_price']
                price_deviations.append(deviation)
        
        if price_deviations:
            avg_deviation = statistics.mean(price_deviations)
            if avg_deviation > 0.10:  # More than 10% average deviation
                insights.append({
                    'type': 'high_price_deviation',
                    'message': f'Average price deviation from recommendations: {avg_deviation*100:.1f}%',
                    'severity': 'medium'
                })
                recommendations.append('Investigate reasons for high price deviations from recommendations')
        
        return {
            'insights': insights,
            'recommendations': recommendations,
            'metrics': metrics
        }
    
    def persist_pricing_data(self, pricing_results: Dict[str, Any], confidence: float):
        """
        Persist pricing data to DynamoDB and S3
        
        Args:
            pricing_results: Pricing results dictionary
            confidence: Confidence level of the recommendations
        """
        timestamp = datetime.now(timezone.utc)
        
        # Persist pricing recommendations to DynamoDB
        if pricing_results.get('price_recommendations'):
            pricing_entity = BusinessIntelligence(
                entity_type=EntityType.PRICING,
                entity_id=f"pricing-{timestamp.strftime('%Y%m%d-%H%M%S')}",
                insights=Insights(
                    trend='pricing_optimization',
                    prediction={
                        'recommendation_count': len(pricing_results['price_recommendations']),
                        'avg_margin': statistics.mean([
                            r.expected_margin for r in pricing_results['price_recommendations']
                        ]) if pricing_results['price_recommendations'] else 0.0,
                        'competitive_analysis_count': len(pricing_results.get('competitive_analysis', {}))
                    },
                    confidence=confidence,
                    timeframe='current'
                ),
                recommendations=self._create_recommendations(pricing_results),
                data_source=['pricing_optimization_agent']
            )
            self.bi_repository.create(pricing_entity)
        
        # Store detailed pricing data in S3
        s3_key = f"pricing-recommendations/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-recommendations.json"
        self.s3_repository.upload_json(
            data={
                'timestamp': timestamp.isoformat(),
                'recommendations': [
                    {
                        'sku': r.sku,
                        'region': r.region,
                        'current_price': r.current_price,
                        'recommended_price': r.recommended_price,
                        'expected_margin': r.expected_margin,
                        'competitive_position': r.competitive_position,
                        'elasticity_impact': r.elasticity_impact,
                        'confidence': r.confidence
                    }
                    for r in pricing_results.get('price_recommendations', [])
                ],
                'competitive_analysis': pricing_results.get('competitive_analysis', {}),
                'elasticity_simulations': pricing_results.get('elasticity_simulations', {}),
                'overall_confidence': confidence
            },
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'recommendation_date': timestamp.strftime('%Y-%m-%d')
            }
        )
    
    def _create_recommendations(self, pricing_results: Dict[str, Any]) -> List[ActionRecommendation]:
        """
        Create action recommendations from pricing results
        
        Args:
            pricing_results: Pricing results dictionary
            
        Returns:
            List of ActionRecommendation objects
        """
        recommendations = []
        
        price_recs = pricing_results.get('price_recommendations', [])
        
        if not price_recs:
            return [
                ActionRecommendation(
                    action='Collect more pricing data for analysis',
                    priority=Priority.MEDIUM,
                    expected_impact='Enable pricing optimization'
                )
            ]
        
        # Identify high-impact pricing opportunities
        high_margin_opportunities = [
            r for r in price_recs 
            if r.expected_margin > 0.30 and r.confidence > 0.7
        ]
        
        if high_margin_opportunities:
            recommendations.append(ActionRecommendation(
                action=f'Implement pricing changes for {len(high_margin_opportunities)} high-margin SKUs',
                priority=Priority.HIGH,
                expected_impact='Increase profitability while maintaining competitiveness'
            ))
        
        # Identify competitive pricing adjustments
        below_market = [
            r for r in price_recs 
            if r.competitive_position == 'below' and r.recommended_price > r.current_price
        ]
        
        if below_market:
            recommendations.append(ActionRecommendation(
                action=f'Increase prices for {len(below_market)} SKUs currently below market',
                priority=Priority.MEDIUM,
                expected_impact='Capture additional margin without losing competitiveness'
            ))
        
        # Identify elasticity-based opportunities
        positive_revenue_impact = [
            r for r in price_recs 
            if r.elasticity_impact.get('revenue_change_pct', 0) > 0.05
        ]
        
        if positive_revenue_impact:
            recommendations.append(ActionRecommendation(
                action=f'Optimize prices for {len(positive_revenue_impact)} SKUs with positive revenue impact',
                priority=Priority.HIGH,
                expected_impact='Increase revenue through strategic pricing'
            ))
        
        if not recommendations:
            recommendations.append(ActionRecommendation(
                action='Monitor pricing performance and market conditions',
                priority=Priority.LOW,
                expected_impact='Maintain pricing competitiveness'
            ))
        
        return recommendations
    
    def _calculate_confidence(
        self,
        pricing_data: List[PricingData],
        price_recommendations: List[PriceRecommendation]
    ) -> float:
        """
        Calculate overall confidence based on data quality
        
        Args:
            pricing_data: Input pricing data
            price_recommendations: Generated recommendations
            
        Returns:
            Confidence level (0.0 to 1.0)
        """
        if not pricing_data or not price_recommendations:
            return 0.5
        
        # Calculate average recommendation confidence
        avg_rec_confidence = statistics.mean([r.confidence for r in price_recommendations])
        
        # Adjust based on data volume
        data_volume_factor = min(len(pricing_data) / 100, 1.0)  # Cap at 100 data points
        
        # Combine factors
        overall_confidence = (avg_rec_confidence * 0.7) + (data_volume_factor * 0.3)
        
        return min(overall_confidence, 0.95)
    
    def _generate_recommendations(self, pricing_results: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations from pricing results
        
        Args:
            pricing_results: Pricing results dictionary
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        price_recs = pricing_results.get('price_recommendations', [])
        
        if price_recs:
            recommendations.append(f"Review {len(price_recs)} pricing recommendations")
            
            # Check for high-impact opportunities
            high_impact = [r for r in price_recs if r.elasticity_impact.get('revenue_change_pct', 0) > 0.05]
            if high_impact:
                recommendations.append(f"Prioritize {len(high_impact)} high-impact pricing changes")
        
        competitive_analysis = pricing_results.get('competitive_analysis', {})
        if competitive_analysis:
            recommendations.append(f"Monitor competitive position for {len(competitive_analysis)} SKUs")
        
        return recommendations if recommendations else ["Continue monitoring pricing data"]
    
    def handle_message(self, message: ACPMessage) -> Optional[Dict[str, Any]]:
        """
        Handle incoming messages from other agents or AI Council
        
        Args:
            message: ACPMessage to handle
            
        Returns:
            Response payload if applicable
        """
        if message.message_type == MessageType.REQUEST:
            return self._handle_pricing_request(message)
        elif message.message_type == MessageType.BROADCAST:
            return self._handle_broadcast(message)
        elif message.message_type == MessageType.NOTIFICATION:
            return self._handle_notification(message)
        else:
            print(f"Unknown message type: {message.message_type}")
            return None
    
    def _handle_pricing_request(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle request for pricing data"""
        request_type = message.payload.get('request_type')
        
        if request_type == 'pricing_recommendations':
            entities = self.bi_repository.get_by_type(EntityType.PRICING.value, limit=10)
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
        """Handle broadcast messages from AI Council"""
        print(f"Received broadcast from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
    
    def _handle_notification(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle notification messages"""
        print(f"Received notification from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
