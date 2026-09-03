$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$engineRoot = Join-Path $projectRoot "third_party\fribbels-hsr-optimizer"
$bridgeRoot = Join-Path $PSScriptRoot "fribbels"

if (-not (Test-Path -LiteralPath (Join-Path $engineRoot "package.json"))) {
    throw "Repositório do Fribbels não encontrado. Execute: git submodule update --init --recursive"
}

Copy-Item -LiteralPath (Join-Path $bridgeRoot "honkaiBridge.ts") `
    -Destination (Join-Path $engineRoot "src\honkaiBridge.ts") -Force
Copy-Item -LiteralPath (Join-Path $bridgeRoot "vite.honkai.config.ts") `
    -Destination (Join-Path $engineRoot "vite.honkai.config.ts") -Force

Push-Location $engineRoot
try {
    npm ci --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw "npm ci falhou" }
    npx vite build --config vite.honkai.config.ts --configLoader native
    if ($LASTEXITCODE -ne 0) { throw "A compilação do motor falhou" }
} finally {
    Pop-Location
}

Write-Host "Motor Fribbels compilado com sucesso."
