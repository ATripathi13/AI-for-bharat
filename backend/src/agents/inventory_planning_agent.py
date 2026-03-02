"""
Inventory Planning Agent for RetailMind AI
Handles overstock/stockout detection, inventory optimization, and stock rebalancing
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
class InventoryLevel:
    """Current inventory level data"""
    sku: str
    region: str
    current_stock: float
    reorder_point: float
    max_stock: float
    timestamp: datetime


@dataclass
class DemandForecastData:
    """Demand forecast data for inventory planning"""
    sku: str
    region: str
    predicted_demand: float
    forecast_horizon_days: int


@dataclass
class InventoryPlanningInput:
    """Input data for Inventory Planning Agent"""
    inventory_levels: List[InventoryLevel]
    demand_forecasts: List[DemandForecastData]
    lead_time_days: int = 7


@dataclass
class StockCondition:
    """Stock condition detection result"""
    sku: str
    region: str
    condition: str  # 'overstock', 'stockout', 'optimal', 'approaching_stockout'
    current_stock: float
    recommended_action: str
    urgency: str  # 'high', 'medium', 'low'


@dataclass
class InventoryRecommendation:
    """Inventory optimization recommendation"""
    sku: str
    region: str
    action_type: str  # 'reorder', 'reduce', 'rebalance', 'maintain'
    reorder_quantity: Optional[float]
    target_stock: float
    reasoning: str


class InventoryPlanningAgent(BaseAgent):
    """
    Inventory Planning Agent
    Detects overstock/stockout conditions and provides inventory optimization recommendations
    """
    
    def __init__(
        self, 
        agent_id: str = "inventory-planning-agent",
        s3_bucket: str = "retailmind-inventory-planning",
        register_with_council: bool = True
    ):
        """
        Initialize Inventory Planning Agent
        
        Args:
            agent_id: Unique identifier for the agent
            s3_bucket: S3 bucket for storing inventory planning data
            register_with_council: Whether to register with AI Council on initialization
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="inventory_planning",
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
            print(f"Inventory Planning Agent {self.metadata.agent_id} registered successfully")
        except Exception as e:
            print(f"Failed to register Inventory Planning Agent: {str(e)}")
            raise
    
    def unregister(self):
        """Unregister this agent from the AI Council"""
        try:
            self.registry.unregister_agent(self.metadata.agent_id)
            print(f"Inventory Planning Agent {self.metadata.agent_id} unregistered successfully")
        except Exception as e:
            print(f"Failed to unregister Inventory Planning Agent: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "overstock_detection",
            "stockout_detection",
            "inventory_optimization",
            "stock_rebalancing",
            "supply_demand_mismatch_detection"
        ]
    
    def process(self, input_data: InventoryPlanningInput) -> AgentDecision:
        """
        Process inventory levels and demand forecasts to generate recommendations
        
        Args:
            input_data: InventoryPlanningInput with inventory and forecast data
            
        Returns:
            AgentDecision with inventory recommendations
        """
        # Detect overstock and stockout conditions
        stock_conditions = self.detect_stock_conditions(
            input_data.inventory_levels,
            input_data.demand_forecasts,
            input_data.lead_time_days
        )
        
        # Generate inventory optimization recommendations
        optimization_recommendations = self.generate_optimization_recommendations(
            input_data.inventory_levels,
            input_data.demand_forecasts,
            input_data.lead_time_days
        )
        
        # Implement stock rebalancing logic
        rebalancing_plan = self.generate_rebalancing_plan(
            input_data.inventory_levels,
            stock_conditions
        )
        
        # Detect supply-demand mismatches
        mismatches = self.detect_supply_demand_mismatch(
            input_data.inventory_levels,
            input_data.demand_forecasts
        )
        
        # Aggregate results
        planning_results = {
            'stock_conditions': stock_conditions,
            'optimization_recommendations': optimization_recommendations,
            'rebalancing_plan': rebalancing_plan,
            'supply_demand_mismatches': mismatches
        }
        
        # Calculate confidence based on data quality
        confidence = self._calculate_confidence(input_data)
        
        # Generate action recommendations
        recommendations = self._generate_recommendations(planning_results)
        
        # Create decision
        decision = self.create_decision(
            input_data=input_data,
            action="inventory_planning_update",
            confidence=confidence,
            reasoning=f"Analyzed {len(input_data.inventory_levels)} inventory positions with {len(input_data.demand_forecasts)} demand forecasts",
            supporting_data=[planning_results, recommendations]
        )
        
        # Persist inventory planning data
        self.persist_planning_data(planning_results, confidence)
        
        return decision
    
    def detect_stock_conditions(
        self,
        inventory_levels: List[InventoryLevel],
        demand_forecasts: List[DemandForecastData],
        lead_time_days: int
    ) -> List[StockCondition]:
        """
        Detect overstock and stockout conditions in real-time
        
        Args:
            inventory_levels: Current inventory levels
            demand_forecasts: Demand forecasts
            lead_time_days: Lead time for replenishment
            
        Returns:
            List of StockCondition objects
        """
        conditions = []
        
        # Create forecast lookup
        forecast_map = {
            (f.sku, f.region): f for f in demand_forecasts
        }
        
        for inventory in inventory_levels:
            key = (inventory.sku, inventory.region)
            forecast = forecast_map.get(key)
            
            if not forecast:
                # No forecast available, use basic thresholds
                condition = self._detect_condition_without_forecast(inventory)
            else:
                # Use forecast to detect condition
                condition = self._detect_condition_with_forecast(
                    inventory, forecast, lead_time_days
                )
            
            conditions.append(condition)
        
        return conditions
    
    def _detect_condition_without_forecast(
        self, inventory: InventoryLevel
    ) -> StockCondition:
        """Detect stock condition without forecast data"""
        if inventory.current_stock <= inventory.reorder_point:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='stockout',
                current_stock=inventory.current_stock,
                recommended_action='Immediate reorder required',
                urgency='high'
            )
        elif inventory.current_stock >= inventory.max_stock:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='overstock',
                current_stock=inventory.current_stock,
                recommended_action='Reduce inventory or increase sales efforts',
                urgency='medium'
            )
        elif inventory.current_stock <= inventory.reorder_point * 1.5:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='approaching_stockout',
                current_stock=inventory.current_stock,
                recommended_action='Plan reorder soon',
                urgency='medium'
            )
        else:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='optimal',
                current_stock=inventory.current_stock,
                recommended_action='Maintain current levels',
                urgency='low'
            )
    
    def _detect_condition_with_forecast(
        self,
        inventory: InventoryLevel,
        forecast: DemandForecastData,
        lead_time_days: int
    ) -> StockCondition:
        """Detect stock condition using forecast data"""
        # Calculate expected demand during lead time
        daily_demand = forecast.predicted_demand / forecast.forecast_horizon_days
        lead_time_demand = daily_demand * lead_time_days
        
        # If demand is zero or near-zero, fall back to basic threshold logic
        if daily_demand < 0.01:
            return self._detect_condition_without_forecast(inventory)
        
        # Calculate days of inventory remaining
        days_remaining = inventory.current_stock / daily_demand
        
        if days_remaining <= lead_time_days:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='stockout',
                current_stock=inventory.current_stock,
                recommended_action=f'Immediate reorder: {lead_time_demand:.2f} units needed',
                urgency='high'
            )
        elif days_remaining <= lead_time_days * 1.5:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='approaching_stockout',
                current_stock=inventory.current_stock,
                recommended_action=f'Plan reorder: {lead_time_demand:.2f} units recommended',
                urgency='medium'
            )
        elif days_remaining >= forecast.forecast_horizon_days * 2:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='overstock',
                current_stock=inventory.current_stock,
                recommended_action='Reduce inventory or increase sales efforts',
                urgency='medium'
            )
        else:
            return StockCondition(
                sku=inventory.sku,
                region=inventory.region,
                condition='optimal',
                current_stock=inventory.current_stock,
                recommended_action='Maintain current levels',
                urgency='low'
            )
    
    def generate_optimization_recommendations(
        self,
        inventory_levels: List[InventoryLevel],
        demand_forecasts: List[DemandForecastData],
        lead_time_days: int
    ) -> List[InventoryRecommendation]:
        """
        Generate inventory optimization recommendations with specific reorder quantities
        
        Args:
            inventory_levels: Current inventory levels
            demand_forecasts: Demand forecasts
            lead_time_days: Lead time for replenishment
            
        Returns:
            List of InventoryRecommendation objects
        """
        recommendations = []
        
        # Create forecast lookup
        forecast_map = {
            (f.sku, f.region): f for f in demand_forecasts
        }
        
        for inventory in inventory_levels:
            key = (inventory.sku, inventory.region)
            forecast = forecast_map.get(key)
            
            if not forecast:
                # Without forecast, use basic reorder point logic
                recommendation = self._generate_basic_recommendation(inventory)
            else:
                # Use forecast for optimization
                recommendation = self._generate_forecast_based_recommendation(
                    inventory, forecast, lead_time_days
                )
            
            recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_basic_recommendation(
        self, inventory: InventoryLevel
    ) -> InventoryRecommendation:
        """Generate basic recommendation without forecast"""
        if inventory.current_stock <= inventory.reorder_point:
            reorder_qty = inventory.max_stock - inventory.current_stock
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='reorder',
                reorder_quantity=reorder_qty,
                target_stock=inventory.max_stock,
                reasoning='Stock below reorder point'
            )
        elif inventory.current_stock >= inventory.max_stock:
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='reduce',
                reorder_quantity=None,
                target_stock=inventory.max_stock * 0.8,
                reasoning='Overstock condition detected'
            )
        else:
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='maintain',
                reorder_quantity=None,
                target_stock=inventory.current_stock,
                reasoning='Inventory levels optimal'
            )
    
    def _generate_forecast_based_recommendation(
        self,
        inventory: InventoryLevel,
        forecast: DemandForecastData,
        lead_time_days: int
    ) -> InventoryRecommendation:
        """Generate recommendation using forecast data"""
        # Calculate expected demand
        daily_demand = forecast.predicted_demand / forecast.forecast_horizon_days
        lead_time_demand = daily_demand * lead_time_days
        
        # Calculate safety stock (20% of lead time demand)
        safety_stock = lead_time_demand * 0.2
        
        # Calculate optimal stock level (lead time demand + safety stock + cycle stock)
        cycle_stock = daily_demand * 7  # 1 week of demand
        target_stock = lead_time_demand + safety_stock + cycle_stock
        
        # Calculate days of inventory
        days_remaining = inventory.current_stock / daily_demand if daily_demand > 0 else float('inf')
        
        if days_remaining <= lead_time_days:
            # Need immediate reorder
            reorder_qty = target_stock - inventory.current_stock
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='reorder',
                reorder_quantity=max(0, reorder_qty),
                target_stock=target_stock,
                reasoning=f'Stock will run out in {days_remaining:.1f} days, reorder needed'
            )
        elif days_remaining <= lead_time_days * 1.5:
            # Plan reorder soon
            reorder_qty = target_stock - inventory.current_stock
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='reorder',
                reorder_quantity=max(0, reorder_qty),
                target_stock=target_stock,
                reasoning=f'Stock approaching reorder point, {days_remaining:.1f} days remaining'
            )
        elif days_remaining >= forecast.forecast_horizon_days * 2:
            # Overstock - consider reducing
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='reduce',
                reorder_quantity=None,
                target_stock=target_stock,
                reasoning=f'Overstock detected, {days_remaining:.1f} days of inventory'
            )
        else:
            # Optimal level
            return InventoryRecommendation(
                sku=inventory.sku,
                region=inventory.region,
                action_type='maintain',
                reorder_quantity=None,
                target_stock=inventory.current_stock,
                reasoning='Inventory levels optimal'
            )
    
    def generate_rebalancing_plan(
        self,
        inventory_levels: List[InventoryLevel],
        stock_conditions: List[StockCondition]
    ) -> Dict[str, Any]:
        """
        Implement stock rebalancing logic across regions
        
        Args:
            inventory_levels: Current inventory levels
            stock_conditions: Detected stock conditions
            
        Returns:
            Dictionary with rebalancing plan
        """
        # Group by SKU
        sku_inventory = {}
        sku_conditions = {}
        
        for inventory in inventory_levels:
            if inventory.sku not in sku_inventory:
                sku_inventory[inventory.sku] = []
            sku_inventory[inventory.sku].append(inventory)
        
        for condition in stock_conditions:
            if condition.sku not in sku_conditions:
                sku_conditions[condition.sku] = []
            sku_conditions[condition.sku].append(condition)
        
        # Generate rebalancing recommendations
        rebalancing_actions = []
        
        for sku, inventories in sku_inventory.items():
            conditions = sku_conditions.get(sku, [])
            
            # Find overstock and stockout regions
            overstock_regions = [
                (inv, cond) for inv, cond in zip(inventories, conditions)
                if cond.condition == 'overstock'
            ]
            stockout_regions = [
                (inv, cond) for inv, cond in zip(inventories, conditions)
                if cond.condition in ['stockout', 'approaching_stockout']
            ]
            
            # Generate rebalancing actions
            for overstock_inv, overstock_cond in overstock_regions:
                for stockout_inv, stockout_cond in stockout_regions:
                    # Calculate transfer quantity
                    excess = overstock_inv.current_stock - overstock_inv.max_stock * 0.8
                    needed = stockout_inv.reorder_point - stockout_inv.current_stock
                    
                    if excess > 0 and needed > 0:
                        transfer_qty = min(excess, needed)
                        rebalancing_actions.append({
                            'sku': sku,
                            'from_region': overstock_inv.region,
                            'to_region': stockout_inv.region,
                            'quantity': transfer_qty,
                            'priority': 'high' if stockout_cond.condition == 'stockout' else 'medium',
                            'reasoning': f'Transfer excess from {overstock_inv.region} to address shortage in {stockout_inv.region}'
                        })
        
        return {
            'rebalancing_actions': rebalancing_actions,
            'total_transfers': len(rebalancing_actions),
            'summary': f'Generated {len(rebalancing_actions)} rebalancing actions across {len(sku_inventory)} SKUs'
        }
    
    def detect_supply_demand_mismatch(
        self,
        inventory_levels: List[InventoryLevel],
        demand_forecasts: List[DemandForecastData]
    ) -> List[Dict[str, Any]]:
        """
        Detect supply-demand mismatch conditions
        
        Args:
            inventory_levels: Current inventory levels
            demand_forecasts: Demand forecasts
            
        Returns:
            List of mismatch detections
        """
        mismatches = []
        
        # Create inventory lookup
        inventory_map = {
            (inv.sku, inv.region): inv for inv in inventory_levels
        }
        
        for forecast in demand_forecasts:
            key = (forecast.sku, forecast.region)
            inventory = inventory_map.get(key)
            
            if not inventory:
                # No inventory data for forecasted demand
                mismatches.append({
                    'sku': forecast.sku,
                    'region': forecast.region,
                    'mismatch_type': 'missing_inventory_data',
                    'predicted_demand': forecast.predicted_demand,
                    'current_supply': 0,
                    'severity': 'high',
                    'recommendation': 'Set up inventory tracking for this SKU-region'
                })
                continue
            
            # Calculate supply-demand ratio
            daily_demand = forecast.predicted_demand / forecast.forecast_horizon_days
            days_of_supply = inventory.current_stock / daily_demand if daily_demand > 0 else float('inf')
            
            if days_of_supply < 7:
                mismatches.append({
                    'sku': forecast.sku,
                    'region': forecast.region,
                    'mismatch_type': 'supply_shortage',
                    'predicted_demand': forecast.predicted_demand,
                    'current_supply': inventory.current_stock,
                    'days_of_supply': days_of_supply,
                    'severity': 'high' if days_of_supply < 3 else 'medium',
                    'recommendation': f'Increase supply to meet {forecast.forecast_horizon_days}-day demand'
                })
            elif days_of_supply > forecast.forecast_horizon_days * 2:
                mismatches.append({
                    'sku': forecast.sku,
                    'region': forecast.region,
                    'mismatch_type': 'supply_excess',
                    'predicted_demand': forecast.predicted_demand,
                    'current_supply': inventory.current_stock,
                    'days_of_supply': days_of_supply,
                    'severity': 'low',
                    'recommendation': 'Consider reducing inventory or increasing sales efforts'
                })
        
        return mismatches
    
    def persist_planning_data(self, planning_results: Dict[str, Any], confidence: float):
        """
        Persist inventory planning data to DynamoDB and S3
        
        Args:
            planning_results: Planning results dictionary
            confidence: Confidence level of the recommendations
        """
        timestamp = datetime.now(timezone.utc)
        
        # Persist inventory intelligence to DynamoDB
        if planning_results.get('optimization_recommendations'):
            inventory_entity = BusinessIntelligence(
                entity_type=EntityType.INVENTORY,
                entity_id=f"inventory-{timestamp.strftime('%Y%m%d-%H%M%S')}",
                insights=Insights(
                    trend='inventory_optimization',
                    prediction={
                        'recommendations_count': len(planning_results['optimization_recommendations']),
                        'rebalancing_actions': planning_results['rebalancing_plan'].get('total_transfers', 0),
                        'mismatches_detected': len(planning_results.get('supply_demand_mismatches', []))
                    },
                    confidence=confidence,
                    timeframe='current'
                ),
                recommendations=self._create_recommendations(planning_results),
                data_source=['inventory_planning_agent']
            )
            self.bi_repository.create(inventory_entity)
        
        # Store detailed planning data in S3
        s3_key = f"inventory-planning/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-planning.json"
        self.s3_repository.upload_json(
            data={
                'timestamp': timestamp.isoformat(),
                'stock_conditions': [
                    {
                        'sku': c.sku,
                        'region': c.region,
                        'condition': c.condition,
                        'current_stock': c.current_stock,
                        'recommended_action': c.recommended_action,
                        'urgency': c.urgency
                    }
                    for c in planning_results.get('stock_conditions', [])
                ],
                'optimization_recommendations': [
                    {
                        'sku': r.sku,
                        'region': r.region,
                        'action_type': r.action_type,
                        'reorder_quantity': r.reorder_quantity,
                        'target_stock': r.target_stock,
                        'reasoning': r.reasoning
                    }
                    for r in planning_results.get('optimization_recommendations', [])
                ],
                'rebalancing_plan': planning_results.get('rebalancing_plan', {}),
                'supply_demand_mismatches': planning_results.get('supply_demand_mismatches', []),
                'confidence': confidence
            },
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'planning_date': timestamp.strftime('%Y-%m-%d')
            }
        )
    
    def _create_recommendations(self, planning_results: Dict[str, Any]) -> List[ActionRecommendation]:
        """Create action recommendations from planning results"""
        recommendations = []
        
        # Check for critical stockouts
        stock_conditions = planning_results.get('stock_conditions', [])
        critical_stockouts = [c for c in stock_conditions if c.condition == 'stockout']
        
        if critical_stockouts:
            recommendations.append(ActionRecommendation(
                action=f'Address {len(critical_stockouts)} critical stockout conditions immediately',
                priority=Priority.HIGH,
                expected_impact='Prevent lost sales and customer dissatisfaction'
            ))
        
        # Check for rebalancing opportunities
        rebalancing_plan = planning_results.get('rebalancing_plan', {})
        if rebalancing_plan.get('total_transfers', 0) > 0:
            recommendations.append(ActionRecommendation(
                action=f'Execute {rebalancing_plan["total_transfers"]} stock rebalancing transfers',
                priority=Priority.MEDIUM,
                expected_impact='Optimize inventory distribution across regions'
            ))
        
        # Check for supply-demand mismatches
        mismatches = planning_results.get('supply_demand_mismatches', [])
        high_severity_mismatches = [m for m in mismatches if m.get('severity') == 'high']
        
        if high_severity_mismatches:
            recommendations.append(ActionRecommendation(
                action=f'Address {len(high_severity_mismatches)} high-severity supply-demand mismatches',
                priority=Priority.HIGH,
                expected_impact='Align inventory with demand forecasts'
            ))
        
        if not recommendations:
            recommendations.append(ActionRecommendation(
                action='Continue monitoring inventory levels',
                priority=Priority.LOW,
                expected_impact='Maintain optimal inventory positions'
            ))
        
        return recommendations
    
    def _calculate_confidence(self, input_data: InventoryPlanningInput) -> float:
        """Calculate confidence based on data quality"""
        inventory_count = len(input_data.inventory_levels)
        forecast_count = len(input_data.demand_forecasts)
        
        # Base confidence on data availability
        if inventory_count == 0:
            return 0.0
        
        # Higher confidence when we have both inventory and forecast data
        if forecast_count == 0:
            return 0.6  # Lower confidence without forecasts
        
        # Calculate coverage ratio
        coverage_ratio = min(1.0, forecast_count / inventory_count)
        
        # Confidence increases with better coverage
        if coverage_ratio >= 0.9:
            return 0.95
        elif coverage_ratio >= 0.7:
            return 0.85
        elif coverage_ratio >= 0.5:
            return 0.75
        else:
            return 0.65
    
    def _generate_recommendations(self, planning_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations from planning results"""
        recommendations = []
        
        stock_conditions = planning_results.get('stock_conditions', [])
        stockouts = [c for c in stock_conditions if c.condition == 'stockout']
        overstocks = [c for c in stock_conditions if c.condition == 'overstock']
        
        if stockouts:
            recommendations.append(f"Address {len(stockouts)} stockout conditions immediately")
        
        if overstocks:
            recommendations.append(f"Reduce {len(overstocks)} overstock situations")
        
        rebalancing_actions = planning_results.get('rebalancing_plan', {}).get('total_transfers', 0)
        if rebalancing_actions > 0:
            recommendations.append(f"Execute {rebalancing_actions} stock rebalancing transfers")
        
        mismatches = planning_results.get('supply_demand_mismatches', [])
        if mismatches:
            recommendations.append(f"Address {len(mismatches)} supply-demand mismatches")
        
        return recommendations if recommendations else ["Continue monitoring inventory levels"]
    
    def handle_message(self, message: ACPMessage) -> Optional[Dict[str, Any]]:
        """
        Handle incoming messages from other agents or AI Council
        
        Args:
            message: ACPMessage to handle
            
        Returns:
            Response payload if applicable
        """
        if message.message_type == MessageType.REQUEST:
            return self._handle_inventory_request(message)
        elif message.message_type == MessageType.BROADCAST:
            return self._handle_broadcast(message)
        elif message.message_type == MessageType.NOTIFICATION:
            return self._handle_notification(message)
        else:
            print(f"Unknown message type: {message.message_type}")
            return None
    
    def _handle_inventory_request(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle request for inventory planning data"""
        request_type = message.payload.get('request_type')
        
        if request_type == 'inventory_status':
            entities = self.bi_repository.get_by_type(EntityType.INVENTORY.value, limit=10)
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
    
    def request_demand_forecasts(
        self,
        sku_region_pairs: List[tuple[str, str]],
        correlation_id: str
    ) -> List[DemandForecastData]:
        """
        Request demand forecasts from Demand Forecast Agent
        
        Args:
            sku_region_pairs: List of (sku, region) tuples to get forecasts for
            correlation_id: Correlation ID for tracking
            
        Returns:
            List of DemandForecastData objects
        """
        # Send request to Demand Forecast Agent
        response = self.communication.send_request(
            from_agent_id=self.metadata.agent_id,
            to_agent_id="demand-forecast-agent",
            payload={
                'request_type': 'demand_forecast',
                'sku_region_pairs': sku_region_pairs
            },
            correlation_id=correlation_id
        )
        
        # Parse response and convert to DemandForecastData objects
        demand_forecasts = []
        if response and response.get('status') == 'success':
            forecast_data = response.get('data', [])
            for item in forecast_data:
                # Extract forecast information from business intelligence entity
                insights = item.get('insights', {})
                prediction = insights.get('prediction', {})
                
                # Create DemandForecastData objects from the response
                # This is a simplified conversion - in production, you'd parse the full structure
                if 'sku_forecasts' in prediction:
                    for forecast in prediction['sku_forecasts']:
                        demand_forecasts.append(DemandForecastData(
                            sku=forecast.get('sku', ''),
                            region=forecast.get('region', ''),
                            predicted_demand=forecast.get('predicted_demand', 0.0),
                            forecast_horizon_days=30  # Default horizon
                        ))
        
        return demand_forecasts
    
    def process_with_demand_forecasts(
        self,
        inventory_levels: List[InventoryLevel],
        lead_time_days: int = 7,
        correlation_id: Optional[str] = None
    ) -> AgentDecision:
        """
        Process inventory planning with automatic demand forecast retrieval
        
        Args:
            inventory_levels: Current inventory levels
            lead_time_days: Lead time for replenishment
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            AgentDecision with inventory recommendations
        """
        import uuid
        
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        # Extract SKU-region pairs from inventory
        sku_region_pairs = [(inv.sku, inv.region) for inv in inventory_levels]
        
        # Request demand forecasts from Demand Forecast Agent
        demand_forecasts = self.request_demand_forecasts(sku_region_pairs, correlation_id)
        
        # Create input with retrieved forecasts
        input_data = InventoryPlanningInput(
            inventory_levels=inventory_levels,
            demand_forecasts=demand_forecasts,
            lead_time_days=lead_time_days
        )
        
        # Process with standard logic
        return self.process(input_data)
