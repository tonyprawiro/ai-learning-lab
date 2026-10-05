Write-Host ""
Write-Host "=== FAILURE INJECTION ==="
Write-Host "Injecting a deliberate application misconfiguration..."
Write-Host ""

aws lambda update-function-configuration `
  --function-name task-app `
  --environment "Variables={TABLE_NAME=appdata-wrong}" `
  --region ap-southeast-1 `
  | Out-Null

Write-Host "FAULT INJECTED"
Write-Host "  Lambda function: task-app"
Write-Host "  TABLE_NAME:      appdata-wrong"
Write-Host ""
Write-Host "The application is now expected to fail."
Write-Host ""