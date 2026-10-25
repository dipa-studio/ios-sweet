#Requires -Version 5.1
<#
.SYNOPSIS
    Boot a built ios-sweet image under the Windows QEMU. QEMU runs locally on
    Windows; WSL2 is only the build environment. Never modifies the source
    image (defaults to --disk-snapshot).
.EXAMPLE
    .\scripts\windows\boot-hackios.ps1 -Image output\ios16-20H392-hackios-xnu-v1.img `
        -Kernel xnu\out-0086-trace\kernel.development.sweet `
        -Adt research\vm\qemu-smp4-high.adt
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$Image,
    [Parameter(Mandatory=$true)][string]$Kernel,
    [string]$Adt,
    [string]$OutDir = "output\run",
    [int]$Secs = 3600,
    [int]$Cpus = 1,
    [switch]$NoSnapshot,
    [switch]$Input,
    [string]$Display = "gtk",
    [string]$ExtraCmdline = ""
)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Repo

function Resolve-Required([string]$Path, [string]$Label) {
    if (-not $Path) { throw "missing required parameter: $Label" }
    $full = [System.IO.Path]::GetFullPath($Path)
    if (-not (Test-Path $full)) { throw "$Label not found: $full" }
    return $full
}

$Image  = Resolve-Required $Image "Image"
$Kernel = Resolve-Required $Kernel "Kernel"

$Python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $Python) { throw "python not on PATH" }

$Runner = Join-Path $Repo "tools\qemu-sweet.py"
if (-not (Test-Path $Runner)) { throw "runner not found: $Runner" }

# --- payload ---------------------------------------------------------------
if (-not $Adt) {
    $Adt = Join-Path $Repo "research\vm\qemu-hackios.adt"
    if (-not (Test-Path $Adt)) {
        Write-Host "generating QEMU device tree -> $Adt"
        & $Python.Source (Join-Path $Repo "tools\mkadt.py") $Adt --qemu --highmem
        if ($LASTEXITCODE -ne 0) { throw "mkadt.py failed" }
    }
}
$Adt = Resolve-Required $Adt "Adt"

$Payload = Join-Path $Repo "output\payload-hackios.bin"
New-Item -ItemType Directory -Force -Path (Split-Path $Payload) | Out-Null
$Cmdline = "debug=0xc serial=3 cpus=$Cpus keepsyms=1 -enable_kprintf_spam -noprogress rd=vblk0 rootrw=1 virtio_blk=1 virtio_input=1 ramfb=1 sweetfb_noconsole=1"
if ($ExtraCmdline) { $Cmdline = "$Cmdline $ExtraCmdline" }

Write-Host "building payload"
& $Python.Source (Join-Path $Repo "tools\mkpayload.py") $Kernel $Adt $Payload --cmdline $Cmdline
if ($LASTEXITCODE -ne 0) { throw "mkpayload.py failed" }

# --- run QEMU --------------------------------------------------------------
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$Args = @(
    $Payload, $OutDir,
    "--secs", $Secs,
    "--cpu", "cortex-a76",
    "--smp", $Cpus,
    "--tb-mb", "512",
    "--disk", $Image,
    "--input",
    "--display", $Display
)
if (-not $NoSnapshot) { $Args += "--disk-snapshot" }

Write-Host "booting: python tools\qemu-sweet.py $($Args -join ' ')"
& $Python.Source $Runner @Args
$code = $LASTEXITCODE
Write-Host "qemu-sweet.py exit code: $code"
exit $code
