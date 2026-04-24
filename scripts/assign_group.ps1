# DUAL_2PC 세션에 groupId 주입 wrapper (PowerShell 버전) — Phase 17.5
# Usage: .\scripts\assign_group.ps1 -GroupId <id> -DeA <url> -DeB <url> [-Secret <s>]
#   Secret: optional. 생략 시 env ENGINE_SECRET_KEY 사용함

param(
  [Parameter(Mandatory = $true)][string]$GroupId,
  [Parameter(Mandatory = $true)][string]$DeA,
  [Parameter(Mandatory = $true)][string]$DeB,
  [string]$Secret = $env:ENGINE_SECRET_KEY
)

if (-not $Secret) {
  Write-Error "secret missing: -Secret <s> or set env ENGINE_SECRET_KEY"
  exit 1
}

$headers = @{
  "Content-Type"    = "application/json"
  "X-Engine-Secret" = $Secret
}
$body = @{ group_id = $GroupId } | ConvertTo-Json -Compress

Write-Host "[assign] DE A -> $DeA/control/assign-group"
Invoke-RestMethod -Method POST -Uri "$DeA/control/assign-group" -Headers $headers -Body $body

Write-Host "[assign] DE B -> $DeB/control/assign-group"
Invoke-RestMethod -Method POST -Uri "$DeB/control/assign-group" -Headers $headers -Body $body

Write-Host "[assign] done"
