#Requires -Version 5.1
<#
.SYNOPSIS
    Collect and summarize the boot evidence from a qemu-sweet.py output
    directory: manifest, result, serial, msgbuf, and snapshots.
.EXAMPLE
    .\scripts\windows\collect-boot-logs.ps1 -RunDir output\run
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$RunDir
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $RunDir)) { throw "run directory not found: $RunDir" }

function Show-File([string]$Path) {
    if (Test-Path $Path) {
        Write-Host "`n===== $Path =====" -ForegroundColor Cyan
        Get-Content $Path
    }
}

Show-File (Join-Path $RunDir "run-manifest.json")
Show-File (Join-Path $RunDir "result.json")

Write-Host "`n===== files =====" -ForegroundColor Cyan
Get-ChildItem $RunDir -Recurse -File |
    Group-Object Extension |
    Sort-Object Count -Descending |
    Select-Object Count, Name |
    Format-Table -AutoSize

Write-Host "===== framebuffer snapshots =====" -ForegroundColor Cyan
$fb = Get-ChildItem $RunDir -Recurse -Filter "fb.png" | Sort-Object FullName
Write-Host ("{0} framebuffer PNG(s)" -f $fb.Count)

Write-Host "===== msgbuf (guest console ring) =====" -ForegroundColor Cyan
$msgs = Get-ChildItem $RunDir -Recurse -Filter "msgbuf.txt" | Sort-Object FullName
if ($msgs) {
    Write-Host ("{0} msgbuf file(s); last:" -f $msgs.Count)
    Show-File $msgs[-1].FullName
}

Write-Host "===== panic scan =====" -ForegroundColor Cyan
$panicHits = Get-ChildItem $RunDir -Recurse -Include "msgbuf.txt","serial.txt" |
    Select-String -Pattern "panic\(|initproc failed|Halt/Restart Timed Out" -SimpleMatch:$false
if ($panicHits) {
    $panicHits | ForEach-Object { Write-Host "$($_.Path):$($_.LineNumber): $($_.Line)" -ForegroundColor Red }
} else {
    Write-Host "no panic signature found in captured text"
}

Write-Host "`ncollect-boot-logs complete for $RunDir"
