# Deploy Frontend to S3
# This script creates an S3 bucket, builds the frontend, and deploys it

param(
    [string]$BucketName = "retailmind-frontend-060002399377",
    [string]$Region = "us-east-1"
)

Write-Host "Deploying RetailMind AI Frontend..." -ForegroundColor Cyan

# Step 1: Create S3 bucket if it doesn't exist
Write-Host "`n[1/5] Creating S3 bucket..." -ForegroundColor Yellow
$bucketExists = aws s3 ls "s3://$BucketName" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating bucket: $BucketName" -ForegroundColor Gray
    aws s3 mb "s3://$BucketName" --region $Region
    
    # Enable static website hosting
    aws s3 website "s3://$BucketName" --index-document index.html --error-document index.html
    
    # Set bucket policy for public read
    $policy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::$BucketName/*"
        }
    ]
}
"@
    $policy | Out-File -FilePath "temp-policy.json" -Encoding utf8
    aws s3api put-bucket-policy --bucket $BucketName --policy file://temp-policy.json
    Remove-Item "temp-policy.json"
    
    Write-Host "✓ Bucket created and configured" -ForegroundColor Green
} else {
    Write-Host "✓ Bucket already exists" -ForegroundColor Green
}

# Step 2: Build frontend
Write-Host "`n[2/5] Building frontend..." -ForegroundColor Yellow
Push-Location frontend
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Build failed" -ForegroundColor Red
    Pop-Location
    exit 1
}
Pop-Location
Write-Host "✓ Build completed" -ForegroundColor Green

# Step 3: Deploy to S3
Write-Host "`n[3/5] Uploading to S3..." -ForegroundColor Yellow
aws s3 sync frontend/dist "s3://$BucketName" --delete
Write-Host "✓ Upload completed" -ForegroundColor Green

# Step 4: Get website URL
Write-Host "`n[4/5] Getting website URL..." -ForegroundColor Yellow
$websiteUrl = "http://$BucketName.s3-website-$Region.amazonaws.com"
Write-Host "✓ Website URL: $websiteUrl" -ForegroundColor Green

# Step 5: Summary
Write-Host "`n[5/5] Deployment Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Frontend URL: $websiteUrl" -ForegroundColor White
Write-Host "S3 Bucket: $BucketName" -ForegroundColor White
Write-Host "Region: $Region" -ForegroundColor White
Write-Host "`nAPI Endpoint: https://qly2lg0y8g.execute-api.us-east-1.amazonaws.com/dev/" -ForegroundColor White
Write-Host "`n✓ Deployment completed successfully!" -ForegroundColor Green
Write-Host "`nOpen your browser to: $websiteUrl" -ForegroundColor Yellow
