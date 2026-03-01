-- Redshift Analytics Warehouse Schema for RetailMind AI
-- This schema supports analytics, reporting, and business intelligence queries

-- Create schema for organizing tables
CREATE SCHEMA IF NOT EXISTS retailmind_analytics;

-- Set search path
SET search_path TO retailmind_analytics;

-- ============================================================================
-- DIMENSION TABLES
-- ============================================================================

-- Dimension: Products
CREATE TABLE IF NOT EXISTS dim_products (
    product_key BIGINT IDENTITY(1,1) PRIMARY KEY,
    product_id VARCHAR(100) NOT NULL,
    sku VARCHAR(100) NOT NULL,
    product_name VARCHAR(500),
    category VARCHAR(200),
    subcategory VARCHAR(200),
    brand VARCHAR(200),
    unit_of_measure VARCHAR(50),
    effective_date DATE NOT NULL,
    expiration_date DATE,
    is_current BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT GETDATE(),
    updated_at TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (product_id, effective_date);

-- Dimension: Regions
CREATE TABLE IF NOT EXISTS dim_regions (
    region_key BIGINT IDENTITY(1,1) PRIMARY KEY,
    region_id VARCHAR(100) NOT NULL,
    region_name VARCHAR(200),
    state VARCHAR(100),
    city VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    region_type VARCHAR(50), -- urban, rural, metro
    population_density VARCHAR(50),
    created_at TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE ALL
SORTKEY (region_id);

-- Dimension: Time
CREATE TABLE IF NOT EXISTS dim_time (
    time_key BIGINT IDENTITY(1,1) PRIMARY KEY,
    date DATE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    week INTEGER,
    day INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    month_name VARCHAR(20),
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    holiday_name VARCHAR(200),
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    created_at TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE ALL
SORTKEY (date);

-- Dimension: Agents
CREATE TABLE IF NOT EXISTS dim_agents (
    agent_key BIGINT IDENTITY(1,1) PRIMARY KEY,
    agent_id VARCHAR(100) NOT NULL,
    agent_name VARCHAR(200),
    agent_type VARCHAR(100), -- market_intelligence, demand_forecast, pricing, inventory, risk_compliance, business_copilot, workflow_regeneration
    version VARCHAR(50),
    capabilities TEXT,
    created_at TIMESTAMP DEFAULT GETDATE(),
    updated_at TIMESTAMP DEFAULT GETDATE()
)
DISTSTYLE ALL
SORTKEY (agent_id);

-- ============================================================================
-- FACT TABLES
-- ============================================================================

-- Fact: Sales Transactions
CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    region_key BIGINT NOT NULL,
    quantity DECIMAL(18,4),
    unit_price DECIMAL(18,4),
    discount_amount DECIMAL(18,4),
    tax_amount DECIMAL(18,4),
    total_amount DECIMAL(18,4),
    cost_of_goods DECIMAL(18,4),
    gross_margin DECIMAL(18,4),
    transaction_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (transaction_id, time_key)
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (time_key, product_key);

-- Fact: Inventory Snapshots
CREATE TABLE IF NOT EXISTS fact_inventory (
    snapshot_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    region_key BIGINT NOT NULL,
    quantity_on_hand DECIMAL(18,4),
    quantity_reserved DECIMAL(18,4),
    quantity_available DECIMAL(18,4),
    reorder_point DECIMAL(18,4),
    reorder_quantity DECIMAL(18,4),
    stock_value DECIMAL(18,4),
    days_of_supply INTEGER,
    stockout_flag BOOLEAN,
    overstock_flag BOOLEAN,
    snapshot_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (snapshot_id, time_key, product_key)
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (time_key, product_key);

-- Fact: Pricing History
CREATE TABLE IF NOT EXISTS fact_pricing (
    pricing_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    region_key BIGINT NOT NULL,
    list_price DECIMAL(18,4),
    selling_price DECIMAL(18,4),
    competitor_avg_price DECIMAL(18,4),
    competitor_min_price DECIMAL(18,4),
    competitor_max_price DECIMAL(18,4),
    price_elasticity DECIMAL(10,6),
    margin_percentage DECIMAL(10,4),
    pricing_strategy VARCHAR(100),
    price_change_reason VARCHAR(500),
    effective_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (pricing_id, time_key)
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (time_key, product_key);

-- Fact: Demand Forecasts
CREATE TABLE IF NOT EXISTS fact_demand_forecast (
    forecast_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    region_key BIGINT NOT NULL,
    agent_key BIGINT NOT NULL,
    forecast_date DATE,
    forecast_quantity DECIMAL(18,4),
    forecast_confidence DECIMAL(5,4),
    actual_quantity DECIMAL(18,4),
    forecast_error DECIMAL(18,4),
    forecast_accuracy DECIMAL(5,4),
    model_version VARCHAR(50),
    forecast_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (forecast_id, time_key)
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (time_key, product_key);

-- Fact: Agent Decisions
CREATE TABLE IF NOT EXISTS fact_agent_decisions (
    decision_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    agent_key BIGINT NOT NULL,
    decision_type VARCHAR(100),
    decision_action VARCHAR(500),
    confidence_score DECIMAL(5,4),
    escalation_required BOOLEAN,
    escalation_reason VARCHAR(1000),
    execution_status VARCHAR(50),
    business_impact_score DECIMAL(18,4),
    decision_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (decision_id, time_key)
)
DISTSTYLE KEY
DISTKEY (agent_key)
SORTKEY (time_key, agent_key);

-- Fact: Workflow Executions
CREATE TABLE IF NOT EXISTS fact_workflow_executions (
    execution_id VARCHAR(100) NOT NULL,
    workflow_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    agent_key BIGINT,
    workflow_type VARCHAR(100),
    execution_status VARCHAR(50),
    execution_time_seconds DECIMAL(18,4),
    step_count INTEGER,
    success_rate DECIMAL(5,4),
    business_impact_score DECIMAL(18,4),
    error_count INTEGER,
    rollback_flag BOOLEAN,
    created_by VARCHAR(50),
    generated_by VARCHAR(100),
    execution_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (execution_id, time_key)
)
DISTSTYLE KEY
DISTKEY (workflow_id)
SORTKEY (time_key, workflow_id);

-- Fact: Risk and Compliance Events
CREATE TABLE IF NOT EXISTS fact_risk_compliance (
    event_id VARCHAR(100) NOT NULL,
    time_key BIGINT NOT NULL,
    agent_key BIGINT NOT NULL,
    event_type VARCHAR(100), -- fraud_detection, compliance_violation, document_validation
    risk_score DECIMAL(5,4),
    risk_category VARCHAR(100),
    severity VARCHAR(50),
    detection_method VARCHAR(200),
    remediation_action VARCHAR(1000),
    remediation_status VARCHAR(50),
    false_positive_flag BOOLEAN,
    event_timestamp TIMESTAMP,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (event_id, time_key)
)
DISTSTYLE KEY
DISTKEY (agent_key)
SORTKEY (time_key, risk_score);

-- ============================================================================
-- AGGREGATE TABLES (for performance optimization)
-- ============================================================================

-- Aggregate: Daily Product Performance
CREATE TABLE IF NOT EXISTS agg_daily_product_performance (
    date DATE NOT NULL,
    product_key BIGINT NOT NULL,
    region_key BIGINT NOT NULL,
    total_sales_quantity DECIMAL(18,4),
    total_sales_amount DECIMAL(18,4),
    total_transactions INTEGER,
    avg_unit_price DECIMAL(18,4),
    avg_discount_percentage DECIMAL(10,4),
    total_margin DECIMAL(18,4),
    avg_inventory_level DECIMAL(18,4),
    stockout_hours INTEGER,
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (date, product_key, region_key)
)
DISTSTYLE KEY
DISTKEY (product_key)
SORTKEY (date, product_key);

-- Aggregate: Monthly Agent Performance
CREATE TABLE IF NOT EXISTS agg_monthly_agent_performance (
    year_month VARCHAR(7) NOT NULL, -- YYYY-MM
    agent_key BIGINT NOT NULL,
    total_decisions INTEGER,
    avg_confidence_score DECIMAL(5,4),
    escalation_count INTEGER,
    escalation_rate DECIMAL(5,4),
    successful_decisions INTEGER,
    success_rate DECIMAL(5,4),
    avg_business_impact DECIMAL(18,4),
    total_execution_time_seconds DECIMAL(18,4),
    created_at TIMESTAMP DEFAULT GETDATE(),
    PRIMARY KEY (year_month, agent_key)
)
DISTSTYLE ALL
SORTKEY (year_month, agent_key);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Current Product Inventory Status
CREATE OR REPLACE VIEW v_current_inventory_status AS
SELECT 
    p.product_id,
    p.sku,
    p.product_name,
    r.region_name,
    i.quantity_available,
    i.days_of_supply,
    i.stockout_flag,
    i.overstock_flag,
    i.snapshot_timestamp
FROM fact_inventory i
JOIN dim_products p ON i.product_key = p.product_key
JOIN dim_regions r ON i.region_key = r.region_key
WHERE i.snapshot_timestamp >= DATEADD(hour, -24, GETDATE());

-- View: Agent Decision Performance
CREATE OR REPLACE VIEW v_agent_decision_performance AS
SELECT 
    a.agent_name,
    a.agent_type,
    COUNT(d.decision_id) as total_decisions,
    AVG(d.confidence_score) as avg_confidence,
    SUM(CASE WHEN d.escalation_required THEN 1 ELSE 0 END) as escalation_count,
    AVG(d.business_impact_score) as avg_business_impact,
    t.date
FROM fact_agent_decisions d
JOIN dim_agents a ON d.agent_key = a.agent_key
JOIN dim_time t ON d.time_key = t.time_key
GROUP BY a.agent_name, a.agent_type, t.date;

-- View: Sales Performance with Forecasts
CREATE OR REPLACE VIEW v_sales_vs_forecast AS
SELECT 
    t.date,
    p.product_name,
    r.region_name,
    SUM(s.quantity) as actual_sales,
    AVG(f.forecast_quantity) as forecasted_sales,
    AVG(f.forecast_accuracy) as forecast_accuracy
FROM fact_sales s
JOIN fact_demand_forecast f ON s.product_key = f.product_key 
    AND s.region_key = f.region_key 
    AND s.time_key = f.time_key
JOIN dim_products p ON s.product_key = p.product_key
JOIN dim_regions r ON s.region_key = r.region_key
JOIN dim_time t ON s.time_key = t.time_key
GROUP BY t.date, p.product_name, r.region_name;

-- ============================================================================
-- INDEXES AND CONSTRAINTS
-- ============================================================================

-- Add foreign key constraints (informational only in Redshift)
-- These are not enforced but help query optimizer

ALTER TABLE fact_sales ADD CONSTRAINT fk_sales_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_sales ADD CONSTRAINT fk_sales_product FOREIGN KEY (product_key) REFERENCES dim_products(product_key);
ALTER TABLE fact_sales ADD CONSTRAINT fk_sales_region FOREIGN KEY (region_key) REFERENCES dim_regions(region_key);

ALTER TABLE fact_inventory ADD CONSTRAINT fk_inventory_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_inventory ADD CONSTRAINT fk_inventory_product FOREIGN KEY (product_key) REFERENCES dim_products(product_key);
ALTER TABLE fact_inventory ADD CONSTRAINT fk_inventory_region FOREIGN KEY (region_key) REFERENCES dim_regions(region_key);

ALTER TABLE fact_pricing ADD CONSTRAINT fk_pricing_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_pricing ADD CONSTRAINT fk_pricing_product FOREIGN KEY (product_key) REFERENCES dim_products(product_key);
ALTER TABLE fact_pricing ADD CONSTRAINT fk_pricing_region FOREIGN KEY (region_key) REFERENCES dim_regions(region_key);

ALTER TABLE fact_demand_forecast ADD CONSTRAINT fk_forecast_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_demand_forecast ADD CONSTRAINT fk_forecast_product FOREIGN KEY (product_key) REFERENCES dim_products(product_key);
ALTER TABLE fact_demand_forecast ADD CONSTRAINT fk_forecast_region FOREIGN KEY (region_key) REFERENCES dim_regions(region_key);
ALTER TABLE fact_demand_forecast ADD CONSTRAINT fk_forecast_agent FOREIGN KEY (agent_key) REFERENCES dim_agents(agent_key);

ALTER TABLE fact_agent_decisions ADD CONSTRAINT fk_decisions_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_agent_decisions ADD CONSTRAINT fk_decisions_agent FOREIGN KEY (agent_key) REFERENCES dim_agents(agent_key);

ALTER TABLE fact_workflow_executions ADD CONSTRAINT fk_workflow_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_workflow_executions ADD CONSTRAINT fk_workflow_agent FOREIGN KEY (agent_key) REFERENCES dim_agents(agent_key);

ALTER TABLE fact_risk_compliance ADD CONSTRAINT fk_risk_time FOREIGN KEY (time_key) REFERENCES dim_time(time_key);
ALTER TABLE fact_risk_compliance ADD CONSTRAINT fk_risk_agent FOREIGN KEY (agent_key) REFERENCES dim_agents(agent_key);

-- Grant permissions (adjust as needed for your security model)
-- GRANT SELECT ON ALL TABLES IN SCHEMA retailmind_analytics TO analytics_users;
-- GRANT ALL ON ALL TABLES IN SCHEMA retailmind_analytics TO etl_users;
