Write-Host ""
Write-Host "=== AI TROUBLESHOOTER ==="
Write-Host "Human approval received."
Write-Host "Executing remediation..."
Write-Host ""

aws lambda invoke `
  --function-name ai-troubleshooter `
  --payload '{"approved":true}' `
  --cli-binary-format raw-in-base64-out `
  --region ap-southeast-1 `
  response.json | Out-Null

$outer = Get-Content response.json -Raw | ConvertFrom-Json
$result = $outer.body | ConvertFrom-Json

Write-Host "=== AGENT DIAGNOSIS ==="
Write-Host ""
$result.diagnosis | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "=== REMEDIATION PERFORMED ==="
Write-Host ""
$result.remediation | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "=== VERIFICATION ==="
Write-Host ""
$result.verification | ConvertTo-Json -Depth 10

Write-Host ""
Write-Host "=== APPLICATION VERIFICATION ==="
Write-Host ""
$result.application_verification | ConvertTo-Json -Depth 10

Write-Host ""