# Verify RetailMind AI Deployment Status
# This script checks if all components are properly configured

param(
    [string]$AccountId = "060002399377",
    [string]$Region = "us-east-1"
)

Write-Host "Verifying RetailMind AI Deployment..." -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

$allGood = $true

# Check 1: Frontend .env configuration
Write-Host "[1/6] Checking frontend configuration..." -ForegroundColor Yellow

if (Test-Path "frontend/.env") {
    $envContent = Get-Content "frontend/.env" -Raw
    
    if ($envContent -match "VITE_USER_POOL_ID=<REPLACE") {
        Write-Host "  ✗ Cognito User Pool ID not configured" -ForegroundColor Red
        Write-Host "    Run: aws cloudformation describe-stacks --stack-name RetailMindApiStack" -ForegroundColor Gray
        $allGood = $false
    } else {
        Write-Host "  ✓ User Pool ID configured" -ForegroundColor Green
    }
    
    if ($envContent -match "VITE_USER_POOL_CLIENT_ID=<REPLACE") {
        Write-Host "  ✗ Cognito Client ID not configured" -ForegroundColor Red
        $allGood = $false
    } else {
        Write-Host "  ✓ Client ID configured" -ForegroundColor Green
    }
    
    if ($envContent -match "VITE_API_GATEWAY_URL=https://") {
        Write-Host "  ✓ API Gateway URL configured" -ForegroundColor Green
    } else {
        Write-Host "  ✗ API Gateway URL not configured" -ForegroundColor Red
        $allGood = $false
    }
} else {
    Write-Host "  ✗ frontend/.env file not found" -ForegroundColor Red
    $allGood = $false
}

# Check 2: S3 Buckets
Write-Host "`n[2/6] Checking S3 buckets..." -ForegroundColor Yellow

$rawDataBucket = "retailmind-raw-data-$AccountId"
$result = aws s3 ls "s3://$rawDataBucket" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Raw data bucket exists: $rawDataBucket" -ForegroundColor Green
    
    # Check if bucket has data
    $fileCount = (aws s3 ls "s3://$rawDataBucket" --recursive | Measure-Object).Count
    if ($fileCount -gt 0) {
        Write-Host "  ✓ Bucket contains $fileCount files" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Bucket is empty - run upload-sample-data.ps1" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Raw data bucket not found: $rawDataBucket" -ForegroundColor Red
    $allGood = $false
}

# Check 3: DynamoDB Tables
Write-Host "`n[3/6] Checking DynamoDB tables..." -ForegroundColor Yellow

$tables = @("retailmind-transactions", "retailmind-agent-states", "retailmind-workflow-instances")

foreach ($table in $tables) {
    $result = aws dynamodb describe-table --table-name $table --region $Region 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Table exists: $table" -ForegroundColor Green
        
        # Check item count
        $scanResult = aws dynamodb scan --table-name $table --select COUNT --region $Region --output json 2>&1 | ConvertFrom-Json
        if ($scanResult.Count) {
            $count = $scanResult.Count
            if ($count -gt 0) {
                Write-Host "    Contains $count items" -ForegroundColor Gray
            } else {
                Write-Host "    ⚠ Table is empty" -ForegroundColor Yellow
                if ($table -eq "retailmind-transactions") {
                    Write-Host "    Run: .\scripts\load-s3-to-dynamodb.ps1" -ForegroundColor Gray
                }
            }
        }
    } else {
        Write-Host "  ✗ Table not found: $table" -ForegroundColor Red
        $allGood = $false
    }
}

# Check 4: CloudFormation Stack
Write-Host "`n[4/6] Checking CloudFormation stack..." -ForegroundColor Yellow

$stackResult = aws cloudformation describe-stacks --stack-name RetailMindApiStack --region $Region 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Stack exists: RetailMindApiStack" -ForegroundColor Green
    
    $stackInfo = $stackResult | ConvertFrom-Json
    $stackStatus = $stackInfo.Stacks[0].StackStatus
    
    if ($stackStatus -eq "CREATE_COMPLETE" -or $stackStatus -eq "UPDATE_COMPLETE") {
        Write-Host "  ✓ Stack status: $stackStatus" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Stack status: $stackStatus" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ Stack not found: RetailMindApiStack" -ForegroundColor Red
    Write-Host "    Deploy the stack first: cd infrastructure/cdk && cdk deploy" -ForegroundColor Gray
    $allGood = $false
}

# Check 5: Cognito User Pool
Write-Host "`n[5/6] Checking Cognito User Pool..." -ForegroundColor Yellow

# Try to get User Pool ID from CloudFormation
$userPoolId = aws cloudformation describe-stacks `
    --stack-name RetailMindApiStack `
    --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" `
    --output text `
    --region $Region 2>&1

if ($LASTEXITCODE -eq 0 -and $userPoolId) {
    Write-Host "  ✓ User Pool exists: $userPoolId" -ForegroundColor Green
    
    # Check for users
    $users = aws cognito-idp list-users --user-pool-id $userPoolId --region $Region 2>&1 | ConvertFrom-Json
    if ($users.Users) {
        $userCount = $users.Users.Count
        Write-Host "  ✓ User Pool has $userCount user(s)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ No users in User Pool" -ForegroundColor Yellow
        Write-Host "    Create a test user: .\scripts\create-test-user.ps1" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✗ User Pool not found" -ForegroundColor Red
    $allGood = $false
}

# Check 6: API Gateway
Write-Host "`n[6/6] Checking API Gateway..." -ForegroundColor Yellow

$apiUrl = aws cloudformation describe-stacks `
    --stack-name RetailMindApiStack `
    --query "Stacks[0].Outputs[?OutputKey=='ApiGatewayUrl'].OutputValue" `
    --output text `
    --region $Region 2>&1

if ($LASTEXITCODE -eq 0 -and $apiUrl) {
    Write-Host "  ✓ API Gateway URL: $apiUrl" -ForegroundColor Green
    
    # Try to ping the API (may fail without auth, but checks if it's reachable)
    try {
        $response = Invoke-WebRequest -Uri "$apiUrl/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
        Write-Host "  ✓ API is reachable" -ForegroundColor Green
    } catch {
        Write-Host "  ⚠ API health check failed (may require authentication)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✗ API Gateway URL not found" -ForegroundColor Red
    $allGood = $false
}

# Summary
Write-Host "`n======================================" -ForegroundColor Cyan
if ($allGood) {
    Write-Host "✓ All checks passed!" -ForegroundColor Green
    Write-Host "`nYour deployment looks good. Next steps:" -ForegroundColor White
    Write-Host "1. Ensure DynamoDB has data: .\scripts\load-s3-to-dynamodb.ps1" -ForegroundColor Gray
    Write-Host "2. Create a test user: .\scripts\create-test-user.ps1" -ForegroundColor Gray
    Write-Host "3. Access your frontend and sign in" -ForegroundColor Gray
} else {
    Write-Host "⚠ Some issues found" -ForegroundColor Yellow
    Write-Host "`nPlease fix the issues above and run this script again." -ForegroundColor White
    Write-Host "`nCommon fixes:" -ForegroundColor White
    Write-Host "• Update frontend/.env with Cognito credentials" -ForegroundColor Gray
    Write-Host "• Deploy CDK stack: cd infrastructure/cdk && cdk deploy" -ForegroundColor Gray
    Write-Host "• Upload sample data: .\scripts\upload-sample-data.ps1" -ForegroundColor Gray
    Write-Host "• Load data to DynamoDB: .\scripts\load-s3-to-dynamodb.ps1" -ForegroundColor Gray
}
Write-Host "======================================`n" -ForegroundColor Cyan
