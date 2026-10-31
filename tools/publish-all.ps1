# Publie d'un coup tous les trainers qui ont des changements locaux.
# Chaque repo passe par son propre publish.ps1 : aperçu des fichiers, puis confirmation (o/N) repo par repo.
# Lancement : double-clic sur publish-all.cmd (dossier Atlas)

$ErrorActionPreference = "Continue"
$Root = Split-Path $PSScriptRoot -Parent          # ...\Desktop\Atlas
$Home_ = $env:USERPROFILE
$Py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Blocked = @()
$Repos = @(
  "$Home_\city-placer", "$Home_\bollards-trainer", "$Home_\phone-codes", "$Home_\indonesia-kabupaten",
  "$Home_\plate-trainer", "$Home_\vietnam-province-guesser", "$Home_\russian-pannels-learning",
  "$Home_\script-identifier-geoguessr", $Root
)
foreach ($r in $Repos) {
    if (-not (Test-Path "$r\.git")) { continue }
    $name = Split-Path $r -Leaf
    $dirty = git -C $r status --porcelain
    $ahead = git -C $r rev-list --count "@{u}..HEAD" 2>$null
    if (-not $dirty -and (-not $ahead -or $ahead -eq "0")) { Write-Host "$name : rien à publier" -ForegroundColor DarkGray; continue }
    if (-not (Test-Path "$r\publish.ps1")) { Write-Host "$name : pas de publish.ps1, ignoré" -ForegroundColor Yellow; continue }
    Write-Host "`n==================== $name ====================" -ForegroundColor Cyan
    # Tests de fumée (tools\smoke.py) : un repo en échec n'est pas publié
    & $Py "$Root\tools\smoke.py" $name
    $code = $LASTEXITCODE
    if ($code -eq 3) {
        $ans = Read-Host "Tests navigateur impossibles (installer : $Py -m pip install playwright). Publier $name quand même ? (o/N)"
        if ($ans -ne "o") { $Blocked += $name; continue }
    } elseif ($code -ne 0) {
        Write-Host "$name : tests en échec, NON publié (captures dans Atlas\_private_cache\smoke)" -ForegroundColor Red
        $Blocked += $name; continue
    }
    & powershell -NoProfile -ExecutionPolicy Bypass -File "$r\publish.ps1"
}
if ($Blocked) { Write-Host "`nNon publiés : $($Blocked -join ', ')" -ForegroundColor Red }
Write-Host "`nTerminé." -ForegroundColor Green
