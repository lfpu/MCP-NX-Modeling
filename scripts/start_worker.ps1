# Start the NX worker manually (optional: the MCP server auto-starts it when NX_MCP_AUTOSTART != 0).
param(
    [string]$NxBin = '',
    [int]$Port = 8765
)

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $NxBin) {
    $hit = Get-ChildItem (Join-Path $env:ProgramFiles 'Siemens') -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Join-Path (Join-Path $_.FullName 'NXBIN') 'run_journal.exe' } |
        Where-Object { Test-Path $_ } | Sort-Object -Descending | Select-Object -First 1
    if (-not $hit) { Write-Host 'run_journal.exe not found, pass -NxBin'; exit 2 }
} else {
    $hit = Join-Path $NxBin 'run_journal.exe'
}
$env:NX_MCP_ROOT = $root
$env:NX_MCP_PORT = $Port
if (-not $env:UGII_BASE_DIR) { $env:UGII_BASE_DIR = Split-Path -Parent (Split-Path -Parent $hit) }
Write-Host ('starting worker with ' + $hit + ' on port ' + $Port)
Write-Host 'log: logs/nx_worker.log   (Ctrl+C or nx worker shutdown to stop)'
& $hit (Join-Path $root 'nx_worker\main.py')
