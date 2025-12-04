# PowerShell script to add Windows Firewall rule for Face Recognition Backend
# Run this as Administrator: Right-click -> Run with PowerShell (as Admin)

Write-Host "=" -NoNewline -ForegroundColor Blue
Write-Host ("=" * 69) -ForegroundColor Blue
Write-Host "  Adding Windows Firewall Rule for Port 5000" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Blue
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator!" -ForegroundColor Red
    Write-Host ""
    Write-Host "To run as Administrator:" -ForegroundColor Yellow
    Write-Host "  1. Right-click on this file (add_firewall_rule.ps1)" -ForegroundColor Yellow
    Write-Host "  2. Select 'Run with PowerShell'" -ForegroundColor Yellow
    Write-Host "  3. Click 'Yes' when prompted for administrator access" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run this command in an Administrator PowerShell:" -ForegroundColor Yellow
    Write-Host "  cd '$PSScriptRoot'" -ForegroundColor White
    Write-Host "  .\add_firewall_rule.ps1" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Running with Administrator privileges..." -ForegroundColor Green
Write-Host ""

# Check if rule already exists
Write-Host "[1] Checking if firewall rule already exists..." -ForegroundColor Yellow
$existingRule = Get-NetFirewallRule -DisplayName "Face Recognition Backend Port 5000" -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "    Rule already exists. Removing old rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "Face Recognition Backend Port 5000"
    Write-Host "    Old rule removed." -ForegroundColor Green
}

# Add firewall rule for INBOUND traffic
Write-Host ""
Write-Host "[2] Adding firewall rule for INBOUND connections on port 5000..." -ForegroundColor Yellow

try {
    netsh advfirewall firewall add rule `
        name="Face Recognition Backend Port 5000" `
        dir=in `
        action=allow `
        protocol=TCP `
        localport=5000 `
        profile=any `
        description="Allow incoming connections for Face Recognition Backend on port 5000"

    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [SUCCESS] Firewall rule added successfully!" -ForegroundColor Green
    } else {
        throw "netsh command failed with exit code $LASTEXITCODE"
    }
} catch {
    Write-Host "    [ERROR] Failed to add firewall rule: $_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Verify the rule was added
Write-Host ""
Write-Host "[3] Verifying firewall rule..." -ForegroundColor Yellow

$rule = Get-NetFirewallRule -DisplayName "Face Recognition Backend Port 5000" -ErrorAction SilentlyContinue

if ($rule) {
    Write-Host "    [SUCCESS] Rule verified!" -ForegroundColor Green
    Write-Host ""
    Write-Host "    Rule Details:" -ForegroundColor Cyan
    Write-Host "    - Name: $($rule.DisplayName)" -ForegroundColor White
    Write-Host "    - Direction: Inbound" -ForegroundColor White
    Write-Host "    - Action: Allow" -ForegroundColor White
    Write-Host "    - Protocol: TCP" -ForegroundColor White
    Write-Host "    - Port: 5000" -ForegroundColor White
    Write-Host "    - Enabled: $($rule.Enabled)" -ForegroundColor White
} else {
    Write-Host "    [WARNING] Could not verify rule, but netsh succeeded" -ForegroundColor Yellow
}

# Get local IP addresses
Write-Host ""
Write-Host "[4] Your network IP addresses:" -ForegroundColor Yellow

$ipAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" }

foreach ($ip in $ipAddresses) {
    Write-Host "    - $($ip.IPAddress)" -ForegroundColor White
}

# Summary
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Blue
Write-Host "  FIREWALL CONFIGURATION COMPLETE!" -ForegroundColor Green
Write-Host ("=" * 70) -ForegroundColor Blue
Write-Host ""
Write-Host "Your backend is now accessible from other devices on your network!" -ForegroundColor Green
Write-Host ""
Write-Host "To access from another device, use one of these URLs:" -ForegroundColor Cyan

foreach ($ip in $ipAddresses) {
    Write-Host "  http://$($ip.IPAddress):5000" -ForegroundColor White
}

Write-Host ""
Write-Host "Make sure your backend is running:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\python.exe backend\app.py" -ForegroundColor White
Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Blue
Write-Host ""
Read-Host "Press Enter to exit"
