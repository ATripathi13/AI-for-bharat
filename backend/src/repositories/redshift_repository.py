"""
Redshift repository for analytics queries
"""
import os
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager


class RedshiftRepository:
    """Repository for Redshift analytics warehouse queries"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize Redshift repository
        
        Args:
            host: Redshift cluster endpoint (defaults to env var REDSHIFT_HOST)
            port: Redshift port (defaults to env var REDSHIFT_PORT or 5439)
            database: Database name (defaults to env var REDSHIFT_DATABASE)
            user: Database user (defaults to env var REDSHIFT_USER)
            password: Database password (defaults to env var REDSHIFT_PASSWORD)
        """
        self.host = host or os.getenv('REDSHIFT_HOST')
        self.port = port or int(os.getenv('REDSHIFT_PORT', '5439'))
        self.database = database or os.getenv('REDSHIFT_DATABASE')
        self.user = user or os.getenv('REDSHIFT_USER')
        self.password = password or os.getenv('REDSHIFT_PASSWORD')
        
        if not all([self.host, self.database, self.user, self.password]):
            raise ValueError("Redshift connection parameters must be provided or set in environment variables")

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Yields:
            psycopg2 connection object
        """
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            yield conn
        finally:
            if conn:
                conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Optional query parameters for parameterized queries
            
        Returns:
            List of dictionaries representing query results
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return [dict(row) for row in results]

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query
        
        Args:
            query: SQL query string
            params: Optional query parameters for parameterized queries
            
        Returns:
            Number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                conn.commit()
                return cursor.rowcount

    def execute_batch(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute a batch of queries with different parameters
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Total number of rows affected
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                from psycopg2.extras import execute_batch
                execute_batch(cursor, query, params_list)
                conn.commit()
                return cursor.rowcount

    def get_sales_data(
        self,
        start_date: str,
        end_date: str,
        product_ids: Optional[List[str]] = None,
        region_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales data from fact_sales table
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            product_ids: Optional list of product IDs to filter
            region_ids: Optional list of region IDs to filter
            
        Returns:
            List of sales records
        """
        query = """
            SELECT 
                fs.transaction_id,
                dt.date,
                dp.product_id,
                dp.product_name,
                dr.region_name,
                fs.quantity,
                fs.unit_price,
                fs.total_amount,
                fs.gross_margin
            FROM retailmind_analytics.fact_sales fs
            JOIN retailmind_analytics.dim_time dt ON fs.time_key = dt.time_key
            JOIN retailmind_analytics.dim_products dp ON fs.product_key = dp.product_key
            JOIN retailmind_analytics.dim_regions dr ON fs.region_key = dr.region_key
            WHERE dt.date BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        
        if product_ids:
            query += " AND dp.product_id = ANY(%s)"
            params.append(product_ids)
        
        if region_ids:
            query += " AND dr.region_id = ANY(%s)"
            params.append(region_ids)
        
        query += " ORDER BY dt.date DESC"
        
        return self.execute_query(query, tuple(params))

    def get_inventory_status(
        self,
        product_ids: Optional[List[str]] = None,
        region_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get current inventory status
        
        Args:
            product_ids: Optional list of product IDs to filter
            region_ids: Optional list of region IDs to filter
            
        Returns:
            List of inventory records
        """
        query = """
            SELECT 
                dp.product_id,
                dp.product_name,
                dr.region_name,
                fi.quantity_on_hand,
                fi.quantity_available,
                fi.reorder_point,
                fi.days_of_supply
            FROM retailmind_analytics.fact_inventory fi
            JOIN retailmind_analytics.dim_products dp ON fi.product_key = dp.product_key
            JOIN retailmind_analytics.dim_regions dr ON fi.region_key = dr.region_key
            WHERE dp.is_current = true
        """
        
        params = []
        
        if product_ids:
            query += " AND dp.product_id = ANY(%s)"
            params.append(product_ids)
        
        if region_ids:
            query += " AND dr.region_id = ANY(%s)"
            params.append(region_ids)
        
        return self.execute_query(query, tuple(params) if params else None)

    def get_demand_forecast_accuracy(
        self,
        start_date: str,
        end_date: str,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get demand forecast accuracy metrics
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            agent_id: Optional agent ID to filter
            
        Returns:
            List of forecast accuracy records
        """
        query = """
            SELECT 
                dt.date,
                dp.product_name,
                dr.region_name,
                da.agent_name,
                fdf.forecast_quantity,
                fdf.actual_quantity,
                fdf.forecast_error,
                fdf.forecast_accuracy,
                fdf.forecast_confidence
            FROM retailmind_analytics.fact_demand_forecast fdf
            JOIN retailmind_analytics.dim_time dt ON fdf.time_key = dt.time_key
            JOIN retailmind_analytics.dim_products dp ON fdf.product_key = dp.product_key
            JOIN retailmind_analytics.dim_regions dr ON fdf.region_key = dr.region_key
            JOIN retailmind_analytics.dim_agents da ON fdf.agent_key = da.agent_key
            WHERE dt.date BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        
        if agent_id:
            query += " AND da.agent_id = %s"
            params.append(agent_id)
        
        query += " ORDER BY dt.date DESC"
        
        return self.execute_query(query, tuple(params))

    def get_agent_performance(
        self,
        start_date: str,
        end_date: str,
        agent_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get agent performance metrics
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            agent_ids: Optional list of agent IDs to filter
            
        Returns:
            List of agent performance records
        """
        query = """
            SELECT 
                da.agent_id,
                da.agent_name,
                da.agent_type,
                COUNT(*) as total_decisions,
                AVG(fad.confidence_score) as avg_confidence,
                AVG(fad.business_impact_score) as avg_business_impact
            FROM retailmind_analytics.fact_agent_decisions fad
            JOIN retailmind_analytics.dim_agents da ON fad.agent_key = da.agent_key
            JOIN retailmind_analytics.dim_time dt ON fad.time_key = dt.time_key
            WHERE dt.date BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        
        if agent_ids:
            query += " AND da.agent_id = ANY(%s)"
            params.append(agent_ids)
        
        query += " GROUP BY da.agent_id, da.agent_name, da.agent_type"
        
        return self.execute_query(query, tuple(params))

    def get_workflow_performance(
        self,
        start_date: str,
        end_date: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get workflow execution performance metrics
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            limit: Optional limit on number of results
            
        Returns:
            List of workflow performance records
        """
        query = """
            SELECT 
                dt.date,
                fwe.execution_id,
                da.agent_name as generated_by,
                fwe.execution_time_seconds,
                fwe.step_count,
                fwe.success_rate,
                fwe.business_impact_score,
                fwe.error_count
            FROM retailmind_analytics.fact_workflow_executions fwe
            JOIN retailmind_analytics.dim_time dt ON fwe.time_key = dt.time_key
            JOIN retailmind_analytics.dim_agents da ON fwe.agent_key = da.agent_key
            WHERE dt.date BETWEEN %s AND %s
            ORDER BY dt.date DESC
        """
        
        params = [start_date, end_date]
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        return self.execute_query(query, tuple(params))

    def get_pricing_trends(
        self,
        start_date: str,
        end_date: str,
        product_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pricing trends over time
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            product_ids: Optional list of product IDs to filter
            
        Returns:
            List of pricing trend records
        """
        query = """
            SELECT 
                dt.date,
                dp.product_id,
                dp.product_name,
                dr.region_name,
                fp.list_price,
                fp.selling_price,
                fp.competitor_avg_price,
                fp.margin_percentage,
                fp.price_elasticity
            FROM retailmind_analytics.fact_pricing fp
            JOIN retailmind_analytics.dim_time dt ON fp.time_key = dt.time_key
            JOIN retailmind_analytics.dim_products dp ON fp.product_key = dp.product_key
            JOIN retailmind_analytics.dim_regions dr ON fp.region_key = dr.region_key
            WHERE dt.date BETWEEN %s AND %s
        """
        
        params = [start_date, end_date]
        
        if product_ids:
            query += " AND dp.product_id = ANY(%s)"
            params.append(product_ids)
        
        query += " ORDER BY dt.date DESC"
        
        return self.execute_query(query, tuple(params))
