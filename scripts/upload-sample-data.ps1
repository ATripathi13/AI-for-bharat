# Upload Sample Data to RetailMind AI
# This script uploads sample retail data to S3 buckets

param(
    [string]$AccountId = "060002399377",
    [string]$Region = "us-east-1"
)

Write-Host "Uploading sample data to RetailMind AI..." -ForegroundColor Cyan

# Define bucket names (from CDK deployment)
$rawDataBucket = "retailmind-raw-data-$AccountId"
$mlArtifactsBucket = "retailmind-ml-artifacts-$AccountId"
$documentsBucket = "retailmind-documents-$AccountId"

# Step 1: Create sample data directory
Write-Host "`n[1/5] Creating sample data..." -ForegroundColor Yellow
$sampleDir = "sample-data"
New-Item -ItemType Directory -Force -Path $sampleDir | Out-Null

# Create sample transaction data (CSV)
$transactionData = @"
transaction_id,date,product_id,product_name,category,quantity,unit_price,total_amount,store_id,customer_id
TXN001,2024-03-01,P001,Laptop,Electronics,2,899.99,1799.98,S001,C001
TXN002,2024-03-01,P002,Mouse,Electronics,5,29.99,149.95,S001,C002
TXN003,2024-03-02,P003,Keyboard,Electronics,3,79.99,239.97,S002,C003
TXN004,2024-03-02,P004,Monitor,Electronics,1,299.99,299.99,S001,C001
TXN005,2024-03-03,P005,Desk Chair,Furniture,2,199.99,399.98,S003,C004
TXN006,2024-03-03,P001,Laptop,Electronics,1,899.99,899.99,S002,C005
TXN007,2024-03-04,P006,Notebook,Stationery,10,4.99,49.90,S001,C002
TXN008,2024-03-04,P007,Pen Set,Stationery,15,9.99,149.85,S003,C006
TXN009,2024-03-05,P008,Backpack,Accessories,4,49.99,199.96,S002,C007
TXN010,2024-03-05,P009,Water Bottle,Accessories,8,19.99,159.92,S001,C003
"@
$transactionData | Out-File -FilePath "$sampleDir/transactions.csv" -Encoding utf8

# Create sample inventory data (CSV)
$inventoryData = @"
product_id,product_name,category,current_stock,reorder_level,unit_cost,unit_price,supplier_id,last_restock_date
P001,Laptop,Electronics,45,20,699.99,899.99,SUP001,2024-02-15
P002,Mouse,Electronics,150,50,19.99,29.99,SUP001,2024-02-20
P003,Keyboard,Electronics,80,30,49.99,79.99,SUP001,2024-02-18
P004,Monitor,Electronics,35,15,199.99,299.99,SUP002,2024-02-25
P005,Desk Chair,Furniture,25,10,129.99,199.99,SUP003,2024-02-10
P006,Notebook,Stationery,500,200,2.99,4.99,SUP004,2024-03-01
P007,Pen Set,Stationery,300,100,5.99,9.99,SUP004,2024-03-01
P008,Backpack,Accessories,60,25,29.99,49.99,SUP005,2024-02-28
P009,Water Bottle,Accessories,120,50,12.99,19.99,SUP005,2024-02-28
P010,USB Cable,Electronics,200,75,4.99,9.99,SUP001,2024-03-02
"@
$inventoryData | Out-File -FilePath "$sampleDir/inventory.csv" -Encoding utf8

# Create sample customer data (JSON)
$customerData = @"
[
  {
    "customer_id": "C001",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "segment": "Premium",
    "total_purchases": 15,
    "lifetime_value": 4500.00
  },
  {
    "customer_id": "C002",
    "name": "Jane Smith",
    "email": "jane.smith@example.com",
    "segment": "Regular",
    "total_purchases": 8,
    "lifetime_value": 1200.00
  },
  {
    "customer_id": "C003",
    "name": "Bob Johnson",
    "email": "bob.johnson@example.com",
    "segment": "Premium",
    "total_purchases": 12,
    "lifetime_value": 3800.00
  }
]
"@
$customerData | Out-File -FilePath "$sampleDir/customers.json" -Encoding utf8

Write-Host "✓ Sample data created" -ForegroundColor Green

