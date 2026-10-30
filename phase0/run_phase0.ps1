<#
  Phase 0 runner: executes nx_phase0_verify.py with NX run_journal.exe (headless)
  and prints the step results from result.json.
  Usage:
    .\run_phase0.ps1
    .\run_phase0.ps1 -NxBin 'C:\Program Files\Siemens\NX2306\NXBIN'
#>
param(
    [string]$NxBin = '',
    [string]$OutDir = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $root 'nx_phase0_verify.py'
if (-not $OutDir) { $OutDir = Join-Path $root 'output' }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path

function Find-RunJournal([string]$Hint) {
    $cands = @()
    if ($Hint) { $cands += (Join-Path $Hint 'run_journal.exe') }
    if ($env:UGII_BASE_DIR) { $cands += (Join-Path (Join-Path $env:UGII_BASE_DIR 'NXBIN') 'run_journal.exe') }
    foreach ($c in $cands) { if (Test-Path $c) { return $c } }
    $siemens = Join-Path $env:ProgramFiles 'Siemens'
    if (Test-Path $siemens) {
        $hit = Get-ChildItem $siemens -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path (Join-Path $_.FullName 'NXBIN') 'run_journal.exe' } |
            Where-Object { Test-Path $_ } |
            Sort-Object -Descending |
            Select-Object -First 1
        if ($hit) { return $hit }
    }
    return $null
}

$runJournal = Find-RunJournal $NxBin
if (-not $runJournal) {
    Write-Host 'run_journal.exe not found. Pass -NxBin <NX install>\NXBIN or set UGII_BASE_DIR.'
    exit 2
}

if (-not $env:UGII_BASE_DIR) {
    $env:UGII_BASE_DIR = Split-Path -Parent (Split-Path -Parent $runJournal)
}
$env:NX_PHASE0_OUT = $OutDir

$resultFile = Join-Path $OutDir 'result.json'
if (Test-Path $resultFile) { Remove-Item $resultFile -Force }

Write-Host ('run_journal : ' + $runJournal)
Write-Host ('UGII_BASE_DIR: ' + $env:UGII_BASE_DIR)
Write-Host ('script      : ' + $script)
Write-Host ('output dir  : ' + $OutDir)
Write-Host '--- running NX ---'

& $runJournal $script
$exitCode = $LASTEXITCODE

Write-Host '--- NX finished ---'
if (-not (Test-Path $resultFile)) {
    Write-Host ('FAIL: result.json was not produced (run_journal exit code ' + $exitCode + ').')
    Write-Host 'Check the NX license (UGS_LICENSE_SERVER) and that NX starts normally.'
    exit 1
}

$res = Get-Content $resultFile -Raw -Encoding UTF8 | ConvertFrom-Json
if ($res.nx) {
    Write-Host ('NX base dir : ' + $res.nx.UGII_BASE_DIR)
    Write-Host ('NX python   : ' + $res.nx.python)
}
foreach ($s in $res.steps) {
    Write-Host ('[{0}] {1} ({2} ms)' -f $s.status, $s.name, $s.ms)
    if ($s.error) { Write-Host ('      ' + $s.error) }
}

if ($res.success) {
    Write-Host 'PHASE 0 PASSED'
    Write-Host ('Part saved: ' + $res.part_path)
    exit 0
} else {
    Write-Host ('PHASE 0 FAILED: ' + $res.error)
    Write-Host ('Details: ' + $resultFile)
    exit 1
}
