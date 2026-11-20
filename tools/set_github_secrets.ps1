# Requires: gh auth login
# Sets Actions secrets for Aliyun deploy from local deploy key.
$ErrorActionPreference = "Stop"
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

$keyFile = Join-Path $env:USERPROFILE ".ssh\kb_deploy_ed25519"
if (-not (Test-Path $keyFile)) { throw "Missing $keyFile" }

gh secret set DEPLOY_HOST --body "47.95.28.202"
gh secret set DEPLOY_USER --body "root"
gh secret set DEPLOY_PATH --body "/opt/kb"
gh secret set DEPLOY_PORT --body "22"
Get-Content -Raw $keyFile | gh secret set DEPLOY_SSH_KEY
Write-Host "Secrets configured. Triggering workflow..."
gh workflow run "Deploy to Aliyun" --ref main
Start-Sleep -Seconds 5
gh run list --workflow=deploy.yml --limit 3
