"""
Demand Forecast Agent for RetailMind AI
Handles time-series forecasting, SKU-level demand prediction, and region-wise sales forecasting
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
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
class HistoricalSalesData:
    """Historical sales data point"""
    sku: str
    region: str
    sales_volume: float
    timestamp: datetime
    price: Optional[float] = None


@dataclass
class DemandForecast:
    """Demand forecast result"""
    sku: str
    region: str
    forecast_date: datetime
    predicted_demand: float
    confidence_interval: tuple[float, float]
    accuracy: Optional[float] = None


@dataclass
class DemandForecastInput:
    """Input data for Demand Forecast Agent"""
    historical_sales: List[HistoricalSalesData]
    forecast_horizon_days: int = 30
    region_filter: Optional[str] = None
    sku_filter: Optional[str] = None


class DemandForecastAgent(BaseAgent):
    """
    Demand Forecast Agent
    Generates SKU-level demand forecasts and region-wise sales predictions
    """
    
    def __init__(
        self, 
        agent_id: str = "demand-forecast-agent",
        s3_bucket: str = "retailmind-demand-forecasts",
        sagemaker_endpoint: Optional[str] = None,
        register_with_council: bool = True
    ):
        """
        Initialize Demand Forecast Agent
        
        Args:
            agent_id: Unique identifier for the agent
            s3_bucket: S3 bucket for storing forecast data
            sagemaker_endpoint: SageMaker endpoint for ML model inference
            register_with_council: Whether to register with AI Council on initialization
        """
        super().__init__(
            agent_id=agent_id,
            agent_type="demand_forecast",
            version="1.0.0"
        )
        
        # Initialize communication and registry
        self.communication = AgentCommunicationInterface()
        self.registry = AgentRegistry()
        
        # Initialize data persistence
        self.bi_repository = BusinessIntelligenceRepository()
        self.s3_repository = S3Repository(s3_bucket)
        
        # SageMaker configuration
        self.sagemaker_endpoint = sagemaker_endpoint
        
        # Forecast accuracy tracking
        self.accuracy_history: List[Dict[str, Any]] = []
        
        # Register with AI Council if requested
        if register_with_council:
            self.register()
    
    def register(self):
        """Register this agent with the AI Council"""
        try:
            self.registry.register_agent(self.metadata)
            print(f"Demand Forecast Agent {self.metadata.agent_id} registered successfully")
        except Exception as e:
            print(f"Failed to register Demand Forecast Agent: {str(e)}")
            raise
    
    def unregister(self):
        """Unregister this agent from the AI Council"""
        try:
            self.registry.unregister_agent(self.metadata.agent_id)
            print(f"Demand Forecast Agent {self.metadata.agent_id} unregistered successfully")
        except Exception as e:
            print(f"Failed to unregister Demand Forecast Agent: {str(e)}")
            raise
    
    def get_capabilities(self) -> List[str]:
        """Return agent capabilities"""
        return [
            "sku_level_forecasting",
            "region_wise_prediction",
            "time_series_analysis",
            "forecast_accuracy_tracking"
        ]
    
    def process(self, input_data: DemandForecastInput) -> AgentDecision:
        """
        Process historical sales data and generate demand forecasts
        
        Args:
            input_data: DemandForecastInput with historical sales data
            
        Returns:
            AgentDecision with demand forecasts
        """
        # Generate SKU-level forecasts
        sku_forecasts = self.generate_sku_forecasts(
            input_data.historical_sales,
            input_data.forecast_horizon_days,
            input_data.sku_filter
        )
        
        # Generate region-wise predictions
        region_forecasts = self.generate_region_forecasts(
            input_data.historical_sales,
            input_data.forecast_horizon_days,
            input_data.region_filter
        )
        
        # Track forecast accuracy
        accuracy_metrics = self.track_forecast_accuracy(sku_forecasts)
        
        # Aggregate results
        forecast_results = {
            'sku_forecasts': sku_forecasts,
            'region_forecasts': region_forecasts,
            'accuracy_metrics': accuracy_metrics
        }
        
        # Calculate confidence based on historical accuracy
        confidence = self._calculate_confidence(accuracy_metrics)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(forecast_results)
        
        # Create decision
        decision = self.create_decision(
            input_data=input_data,
            action="demand_forecast_update",
            confidence=confidence,
            reasoning=f"Generated forecasts for {len(sku_forecasts)} SKUs across {len(region_forecasts)} regions",
            supporting_data=[forecast_results, recommendations]
        )
        
        # Persist forecast data
        self.persist_forecasts(forecast_results, confidence)
        
        return decision
    
    def generate_sku_forecasts(
        self,
        historical_sales: List[HistoricalSalesData],
        forecast_horizon_days: int,
        sku_filter: Optional[str] = None
    ) -> List[DemandForecast]:
        """
        Generate SKU-level demand forecasts
        
        Args:
            historical_sales: Historical sales data
            forecast_horizon_days: Number of days to forecast
            sku_filter: Optional SKU filter
            
        Returns:
            List of DemandForecast objects
        """
        if not historical_sales:
            return []
        
        # Filter by SKU if specified
        if sku_filter:
            historical_sales = [s for s in historical_sales if s.sku == sku_filter]
        
        # Group by SKU and region
        sku_region_data = {}
        for sale in historical_sales:
            key = (sale.sku, sale.region)
            if key not in sku_region_data:
                sku_region_data[key] = []
            sku_region_data[key].append(sale)
        
        # Generate forecasts for each SKU-region combination
        forecasts = []
        for (sku, region), sales_data in sku_region_data.items():
            forecast = self._forecast_time_series(
                sku=sku,
                region=region,
                sales_data=sales_data,
                forecast_horizon_days=forecast_horizon_days
            )
            if forecast:
                forecasts.extend(forecast)
        
        return forecasts
    
    def generate_region_forecasts(
        self,
        historical_sales: List[HistoricalSalesData],
        forecast_horizon_days: int,
        region_filter: Optional[str] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Generate region-wise sales predictions
        
        Args:
            historical_sales: Historical sales data
            forecast_horizon_days: Number of days to forecast
            region_filter: Optional region filter
            
        Returns:
            Dictionary mapping regions to SKU forecasts
        """
        if not historical_sales:
            return {}
        
        # Filter by region if specified
        if region_filter:
            historical_sales = [s for s in historical_sales if s.region == region_filter]
        
        # Group by region
        region_data = {}
        for sale in historical_sales:
            if sale.region not in region_data:
                region_data[sale.region] = {}
            if sale.sku not in region_data[sale.region]:
                region_data[sale.region][sale.sku] = []
            region_data[sale.region][sale.sku].append(sale)
        
        # Generate region-wise predictions
        region_forecasts = {}
        for region, sku_data in region_data.items():
            region_forecasts[region] = {}
            for sku, sales_data in sku_data.items():
                # Calculate average demand for the forecast period
                if sales_data:
                    avg_demand = statistics.mean([s.sales_volume for s in sales_data])
                    region_forecasts[region][sku] = avg_demand * forecast_horizon_days
        
        return region_forecasts
    
    def _forecast_time_series(
        self,
        sku: str,
        region: str,
        sales_data: List[HistoricalSalesData],
        forecast_horizon_days: int
    ) -> List[DemandForecast]:
        """
        Forecast time series for a specific SKU-region combination
        
        Args:
            sku: SKU identifier
            region: Region identifier
            sales_data: Historical sales data
            forecast_horizon_days: Number of days to forecast
            
        Returns:
            List of DemandForecast objects
        """
        if not sales_data or len(sales_data) < 2:
            return []
        
        # Sort by timestamp
        sorted_sales = sorted(sales_data, key=lambda x: x.timestamp)
        
        # Use SageMaker endpoint if available, otherwise use simple forecasting
        if self.sagemaker_endpoint:
            return self._sagemaker_forecast(sku, region, sorted_sales, forecast_horizon_days)
        else:
            return self._simple_forecast(sku, region, sorted_sales, forecast_horizon_days)
    
    def _simple_forecast(
        self,
        sku: str,
        region: str,
        sorted_sales: List[HistoricalSalesData],
        forecast_horizon_days: int
    ) -> List[DemandForecast]:
        """
        Simple moving average forecast (fallback when SageMaker is not available)
        
        Args:
            sku: SKU identifier
            region: Region identifier
            sorted_sales: Sorted historical sales data
            forecast_horizon_days: Number of days to forecast
            
        Returns:
            List of DemandForecast objects
        """
        # Calculate moving average
        volumes = [s.sales_volume for s in sorted_sales]
        avg_volume = statistics.mean(volumes)
        std_volume = statistics.stdev(volumes) if len(volumes) > 1 else avg_volume * 0.1
        
        # Generate daily forecasts
        forecasts = []
        last_date = sorted_sales[-1].timestamp
        
        for day in range(1, forecast_horizon_days + 1):
            forecast_date = last_date + timedelta(days=day)
            
            # Simple forecast with confidence interval
            forecasts.append(DemandForecast(
                sku=sku,
                region=region,
                forecast_date=forecast_date,
                predicted_demand=avg_volume,
                confidence_interval=(
                    max(0, avg_volume - 1.96 * std_volume),
                    avg_volume + 1.96 * std_volume
                )
            ))
        
        return forecasts
    
    def _sagemaker_forecast(
        self,
        sku: str,
        region: str,
        sorted_sales: List[HistoricalSalesData],
        forecast_horizon_days: int
    ) -> List[DemandForecast]:
        """
        Generate forecast using SageMaker endpoint
        
        Args:
            sku: SKU identifier
            region: Region identifier
            sorted_sales: Sorted historical sales data
            forecast_horizon_days: Number of days to forecast
            
        Returns:
            List of DemandForecast objects
        """
        # TODO: Implement SageMaker integration
        # For now, fall back to simple forecast
        return self._simple_forecast(sku, region, sorted_sales, forecast_horizon_days)
    
    def track_forecast_accuracy(
        self,
        forecasts: List[DemandForecast]
    ) -> Dict[str, float]:
        """
        Track forecast accuracy by comparing predictions with actual outcomes
        
        Args:
            forecasts: List of forecasts to track
            
        Returns:
            Dictionary with accuracy metrics
        """
        if not forecasts:
            return {
                'overall_accuracy': 0.0,
                'forecast_count': 0,
                'tracked_count': 0
            }
        
        # Calculate accuracy for forecasts that have actual data
        accurate_forecasts = 0
        total_tracked = 0
        
        for forecast in forecasts:
            if forecast.accuracy is not None:
                total_tracked += 1
                if forecast.accuracy >= 0.85:  # 85% accuracy threshold
                    accurate_forecasts += 1
        
        overall_accuracy = (accurate_forecasts / total_tracked) if total_tracked > 0 else 0.0
        
        # Store in accuracy history
        accuracy_record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_accuracy': overall_accuracy,
            'forecast_count': len(forecasts),
            'tracked_count': total_tracked
        }
        self.accuracy_history.append(accuracy_record)
        
        return {
            'overall_accuracy': overall_accuracy,
            'forecast_count': len(forecasts),
            'tracked_count': total_tracked
        }
    
    def update_forecast_accuracy(
        self,
        sku: str,
        region: str,
        forecast_date: datetime,
        actual_demand: float
    ) -> Dict[str, Any]:
        """
        Update forecast accuracy with actual demand data (feedback loop)
        
        Args:
            sku: SKU identifier
            region: Region identifier
            forecast_date: Date of the forecast
            actual_demand: Actual demand observed
            
        Returns:
            Dictionary with accuracy update results
        """
        # Retrieve stored forecasts from S3
        # In a real implementation, this would query S3 for the specific forecast
        # For now, we'll create a placeholder implementation
        
        # Calculate accuracy metrics
        accuracy_update = {
            'sku': sku,
            'region': region,
            'forecast_date': forecast_date.isoformat(),
            'actual_demand': actual_demand,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'accuracy_calculated': True
        }
        
        # Store accuracy feedback for model retraining
        self._store_accuracy_feedback(accuracy_update)
        
        # Check if retraining is needed
        retraining_needed = self._check_retraining_trigger()
        
        if retraining_needed:
            accuracy_update['retraining_triggered'] = True
            self._trigger_model_retraining()
        else:
            accuracy_update['retraining_triggered'] = False
        
        return accuracy_update
    
    def _store_accuracy_feedback(self, accuracy_update: Dict[str, Any]):
        """
        Store accuracy feedback for continuous learning
        
        Args:
            accuracy_update: Accuracy update data
        """
        # Store feedback in S3 for model retraining
        timestamp = datetime.now(timezone.utc)
        s3_key = f"accuracy-feedback/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-feedback.json"
        
        self.s3_repository.upload_json(
            data=accuracy_update,
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'feedback_type': 'accuracy_update',
                'sku': accuracy_update['sku'],
                'region': accuracy_update['region']
            }
        )
    
    def _check_retraining_trigger(self) -> bool:
        """
        Check if model retraining should be triggered
        
        Returns:
            True if retraining is needed, False otherwise
        """
        # Check if we have enough accuracy history
        if len(self.accuracy_history) < 10:
            return False
        
        # Get recent accuracy metrics
        recent_accuracy = [h['overall_accuracy'] for h in self.accuracy_history[-10:]]
        
        # Trigger retraining if average accuracy drops below 80%
        avg_recent_accuracy = sum(recent_accuracy) / len(recent_accuracy)
        
        return avg_recent_accuracy < 0.80
    
    def _trigger_model_retraining(self):
        """
        Trigger model retraining with SageMaker
        
        This would initiate a SageMaker training job with updated data
        """
        # Create retraining request
        retraining_request = {
            'agent_id': self.metadata.agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': 'accuracy_degradation',
            'current_accuracy': self.accuracy_history[-1]['overall_accuracy'] if self.accuracy_history else 0.0,
            'target_accuracy': 0.85
        }
        
        # Store retraining request in S3
        timestamp = datetime.now(timezone.utc)
        s3_key = f"retraining-requests/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-request.json"
        
        self.s3_repository.upload_json(
            data=retraining_request,
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'request_type': 'model_retraining'
            }
        )
        
        print(f"Model retraining triggered for {self.metadata.agent_id}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance monitoring dashboard data
        
        Returns:
            Dictionary with performance metrics
        """
        if not self.accuracy_history:
            return {
                'total_forecasts': 0,
                'average_accuracy': 0.0,
                'recent_accuracy': 0.0,
                'accuracy_trend': 'no_data',
                'retraining_recommended': False
            }
        
        # Calculate overall metrics
        total_forecasts = sum(h['forecast_count'] for h in self.accuracy_history)
        all_accuracies = [h['overall_accuracy'] for h in self.accuracy_history if h['tracked_count'] > 0]
        
        if not all_accuracies:
            average_accuracy = 0.0
            recent_accuracy = 0.0
            accuracy_trend = 'no_data'
        else:
            average_accuracy = sum(all_accuracies) / len(all_accuracies)
            recent_accuracy = sum(all_accuracies[-5:]) / min(5, len(all_accuracies))
            
            # Determine trend
            if len(all_accuracies) >= 2:
                if recent_accuracy > average_accuracy * 1.05:
                    accuracy_trend = 'improving'
                elif recent_accuracy < average_accuracy * 0.95:
                    accuracy_trend = 'declining'
                else:
                    accuracy_trend = 'stable'
            else:
                accuracy_trend = 'insufficient_data'
        
        # Check if retraining is recommended
        retraining_recommended = self._check_retraining_trigger()
        
        return {
            'total_forecasts': total_forecasts,
            'average_accuracy': average_accuracy,
            'recent_accuracy': recent_accuracy,
            'accuracy_trend': accuracy_trend,
            'retraining_recommended': retraining_recommended,
            'history_length': len(self.accuracy_history)
        }
    
    def persist_forecasts(self, forecast_results: Dict[str, Any], confidence: float):
        """
        Persist forecast data to DynamoDB and S3
        
        Args:
            forecast_results: Forecast results dictionary
            confidence: Confidence level of the forecasts
        """
        timestamp = datetime.now(timezone.utc)
        
        # Persist demand forecasts to DynamoDB
        if forecast_results.get('sku_forecasts'):
            demand_entity = BusinessIntelligence(
                entity_type=EntityType.DEMAND,
                entity_id=f"forecast-{timestamp.strftime('%Y%m%d-%H%M%S')}",
                insights=Insights(
                    trend='demand_forecast',
                    prediction={
                        'sku_count': len(forecast_results['sku_forecasts']),
                        'region_count': len(forecast_results.get('region_forecasts', {})),
                        'accuracy': forecast_results['accuracy_metrics'].get('overall_accuracy', 0.0)
                    },
                    confidence=confidence,
                    timeframe='30d'
                ),
                recommendations=self._create_recommendations(forecast_results),
                data_source=['demand_forecast_agent']
            )
            self.bi_repository.create(demand_entity)
        
        # Store detailed forecasts in S3
        s3_key = f"demand-forecasts/{timestamp.strftime('%Y/%m/%d')}/{timestamp.strftime('%H%M%S')}-forecasts.json"
        self.s3_repository.upload_json(
            data={
                'timestamp': timestamp.isoformat(),
                'forecasts': {
                    'sku_forecasts': [
                        {
                            'sku': f.sku,
                            'region': f.region,
                            'forecast_date': f.forecast_date.isoformat(),
                            'predicted_demand': f.predicted_demand,
                            'confidence_interval': f.confidence_interval
                        }
                        for f in forecast_results.get('sku_forecasts', [])
                    ],
                    'region_forecasts': forecast_results.get('region_forecasts', {})
                },
                'accuracy_metrics': forecast_results.get('accuracy_metrics', {}),
                'confidence': confidence
            },
            s3_key=s3_key,
            metadata={
                'agent_id': self.metadata.agent_id,
                'forecast_date': timestamp.strftime('%Y-%m-%d')
            }
        )
    
    def _create_recommendations(self, forecast_results: Dict[str, Any]) -> List[ActionRecommendation]:
        """
        Create action recommendations from forecast results
        
        Args:
            forecast_results: Forecast results dictionary
            
        Returns:
            List of ActionRecommendation objects
        """
        recommendations = []
        
        accuracy = forecast_results.get('accuracy_metrics', {}).get('overall_accuracy', 0.0)
        
        if accuracy >= 0.85:
            recommendations.append(ActionRecommendation(
                action='Use forecasts for inventory planning and procurement',
                priority=Priority.HIGH,
                expected_impact='Optimized stock levels and reduced stockouts'
            ))
        else:
            recommendations.append(ActionRecommendation(
                action='Review forecast model and retrain with additional data',
                priority=Priority.MEDIUM,
                expected_impact='Improved forecast accuracy'
            ))
        
        # Check for high-demand SKUs
        sku_forecasts = forecast_results.get('sku_forecasts', [])
        if sku_forecasts:
            avg_demand = statistics.mean([f.predicted_demand for f in sku_forecasts])
            high_demand_skus = [f for f in sku_forecasts if f.predicted_demand > avg_demand * 1.5]
            
            if high_demand_skus:
                recommendations.append(ActionRecommendation(
                    action=f'Prioritize inventory for {len(high_demand_skus)} high-demand SKUs',
                    priority=Priority.HIGH,
                    expected_impact='Prevent stockouts for popular items'
                ))
        
        return recommendations if recommendations else [
            ActionRecommendation(
                action='Continue monitoring demand patterns',
                priority=Priority.LOW,
                expected_impact='Maintain forecast accuracy'
            )
        ]
    
    def _calculate_confidence(self, accuracy_metrics: Dict[str, float]) -> float:
        """Calculate confidence based on forecast accuracy"""
        overall_accuracy = accuracy_metrics.get('overall_accuracy', 0.0)
        tracked_count = accuracy_metrics.get('tracked_count', 0)
        
        # Base confidence on accuracy and sample size
        if tracked_count == 0:
            # No historical accuracy data, use moderate confidence
            return 0.7
        elif tracked_count < 10:
            # Limited data, reduce confidence
            return overall_accuracy * 0.8
        else:
            # Sufficient data, use accuracy directly
            return overall_accuracy
    
    def _generate_recommendations(self, forecast_results: Dict[str, Any]) -> List[str]:
        """Generate actionable recommendations from forecasts"""
        recommendations = []
        
        accuracy = forecast_results.get('accuracy_metrics', {}).get('overall_accuracy', 0.0)
        
        if accuracy >= 0.85:
            recommendations.append("Use forecasts for inventory planning")
        else:
            recommendations.append("Review and retrain forecast models")
        
        sku_count = len(forecast_results.get('sku_forecasts', []))
        if sku_count > 0:
            recommendations.append(f"Monitor {sku_count} SKUs for demand changes")
        
        return recommendations
    
    def handle_message(self, message: ACPMessage) -> Optional[Dict[str, Any]]:
        """
        Handle incoming messages from other agents or AI Council
        
        Args:
            message: ACPMessage to handle
            
        Returns:
            Response payload if applicable
        """
        if message.message_type == MessageType.REQUEST:
            return self._handle_forecast_request(message)
        elif message.message_type == MessageType.BROADCAST:
            return self._handle_broadcast(message)
        elif message.message_type == MessageType.NOTIFICATION:
            return self._handle_notification(message)
        else:
            print(f"Unknown message type: {message.message_type}")
            return None
    
    def _handle_forecast_request(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle request for demand forecast data"""
        request_type = message.payload.get('request_type')
        
        if request_type == 'demand_forecast':
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
        """Handle broadcast messages from AI Council"""
        print(f"Received broadcast from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}
    
    def _handle_notification(self, message: ACPMessage) -> Dict[str, Any]:
        """Handle notification messages"""
        print(f"Received notification from {message.agent_id}: {message.payload}")
        return {'status': 'acknowledged'}

    def check_retraining_trigger(self) -> bool:
        """
        Check if model retraining should be triggered based on accuracy degradation
        
        Returns:
            True if retraining should be triggered, False otherwise
        """
        if len(self.accuracy_history) < 10:
            # Need at least 10 accuracy measurements to detect degradation
            return False
        
        # Get recent accuracy (last 5 measurements)
        recent_accuracy = [h['overall_accuracy'] for h in self.accuracy_history[-5:]]
        
        # Get historical accuracy (previous 5 measurements)
        historical_accuracy = [h['overall_accuracy'] for h in self.accuracy_history[-10:-5]]
        
        if not recent_accuracy or not historical_accuracy:
            return False
        
        # Calculate average accuracy for both periods
        recent_avg = statistics.mean(recent_accuracy)
        historical_avg = statistics.mean(historical_accuracy)
        
        # Trigger retraining if accuracy has degraded by more than 10%
        if historical_avg > 0 and (historical_avg - recent_avg) / historical_avg > 0.1:
            return True
        
        # Also trigger if accuracy falls below 75%
        if recent_avg < 0.75:
            return True
        
        return False
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance monitoring dashboard data
        
        Returns:
            Dictionary with performance metrics for monitoring
        """
        if not self.accuracy_history:
            return {
                'status': 'no_data',
                'message': 'No accuracy history available'
            }
        
        # Calculate overall statistics
        all_accuracies = [h['overall_accuracy'] for h in self.accuracy_history if h['tracked_count'] > 0]
        
        if not all_accuracies:
            return {
                'status': 'insufficient_data',
                'message': 'No tracked forecasts with accuracy data'
            }
        
        metrics = {
            'status': 'active',
            'overall_accuracy': {
                'current': all_accuracies[-1] if all_accuracies else 0.0,
                'average': statistics.mean(all_accuracies),
                'min': min(all_accuracies),
                'max': max(all_accuracies),
                'std_dev': statistics.stdev(all_accuracies) if len(all_accuracies) > 1 else 0.0
            },
            'forecast_volume': {
                'total_forecasts': sum(h['forecast_count'] for h in self.accuracy_history),
                'tracked_forecasts': sum(h['tracked_count'] for h in self.accuracy_history),
                'tracking_rate': sum(h['tracked_count'] for h in self.accuracy_history) / sum(h['forecast_count'] for h in self.accuracy_history) if sum(h['forecast_count'] for h in self.accuracy_history) > 0 else 0.0
            },
            'retraining_recommended': self.check_retraining_trigger(),
            'last_updated': self.accuracy_history[-1]['timestamp'] if self.accuracy_history else None
        }
        
        return metrics
