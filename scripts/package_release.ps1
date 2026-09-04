param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$appFolder = Join-Path $projectRoot "AstralOptimizer"
$configPath = Join-Path $projectRoot "app\config.py"
$releaseFolder = Join-Path $projectRoot "release"

if (-not (Test-Path -LiteralPath (Join-Path $appFolder "AstralOptimizer.exe") -PathType Leaf)) {
    throw "Executável não encontrado. Execute scripts\build_executable.ps1 primeiro."
}

if (-not $Version) {
    $match = Select-String -Path $configPath -Pattern '^APP_VERSION\s*=\s*"([^"]+)"$'
    if (-not $match) {
        throw "Não foi possível ler APP_VERSION em app\config.py."
    }
    $Version = $match.Matches[0].Groups[1].Value
}

New-Item -ItemType Directory -Force -Path $releaseFolder | Out-Null
$archiveName = "AstralOptimizer-v$Version-Windows.zip"
$archivePath = Join-Path $releaseFolder $archiveName
$checksumPath = "$archivePath.sha256"

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
Compress-Archive -LiteralPath $appFolder -DestinationPath $archivePath -CompressionLevel Optimal
$hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -LiteralPath $checksumPath -Value "$hash  $archiveName" -Encoding ascii

Write-Host "Release preparada:"
Write-Host "  $archivePath"
Write-Host "  $checksumPath"
