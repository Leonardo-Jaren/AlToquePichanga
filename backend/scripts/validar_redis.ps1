$ErrorActionPreference = 'Stop'

$raiz = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$archivoCompose = Join-Path $raiz 'compose.redis.dev.yml'
$proyectoCompose = 'altoque-pichanga-fase4d'
$python = Join-Path (Split-Path $PSScriptRoot -Parent) 'venv\Scripts\python.exe'
$redisAnterior = $env:ALTOQUE_TEST_REDIS_URL

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Instala Docker Desktop y habilita Docker Compose para levantar Redis aislado.'
}
if (-not (Test-Path -LiteralPath $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}

docker compose -p $proyectoCompose -f $archivoCompose up -d --wait redis
if ($LASTEXITCODE -ne 0) { throw 'No se pudo iniciar el servicio Redis local.' }

try {
    $pong = docker compose -p $proyectoCompose -f $archivoCompose exec -T redis redis-cli ping
    if ($LASTEXITCODE -ne 0 -or $pong -ne 'PONG') { throw 'Redis no respondió PONG.' }

    $env:ALTOQUE_TEST_REDIS_URL = 'redis://127.0.0.1:16379/1'
    Push-Location (Split-Path $PSScriptRoot -Parent)
    try {
        & $python -m pytest tests/test_fase4b_websocket.py -q
        if ($LASTEXITCODE -ne 0) { throw 'Falló la prueba Channels contra Redis real.' }
    } finally {
        Pop-Location
    }
} finally {
    if ($null -eq $redisAnterior) {
        Remove-Item Env:ALTOQUE_TEST_REDIS_URL -ErrorAction SilentlyContinue
    } else {
        $env:ALTOQUE_TEST_REDIS_URL = $redisAnterior
    }
}

Write-Output 'Redis permanece activo en 127.0.0.1:16379. Deténlo con docker compose -p altoque-pichanga-fase4d -f compose.redis.dev.yml down.'
