# Test CDK Configuration Script
# This script activates the virtual environment and tests CDK

Write-Host "Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

Write-Host "`nChecking CDK version..." -ForegroundColor Cyan
cdk --version

Write-Host "`nSynthesizing CDK stacks..." -ForegroundColor Cyan
cdk synth

Write-Host "`nCDK configuration test complete!" -ForegroundColor Green