# Step 2: Upload to raw data bucket
Write-Host "`n[2/5] Uploading to raw data bucket..." -ForegroundColor Yellow
aws s3 cp "$sampleDir/transactions.csv" "s3://$rawDataBucket/transactions/2024/03/transactions.csv"
aws s3 cp "$sampleDir/inventory.csv" "s3://$rawDataBucket/inventory/current/inventory.csv"
aws s3 cp "$sampleDir/customers.json" "s3://$rawDataBucket/customers/customers.json"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Data uploaded to raw data bucket" -ForegroundColor Green
} else {
    Write-Host "⚠ Some files may not have uploaded. Check bucket exists: $rawDataBucket" -ForegroundColor Yellow
}

# Step 3: Create sample ML model metadata
Write-Host "`n[3/5] Creating ML artifacts..." -ForegroundColor Yellow
$modelMetadata = @"
{
  "model_name": "demand_forecast_v1",
  "model_type": "time_series",
  "created_date": "2024-03-01",
  "accuracy": 0.87,
  "parameters": {
    "algorithm": "ARIMA",
    "seasonality": "weekly",
    "forecast_horizon": 30
  }
}
"@
$modelMetadata | Out-File -FilePath "$sampleDir/model_metadata.json" -Encoding utf8
aws s3 cp "$sampleDir/model_metadata.json" "s3://$mlArtifactsBucket/models/demand_forecast/metadata.json"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ ML artifacts uploaded" -ForegroundColor Green
} else {
    Write-Host "⚠ ML artifacts may not have uploaded. Check bucket exists: $mlArtifactsBucket" -ForegroundColor Yellow
}

# Step 4: Create sample documents
Write-Host "`n[4/5] Creating sample documents..." -ForegroundColor Yellow
$reportContent = @"
# Retail Performance Report - March 2024

## Executive Summary
- Total Revenue: $4,349.49
- Total Transactions: 10
- Average Order Value: $434.95
- Top Category: Electronics (60% of revenue)

## Key Insights
1. Electronics category shows strong performance
2. Laptop sales driving revenue growth
3. Stationery items have high volume but lower margins
4. Inventory levels healthy across all categories

## Recommendations
1. Increase marketing for high-margin electronics
2. Consider bundle deals for accessories
3. Monitor laptop inventory closely due to high demand
"@
$reportContent | Out-File -FilePath "$sampleDir/performance_report.txt" -Encoding utf8
aws s3 cp "$sampleDir/performance_report.txt" "s3://$documentsBucket/reports/2024/03/performance_report.txt"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Documents uploaded" -ForegroundColor Green
} else {
    Write-Host "⚠ Documents may not have uploaded. Check bucket exists: $documentsBucket" -ForegroundColor Yellow
}

# Step 5: Verify uploads
Write-Host "`n[5/5] Verifying uploads..." -ForegroundColor Yellow
Write-Host "`nRaw Data Bucket Contents:" -ForegroundColor Gray
aws s3 ls "s3://$rawDataBucket/" --recursive

Write-Host "`nML Artifacts Bucket Contents:" -ForegroundColor Gray
aws s3 ls "s3://$mlArtifactsBucket/" --recursive

Write-Host "`nDocuments Bucket Contents:" -ForegroundColor Gray
aws s3 ls "s3://$documentsBucket/" --recursive

# Cleanup
Remove-Item -Recurse -Force $sampleDir

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Sample Data Uploaded Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "`nUploaded Files:" -ForegroundColor White
Write-Host "  ✓ transactions.csv (10 sample transactions)" -ForegroundColor Green
Write-Host "  ✓ inventory.csv (10 products)" -ForegroundColor Green
Write-Host "  ✓ customers.json (3 customers)" -ForegroundColor Green
Write-Host "  ✓ model_metadata.json (ML model info)" -ForegroundColor Green
Write-Host "  ✓ performance_report.txt (sample report)" -ForegroundColor Green
Write-Host "`nBuckets:" -ForegroundColor White
Write-Host "  • Raw Data: $rawDataBucket" -ForegroundColor Gray
Write-Host "  • ML Artifacts: $mlArtifactsBucket" -ForegroundColor Gray
Write-Host "  • Documents: $documentsBucket" -ForegroundColor Gray
Write-Host "`nYou can now use this data in your RetailMind AI application!" -ForegroundColor Yellow
Write-Host "`nTo upload your own data:" -ForegroundColor White
Write-Host "  aws s3 cp your-file.csv s3://$rawDataBucket/your-folder/" -ForegroundColor Gray
