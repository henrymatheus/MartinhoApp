# Liga, desliga ou mostra o estado do PostgreSQL de desenvolvimento local.
# Uso (dentro de backend):  .\scripts\banco-local.ps1 ligar | desligar | status
#
# O PostgreSQL fica em %LOCALAPPDATA%\Martinho\postgres e escuta só em
# localhost:55432, então não é acessível por outros computadores da rede.

param([ValidateSet('ligar', 'desligar', 'status')][string]$acao = 'status')

$pg = Join-Path $env:LOCALAPPDATA 'Martinho\postgres'
$pgCtl = Join-Path $pg 'bin\pg_ctl.exe'
$dados = Join-Path $pg 'data'

if (-not (Test-Path $pgCtl)) {
    Write-Error "PostgreSQL não encontrado em $pg."
    exit 1
}

switch ($acao) {
    'ligar' { & $pgCtl -D $dados -o '-p 55432 -c listen_addresses=localhost' -l (Join-Path $pg 'postgres.log') start -w }
    'desligar' { & $pgCtl -D $dados stop -m fast }
    'status' { & $pgCtl -D $dados status }
}
