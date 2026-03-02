"""
Workflow Template Library for RetailMind AI
Provides pre-built workflow templates for common business scenarios
"""
from typing import Dict, List, Optional
from .wdl_parser import (
    WorkflowDefinition,
    WDLStep,
    WDLStepType,
    WDLCondition,
    WDLConditionOperator,
    WDLRollbackStep
)


class WorkflowTemplateLibrary:
    """
    Library of pre-built workflow templates
    Provides templates for common retail business scenarios
    """
    
    def __init__(self):
        """Initialize template library"""
        self._templates: Dict[str, WorkflowDefinition] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default workflow templates"""
        self._templates['pricing_optimization'] = self._create_pricing_optimization_template()
        self._templates['inventory_rebalancing'] = self._create_inventory_rebalancing_template()
        self._templates['demand_forecast_update'] = self._create_demand_forecast_template()
        self._templates['risk_assessment'] = self._create_risk_assessment_template()
        self._templates['market_intelligence_sync'] = self._create_market_intelligence_template()
    
    def get_template(self, template_name: str) -> Optional[WorkflowDefinition]:
        """
        Get a workflow template by name
        
        Args:
            template_name: Name of the template
            
        Returns:
            WorkflowDefinition or None if not found
        """
        return self._templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """
        List all available template names
        
        Returns:
            List of template names
        """
        return list(self._templates.keys())
    
    def add_template(self, name: str, template: WorkflowDefinition):
        """
        Add a custom template to the library
        
        Args:
            name: Template name
            template: WorkflowDefinition
        """
        self._templates[name] = template
    
    def _create_pricing_optimization_template(self) -> WorkflowDefinition:
        """Create pricing optimization workflow template"""
        steps = [
            WDLStep(
                step_id='fetch_market_data',
                name='Fetch Market Data',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'market_intelligence_agent.get_pricing_trends',
                    'input': '$.productId'
                },
                next_step='analyze_competition'
            ),
            WDLStep(
                step_id='analyze_competition',
                name='Analyze Competition',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'pricing_optimization_agent.analyze_competitors',
                    'input': '$.marketData'
                },
                next_step='calculate_optimal_price'
            ),
            WDLStep(
                step_id='calculate_optimal_price',
                name='Calculate Optimal Price',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'pricing_optimization_agent.optimize_price',
                    'input': '$.competitorAnalysis'
                },
                next_step='check_confidence'
            ),
            WDLStep(
                step_id='check_confidence',
                name='Check Confidence Level',
                type=WDLStepType.CHOICE,
                configuration={
                    'choices': [
                        {
                            'condition': {'variable': '$.confidence', 'operator': 'greater_equal', 'value': 0.8},
                            'next': 'apply_pricing'
                        },
                        {
                            'condition': {'variable': '$.confidence', 'operator': 'less_than', 'value': 0.8},
                            'next': 'escalate_to_human'
                        }
                    ]
                },
                conditions=[
                    WDLCondition(
                        variable='$.confidence',
                        operator=WDLConditionOperator.GREATER_EQUAL,
                        value=0.8
                    )
                ]
            ),
            WDLStep(
                step_id='apply_pricing',
                name='Apply Pricing Changes',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'pricing_service.update_prices',
                    'input': '$.pricingRecommendation'
                },
                next_step='log_outcome'
            ),
            WDLStep(
                step_id='escalate_to_human',
                name='Escalate to Human',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'escalation_service.create_escalation',
                    'input': '$.pricingRecommendation'
                },
                next_step='log_outcome'
            ),
            WDLStep(
                step_id='log_outcome',
                name='Log Outcome',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'audit_service.log_decision',
                    'input': '$'
                }
            )
        ]
        
        rollback = [
            WDLRollbackStep(
                step_id='apply_pricing',
                action='revert_pricing',
                configuration={'function': 'pricing_service.revert_prices'}
            )
        ]
        
        return WorkflowDefinition(
            workflow_id='pricing_optimization_v1',
            name='Pricing Optimization Workflow',
            version='1.0.0',
            description='Optimizes product pricing based on market intelligence and competition',
            steps=steps,
            start_step='fetch_market_data',
            rollback_procedure=rollback,
            metadata={'category': 'pricing', 'priority': 'high'}
        )
    
    def _create_inventory_rebalancing_template(self) -> WorkflowDefinition:
        """Create inventory rebalancing workflow template"""
        steps = [
            WDLStep(
                step_id='fetch_inventory_levels',
                name='Fetch Inventory Levels',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'inventory_service.get_current_levels',
                    'input': '$.warehouseId'
                },
                next_step='get_demand_forecast'
            ),
            WDLStep(
                step_id='get_demand_forecast',
                name='Get Demand Forecast',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'demand_forecast_agent.get_forecast',
                    'input': '$.inventoryData'
                },
                next_step='calculate_rebalancing'
            ),
            WDLStep(
                step_id='calculate_rebalancing',
                name='Calculate Rebalancing Plan',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'inventory_planning_agent.optimize_stock',
                    'input': '$.forecastData'
                },
                next_step='execute_rebalancing'
            ),
            WDLStep(
                step_id='execute_rebalancing',
                name='Execute Rebalancing',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'inventory_service.rebalance_stock',
                    'input': '$.rebalancingPlan'
                },
                next_step='verify_execution'
            ),
            WDLStep(
                step_id='verify_execution',
                name='Verify Execution',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'inventory_service.verify_rebalancing',
                    'input': '$.executionResult'
                }
            )
        ]
        
        rollback = [
            WDLRollbackStep(
                step_id='execute_rebalancing',
                action='revert_rebalancing',
                configuration={'function': 'inventory_service.revert_rebalancing'}
            )
        ]
        
        return WorkflowDefinition(
            workflow_id='inventory_rebalancing_v1',
            name='Inventory Rebalancing Workflow',
            version='1.0.0',
            description='Rebalances inventory across warehouses based on demand forecasts',
            steps=steps,
            start_step='fetch_inventory_levels',
            rollback_procedure=rollback,
            metadata={'category': 'inventory', 'priority': 'medium'}
        )
    
    def _create_demand_forecast_template(self) -> WorkflowDefinition:
        """Create demand forecast update workflow template"""
        steps = [
            WDLStep(
                step_id='collect_sales_data',
                name='Collect Sales Data',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'data_service.get_sales_history',
                    'input': '$.timeRange'
                },
                next_step='prepare_features'
            ),
            WDLStep(
                step_id='prepare_features',
                name='Prepare ML Features',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'demand_forecast_agent.prepare_features',
                    'input': '$.salesData'
                },
                next_step='generate_forecast'
            ),
            WDLStep(
                step_id='generate_forecast',
                name='Generate Forecast',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'demand_forecast_agent.predict',
                    'input': '$.features'
                },
                next_step='validate_forecast'
            ),
            WDLStep(
                step_id='validate_forecast',
                name='Validate Forecast',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'demand_forecast_agent.validate_accuracy',
                    'input': '$.forecast'
                },
                next_step='store_forecast'
            ),
            WDLStep(
                step_id='store_forecast',
                name='Store Forecast',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'data_service.store_forecast',
                    'input': '$.validatedForecast'
                }
            )
        ]
        
        return WorkflowDefinition(
            workflow_id='demand_forecast_update_v1',
            name='Demand Forecast Update Workflow',
            version='1.0.0',
            description='Updates demand forecasts based on latest sales data',
            steps=steps,
            start_step='collect_sales_data',
            rollback_procedure=[],
            metadata={'category': 'forecasting', 'priority': 'high'}
        )
    
    def _create_risk_assessment_template(self) -> WorkflowDefinition:
        """Create risk assessment workflow template"""
        steps = [
            WDLStep(
                step_id='extract_documents',
                name='Extract Document Data',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'risk_compliance_agent.extract_document',
                    'input': '$.documentUrl'
                },
                next_step='validate_compliance'
            ),
            WDLStep(
                step_id='validate_compliance',
                name='Validate Compliance',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'risk_compliance_agent.validate_compliance',
                    'input': '$.extractedData'
                },
                next_step='check_fraud_patterns'
            ),
            WDLStep(
                step_id='check_fraud_patterns',
                name='Check Fraud Patterns',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'risk_compliance_agent.detect_fraud',
                    'input': '$.complianceData'
                },
                next_step='calculate_risk_score'
            ),
            WDLStep(
                step_id='calculate_risk_score',
                name='Calculate Risk Score',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'risk_compliance_agent.calculate_risk',
                    'input': '$.fraudAnalysis'
                },
                next_step='check_risk_level'
            ),
            WDLStep(
                step_id='check_risk_level',
                name='Check Risk Level',
                type=WDLStepType.CHOICE,
                configuration={
                    'choices': [
                        {
                            'condition': {'variable': '$.riskScore', 'operator': 'greater_than', 'value': 0.7},
                            'next': 'generate_alert'
                        },
                        {
                            'condition': {'variable': '$.riskScore', 'operator': 'less_equal', 'value': 0.7},
                            'next': 'log_assessment'
                        }
                    ]
                },
                conditions=[
                    WDLCondition(
                        variable='$.riskScore',
                        operator=WDLConditionOperator.GREATER_THAN,
                        value=0.7
                    )
                ]
            ),
            WDLStep(
                step_id='generate_alert',
                name='Generate Risk Alert',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'compliance_alert_service.create_alert',
                    'input': '$.riskAssessment'
                },
                next_step='log_assessment'
            ),
            WDLStep(
                step_id='log_assessment',
                name='Log Assessment',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'audit_service.log_risk_assessment',
                    'input': '$'
                }
            )
        ]
        
        return WorkflowDefinition(
            workflow_id='risk_assessment_v1',
            name='Risk Assessment Workflow',
            version='1.0.0',
            description='Assesses risk and compliance for documents and transactions',
            steps=steps,
            start_step='extract_documents',
            rollback_procedure=[],
            metadata={'category': 'compliance', 'priority': 'critical'}
        )
    
    def _create_market_intelligence_template(self) -> WorkflowDefinition:
        """Create market intelligence sync workflow template"""
        steps = [
            WDLStep(
                step_id='fetch_competitor_data',
                name='Fetch Competitor Data',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'market_intelligence_agent.fetch_competitor_prices',
                    'input': '$.productCategories'
                },
                next_step='analyze_trends'
            ),
            WDLStep(
                step_id='analyze_trends',
                name='Analyze Market Trends',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'market_intelligence_agent.analyze_trends',
                    'input': '$.competitorData'
                },
                next_step='generate_heatmap'
            ),
            WDLStep(
                step_id='generate_heatmap',
                name='Generate Demand Heatmap',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'market_intelligence_agent.generate_heatmap',
                    'input': '$.trendAnalysis'
                },
                next_step='detect_seasonal_patterns'
            ),
            WDLStep(
                step_id='detect_seasonal_patterns',
                name='Detect Seasonal Patterns',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'market_intelligence_agent.detect_seasonal_trends',
                    'input': '$.heatmapData'
                },
                next_step='store_intelligence'
            ),
            WDLStep(
                step_id='store_intelligence',
                name='Store Market Intelligence',
                type=WDLStepType.LAMBDA,
                configuration={
                    'function': 'data_service.store_market_intelligence',
                    'input': '$.seasonalAnalysis'
                }
            )
        ]
        
        return WorkflowDefinition(
            workflow_id='market_intelligence_sync_v1',
            name='Market Intelligence Sync Workflow',
            version='1.0.0',
            description='Syncs and analyzes market intelligence data',
            steps=steps,
            start_step='fetch_competitor_data',
            rollback_procedure=[],
            metadata={'category': 'market_intelligence', 'priority': 'medium'}
        )
