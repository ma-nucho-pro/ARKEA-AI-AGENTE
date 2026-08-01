param(
  [Parameter(Mandatory=$false)][ValidatePattern('^v[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$')]
  [string]$Tag = 'v0.1.0',
  [switch]$Draft
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Release = Join-Path $Root 'release'
$Repository = 'ma-nucho-pro/ARKEA-AI-AGENTE'
$Assets = @(
  (Join-Path $Release '0_1-COMIENZA-POR-AQUI-ARKEA-AI-OmniAgent-Setup-0.1.0.exe'),
  (Join-Path $Release '0_1-ARKEA-AI-OmniAgent-Windows-x64-portable.zip'),
  (Join-Path $Release 'ARKEA-AI-OmniAgent-0.1.0-source.zip'),
  (Join-Path $Release 'SHA256SUMS.txt')
)

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
  throw 'Falta GitHub CLI (gh). Instálalo y ejecuta: gh auth login'
}

& gh auth status
if ($LASTEXITCODE -ne 0) { throw 'GitHub CLI no tiene una sesión válida.' }

foreach ($asset in $Assets) {
  if (-not (Test-Path -LiteralPath $asset -PathType Leaf)) {
    throw "Falta el artefacto: $asset. Ejecuta primero 0_1_CREAR_EXE_OMNIAGENT.cmd"
  }
  if ((Get-Item -LiteralPath $asset).Length -ge 2GB) {
    throw "El archivo supera el límite de 2 GiB por asset de GitHub Releases: $asset"
  }
}

& gh release view $Tag --repo $Repository 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  $arguments = @('release', 'create', $Tag, '--repo', $Repository, '--title', "ARKEA AI OmniAgent $Tag", '--generate-notes')
  if ($Draft) { $arguments += '--draft' }
  & gh @arguments
  if ($LASTEXITCODE -ne 0) { throw "No se pudo crear la Release $Tag" }
}

& gh release upload $Tag @Assets --repo $Repository --clobber
if ($LASTEXITCODE -ne 0) { throw "No se pudieron subir los archivos a la Release $Tag" }

Write-Host "Release publicada: $Tag" -ForegroundColor Green
