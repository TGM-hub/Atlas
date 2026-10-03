# Publie l'Atlas sur GitHub : build, aperçu de ce qui part, confirmation, commit, push.
# Lancement : double-clic sur publish.cmd (ou powershell -ExecutionPolicy Bypass -File .\publish.ps1)
# Prérequis : gh auth login (fait), Pages activé à la main sur TGM-hub/Atlas (branche main, racine).
# Relançable : initialise le dépôt la première fois, pousse les changements ensuite.

# "Continue" : sous Windows PowerShell 5.1, "Stop" transforme le stderr de git en erreur fatale.
$ErrorActionPreference = "Continue"
$Remote = "https://github.com/TGM-hub/Atlas.git"
Set-Location $PSScriptRoot
$env:PYTHONIOENCODING = "utf-8"

# 1. Build : on ne publie jamais un Atlas cassé
python build.py
if ($LASTEXITCODE -ne 0) { throw "Build en erreur : corrige les fichiers signalés avant de publier." }

# 2. Dépôt local (premier lancement)
if (-not (Test-Path ".git")) {
    git init -b main | Out-Null
    git remote add origin $Remote
    Write-Host "Dépôt initialisé, remote : $Remote"
}
git config core.quotepath false   # noms de fichiers accentués lisibles

# 3. Aperçu
git add -A
$staged = git diff --cached --name-status
$hasUpstream = git rev-parse --abbrev-ref "main@{upstream}" 2>$null
$ahead = if ($hasUpstream) { git rev-list --count "origin/main..main" } elseif (git rev-parse --verify -q HEAD) { "1" } else { "0" }
if (-not $staged -and $ahead -eq "0") { Write-Host "`nRien de nouveau à publier."; exit 0 }

if ($staged) {
    Write-Host "`nFichiers qui vont partir :" -ForegroundColor Cyan
    $staged | ForEach-Object { Write-Host "  $_" }
    $bytes = (git diff --cached --name-only | Where-Object { Test-Path -LiteralPath $_ } | ForEach-Object { (Get-Item -LiteralPath $_).Length } | Measure-Object -Sum).Sum
    Write-Host ("`n{0} fichier(s), {1:N1} Mo." -f @($staged).Count, ($bytes / 1MB))
} else {
    Write-Host "`nCommits locaux pas encore poussés :" -ForegroundColor Cyan
    git log --oneline -n 10
}
if ((Read-Host "Publier ? (o/N)") -notmatch '^[oOyY]') { git reset -q; Write-Host "Annulé, rien n'est parti."; exit 1 }

# 4. Commit et push
if ($staged) {
    $msg = Read-Host ("Message de commit (Entrée = « Atlas : mise à jour {0:yyyy-MM-dd} »)" -f (Get-Date))
    if (-not $msg) { $msg = "Atlas : mise à jour {0:yyyy-MM-dd}" -f (Get-Date) }
    git commit -q -m $msg -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    if ($LASTEXITCODE -ne 0) { throw "git commit a échoué" }
}
# Intègre d'abord ce qui a été poussé ailleurs (ex. README modifié sur GitHub)
if ($hasUpstream) {
    git pull --rebase origin main
    if ($LASTEXITCODE -ne 0) { git rebase --abort; throw "Conflit avec la version en ligne : rien n'est parti, demande de l'aide avant de relancer." }
}
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw "git push a échoué (voir le message ci-dessus)" }
Write-Host "`nPublié. En ligne d'ici une minute : https://tgm-hub.github.io/Atlas/" -ForegroundColor Green
