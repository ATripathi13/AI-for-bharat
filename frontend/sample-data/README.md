# Enhanced Sample Data for RetailMind AI

This directory contains comprehensive sample data files that demonstrate the full capabilities of the RetailMind AI platform.

## Files Overview

### 1. enhanced-customers.json
Contains detailed customer information including:
- Customer ID and basic information
- Segment classification (VIP, Premium, Regular)
- Purchase history and lifetime value
- Regional distribution across India
- Preferred product categories
- Join date and last purchase date

**Total Records:** 10 customers
**Segments:** VIP (1), Premium (5), Regular (4)
**Regions:** North, South, East, West

### 2. enhanced-inventory.csv
Comprehensive inventory data with:
- 30 SKUs across multiple categories
- Current stock levels and reorder points
- Pricing information (cost and retail)
- Supplier relationships
- Demand trends and stock status
- Last restock dates

**Categories:**
- Electronics (18 products)
- Furniture (6 products)
- Stationery (3 products)
- Accessories (3 products)

**Stock Status Distribution:**
- Optimal: 18 products
- Stockout Risk: 10 products
- Overstock: 2 products

### 3. enhanced-transactions.csv
Detailed transaction records showing:
- 40 transactions over 10 days
- Multiple payment methods (Credit Card, UPI, Debit Card, EMI, Cash)
- Regional distribution
- Product mix across categories
- Customer purchase patterns

**Transaction Value Range:** ₹3,000 - ₹195,000
**Total Transaction Value:** ₹1,234,000
**Average Transaction Value:** ₹30,850

## Data Insights

### High-Value Customers
- C008 (Kavita Desai): ₹245,000 lifetime value, VIP segment
- C004 (Sneha Reddy): ₹156,000 lifetime value, Premium segment
- C001 (Rajesh Kumar): ₹125,000 lifetime value, Premium segment

### Top-Selling Products
1. Premium Laptop (SKU001) - High demand, optimal stock
2. 4K Monitor (SKU004) - High demand, stockout risk
3. Noise Cancelling Headphones (SKU017) - Growing demand

### Critical Stock Alerts
Products requiring immediate attention:
- SKU006 (Standing Desk): Only 15 units, high demand
- SKU028 (Printer Wireless): Only 18 units
- SKU030 (Filing Cabinet): Only 12 units

### Regional Performance
- West: Highest customer concentration and transaction volume
- South: Strong premium segment presence
- North: Balanced mix of segments
- East: Growing market with regular customers

## Usage in Dashboard

This data powers all dashboard views:

1. **Market Intelligence**: Pricing trends, competitor analysis, regional demand
2. **Demand Forecast**: Historical patterns for prediction models
3. **Pricing Optimization**: Current pricing vs. market dynamics
4. **Inventory Planning**: Stock levels, reorder recommendations
5. **Risk & Compliance**: Transaction patterns, supplier relationships

## Data Quality

- All dates are current (March 2026)
- Realistic Indian pricing (in Rupees)
- Authentic Indian names and regions
- Consistent relationships between entities
- Balanced distribution across categories

## Future Enhancements

Potential additions:
- Seasonal sales data
- Supplier performance metrics
- Return/refund records
- Customer feedback scores
- Marketing campaign data
- Competitor pricing data
