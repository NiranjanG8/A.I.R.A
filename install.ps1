param(
    [string]$Python = "python",
    [string]$OllamaModel = "auto",
    [switch]$SkipOllama,
    [switch]$SkipModelDownloads
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "[install] Starting Aira installer..." -ForegroundColor Cyan

$argsList = @("installer.py", "--python", $Python, "--ollama-model", $OllamaModel)
if ($SkipOllama) {
    $argsList += "--skip-ollama"
}
if ($SkipModelDownloads) {
    $argsList += "--skip-model-downloads"
}

& $Python @argsList

Write-Host "[install] Done." -ForegroundColor Green
