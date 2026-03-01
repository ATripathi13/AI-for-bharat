"""
Redshift schema definitions and utilities for RetailMind AI
"""
from typing import Dict, List


class RedshiftSchema:
    """Redshift analytics warehouse schema definitions"""

    SCHEMA_NAME = "retailmind_analytics"

    # Dimension Tables
    DIMENSION_TABLES = {
        "dim_products": {
            "description": "Product dimension with SCD Type 2",
            "primary_key": "product_key",
            "business_key": "product_id",
            "columns": [
                "product_key", "product_id", "sku", "product_name",
                "category", "subcategory", "brand", "unit_of_measure",
                "effective_date", "expiration_date", "is_current",
                "created_at", "updated_at"
            ]
        },
        "dim_regions": {
            "description": "Geographic regions dimension",
            "primary_key": "region_key",
            "business_key": "region_id",
            "columns": [
                "region_key", "region_id", "region_name", "state",
                "city", "country", "region_type", "population_density",
                "created_at"
            ]
        },
        "dim_time": {
            "description": "Time dimension for date-based analysis",
            "primary_key": "time_key",
            "business_key": "date",
            "columns": [
                "time_key", "date", "year", "quarter", "month", "week",
                "day", "day_of_week", "day_name", "month_name",
                "is_weekend", "is_holiday", "holiday_name",
                "fiscal_year", "fiscal_quarter", "created_at"
            ]
        },
        "dim_agents": {
            "description": "AI agents dimension",
            "primary_key": "agent_key",
            "business_key": "agent_id",
            "columns": [
                "agent_key", "agent_id", "agent_name", "agent_type",
                "version", "capabilities", "created_at", "updated_at"
            ]
        }
    }

    # Fact Tables
    FACT_TABLES = {
        "fact_sales": {
            "description": "Sales transactions fact table",
            "primary_key": ["transaction_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "product_key": "dim_products",
                "region_key": "dim_regions"
            },
            "measures": [
                "quantity", "unit_price", "discount_amount", "tax_amount",
                "total_amount", "cost_of_goods", "gross_margin"
            ]
        },
        "fact_inventory": {
            "description": "Inventory snapshots fact table",
            "primary_key": ["snapshot_id", "time_key", "product_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "product_key": "dim_products",
                "region_key": "dim_regions"
            },
            "measures": [
                "quantity_on_hand", "quantity_reserved", "quantity_available",
                "reorder_point", "reorder_quantity", "stock_value", "days_of_supply"
            ]
        },
        "fact_pricing": {
            "description": "Pricing history fact table",
            "primary_key": ["pricing_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "product_key": "dim_products",
                "region_key": "dim_regions"
            },
            "measures": [
                "list_price", "selling_price", "competitor_avg_price",
                "competitor_min_price", "competitor_max_price",
                "price_elasticity", "margin_percentage"
            ]
        },
        "fact_demand_forecast": {
            "description": "Demand forecasts fact table",
            "primary_key": ["forecast_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "product_key": "dim_products",
                "region_key": "dim_regions",
                "agent_key": "dim_agents"
            },
            "measures": [
                "forecast_quantity", "forecast_confidence", "actual_quantity",
                "forecast_error", "forecast_accuracy"
            ]
        },
        "fact_agent_decisions": {
            "description": "Agent decisions fact table",
            "primary_key": ["decision_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "agent_key": "dim_agents"
            },
            "measures": [
                "confidence_score", "business_impact_score"
            ]
        },
        "fact_workflow_executions": {
            "description": "Workflow executions fact table",
            "primary_key": ["execution_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "agent_key": "dim_agents"
            },
            "measures": [
                "execution_time_seconds", "step_count", "success_rate",
                "business_impact_score", "error_count"
            ]
        },
        "fact_risk_compliance": {
            "description": "Risk and compliance events fact table",
            "primary_key": ["event_id", "time_key"],
            "foreign_keys": {
                "time_key": "dim_time",
                "agent_key": "dim_agents"
            },
            "measures": [
                "risk_score"
            ]
        }
    }

    # Aggregate Tables
    AGGREGATE_TABLES = {
        "agg_daily_product_performance": {
            "description": "Daily product performance aggregates",
            "grain": "Daily per product per region",
            "measures": [
                "total_sales_quantity", "total_sales_amount", "total_transactions",
                "avg_unit_price", "avg_discount_percentage", "total_margin",
                "avg_inventory_level", "stockout_hours"
            ]
        },
        "agg_monthly_agent_performance": {
            "description": "Monthly agent performance aggregates",
            "grain": "Monthly per agent",
            "measures": [
                "total_decisions", "avg_confidence_score", "escalation_count",
                "escalation_rate", "successful_decisions", "success_rate",
                "avg_business_impact", "total_execution_time_seconds"
            ]
        }
    }

    # Views
    VIEWS = {
        "v_current_inventory_status": {
            "description": "Current inventory status across all products and regions",
            "base_tables": ["fact_inventory", "dim_products", "dim_regions"]
        },
        "v_agent_decision_performance": {
            "description": "Agent decision performance metrics",
            "base_tables": ["fact_agent_decisions", "dim_agents", "dim_time"]
        },
        "v_sales_vs_forecast": {
            "description": "Sales performance compared to forecasts",
            "base_tables": ["fact_sales", "fact_demand_forecast", "dim_products", "dim_regions", "dim_time"]
        }
    }

    @classmethod
    def get_table_ddl_path(cls) -> str:
        """Get path to the SQL DDL file"""
        return "infrastructure/cdk/schemas/redshift_schema.sql"

    @classmethod
    def get_all_tables(cls) -> List[str]:
        """Get list of all table names"""
        return (
            list(cls.DIMENSION_TABLES.keys()) +
            list(cls.FACT_TABLES.keys()) +
            list(cls.AGGREGATE_TABLES.keys())
        )

    @classmethod
    def get_table_info(cls, table_name: str) -> Dict:
        """Get information about a specific table"""
        if table_name in cls.DIMENSION_TABLES:
            return cls.DIMENSION_TABLES[table_name]
        elif table_name in cls.FACT_TABLES:
            return cls.FACT_TABLES[table_name]
        elif table_name in cls.AGGREGATE_TABLES:
            return cls.AGGREGATE_TABLES[table_name]
        else:
            raise ValueError(f"Table {table_name} not found in schema")

    @classmethod
    def get_view_info(cls, view_name: str) -> Dict:
        """Get information about a specific view"""
        if view_name in cls.VIEWS:
            return cls.VIEWS[view_name]
        else:
            raise ValueError(f"View {view_name} not found in schema")
