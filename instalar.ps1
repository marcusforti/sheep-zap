# Instala a skill sheep-zap no Windows, sem admin e sem Git.
# irm https://raw.githubusercontent.com/marcusforti/sheep-zap/main/instalar.ps1 | iex
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $tmp = Join-Path $env:TEMP ('sheep-zap-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Force $tmp | Out-Null
    $repo = $env:SHEEP_ZAP_ORIGEM
    if (-not $repo) {
        $zip = Join-Path $tmp 'repo.zip'
        Invoke-WebRequest 'https://github.com/marcusforti/sheep-zap/archive/refs/heads/main.zip' -OutFile $zip -UseBasicParsing
        Expand-Archive -LiteralPath $zip -DestinationPath $tmp -Force
        $repo = Join-Path $tmp 'sheep-zap-main'
    }
    $origem = Join-Path $repo 'skill\sheep-zap'
    if (-not (Test-Path (Join-Path $origem 'SKILL.md'))) { throw 'Nao achei a skill no pacote baixado.' }
    $alvos = @((Join-Path $env:USERPROFILE '.claude\skills'), (Join-Path $env:USERPROFILE '.agents\skills'))
    $casa = if ($env:SHEEP_HOME) { $env:SHEEP_HOME } else { Join-Path $env:USERPROFILE 'Sheep' }
    if (Test-Path $casa) { $alvos += (Join-Path $casa '.claude\skills'), (Join-Path $casa '.agents\skills') }
    foreach ($alvo in $alvos) {
        New-Item -ItemType Directory -Force $alvo | Out-Null
        $destino = Join-Path $alvo 'sheep-zap'
        $novo = "$destino.novo"
        $velho = "$destino.velho"
        Remove-Item -Recurse -Force $novo, $velho -ErrorAction SilentlyContinue
        # Monta a pasta nova ao lado e troca no fim: se algo falhar no meio, a versão antiga continua inteira.
        Copy-Item -Recurse -Force $origem $novo
        Get-ChildItem $novo -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force
        if (Test-Path $destino) { Rename-Item $destino 'sheep-zap.velho' }
        Rename-Item $novo 'sheep-zap'
        Remove-Item -Recurse -Force $velho -ErrorAction SilentlyContinue
    }
    Write-Host ''
    Write-Host 'sheep-zap instalada.' -ForegroundColor Green
    Write-Host 'Abra o Claude Code e escreva: /sheep-zap'
    Write-Host 'Se o servico ja estava ligado, peca para o agente reiniciar.'
} catch {
    Write-Host "Nao consegui instalar: $_" -ForegroundColor Red
} finally {
    if ($tmp -and (Test-Path $tmp)) { Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue }
}
