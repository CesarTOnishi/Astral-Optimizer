$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$specPath = Join-Path $projectRoot "AstralOptimizer.spec"
$enginePath = Join-Path $projectRoot "third_party\fribbels-hsr-optimizer\.honkai-engine\benchmark-engine.js"
$outputPath = Join-Path $projectRoot "AstralOptimizer"
$workPath = Join-Path $projectRoot "build\pyinstaller"

if (-not (Test-Path -LiteralPath $enginePath -PathType Leaf)) {
    throw "Motor Fribbels não encontrado. Execute scripts\build_fribbels_engine.ps1 primeiro."
}

python -m PyInstaller --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller não instalado. Execute: python -m pip install pyinstaller"
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath $projectRoot `
    --workpath $workPath `
    $specPath

if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível criar o executável."
}

$configPath = Join-Path $projectRoot "app\config.py"
$versionMatch = Select-String -Path $configPath -Pattern '^APP_VERSION\s*=\s*"([^"]+)"$'
if (-not $versionMatch) {
    throw "Não foi possível ler APP_VERSION em app\config.py."
}
$version = $versionMatch.Matches[0].Groups[1].Value
@{
    name = "Astral Optimizer"
    version = $version
    built_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath "version.json") -Encoding UTF8

Write-Host "Executável criado em: $outputPath\AstralOptimizer.exe"
Write-Host "Versão do executável: $version"
