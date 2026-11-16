# Dot-source from PowerShell: . .\scripts\Enter-SONORA.ps1
$sonoraRoot = Split-Path -Parent $PSScriptRoot
$sonoraGit = 'C:\Program Files\Git\cmd'
if (Test-Path -LiteralPath (Join-Path $sonoraGit 'git.exe')) {
    if (($env:Path -split ';') -notcontains $sonoraGit) {
        $env:Path = "$sonoraGit;$env:Path"
    }
}
$env:SONORA_HOME = $sonoraRoot
Set-Location -LiteralPath $sonoraRoot
. (Join-Path $sonoraRoot '.venv\Scripts\Activate.ps1')
