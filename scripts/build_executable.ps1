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

Write-Host "Executável criado em: $outputPath\AstralOptimizer.exe"
