# Fix S3 Bucket Permissions for Frontend
# This script makes the S3 bucket publicly readable

param(
    [string]$BucketName = "retailmind-frontend-060002399377"
)

Write-Host "Fixing S3 bucket permissions..." -ForegroundColor Cyan

# Step 1: Disable Block Public Access
Write-Host "`n[1/4] Disabling Block Public Access..." -ForegroundColor Yellow
aws s3api put-public-access-block `
    --bucket $BucketName `
    --public-access-block-configuration "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Block Public Access disabled" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to disable Block Public Access" -ForegroundColor Red
    exit 1
}

# Step 2: Create bucket policy
Write-Host "`n[2/4] Creating bucket policy..." -ForegroundColor Yellow
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

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Bucket policy applied" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to apply bucket policy" -ForegroundColor Red
    Remove-Item "temp-policy.json" -ErrorAction SilentlyContinue
    exit 1
}

Remove-Item "temp-policy.json" -ErrorAction SilentlyContinue

# Step 3: Enable static website hosting
Write-Host "`n[3/4] Enabling static website hosting..." -ForegroundColor Yellow
aws s3 website "s3://$BucketName" --index-document index.html --error-document index.html

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Static website hosting enabled" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to enable static website hosting" -ForegroundColor Red
}

# Step 4: Verify
Write-Host "`n[4/4] Verifying bucket policy..." -ForegroundColor Yellow
$currentPolicy = aws s3api get-bucket-policy --bucket $BucketName --query Policy --output text 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Bucket policy verified" -ForegroundColor Green
} else {
    Write-Host "⚠ Could not verify bucket policy" -ForegroundColor Yellow
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Permissions Fixed Successfully!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "`nWebsite URL: http://$BucketName.s3-website-us-east-1.amazonaws.com" -ForegroundColor Yellow
Write-Host "`nPlease wait 1-2 minutes for changes to propagate, then refresh your browser." -ForegroundColor White
