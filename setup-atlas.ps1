# GeoGuessr Atlas : crée (et migre) l'arborescence images\ et le raccourci de lancement.
# Idempotent : relance-le quand tu veux, rien n'est écrasé ni supprimé.
# Lancement, depuis le dossier Atlas :
#   powershell -ExecutionPolicy Bypass -File .\setup-atlas.ps1

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Images = Join-Path $Root "images"
New-Item -ItemType Directory -Force -Path $Images | Out-Null

# Pays (ajoute ou retire des lignes "ISO Name" ; noms sans accents pour éviter tout souci d'encodage)
$Countries = @(
    "AD Andorra",
    "AE United Arab Emirates",
    "AL Albania",
    "AR Argentina",
    "AS American Samoa",
    "AT Austria",
    "AU Australia",
    "AX Aland Islands",
    "BD Bangladesh",
    "BE Belgium",
    "BG Bulgaria",
    "BM Bermuda",
    "BO Bolivia",
    "BR Brazil",
    "BT Bhutan",
    "BW Botswana",
    "CA Canada",
    "CH Switzerland",
    "CL Chile",
    "CO Colombia",
    "CR Costa Rica",
    "CW Curacao",
    "CX Christmas Island",
    "CZ Czechia",
    "DE Germany",
    "DK Denmark",
    "DO Dominican Republic",
    "EC Ecuador",
    "EE Estonia",
    "ES Spain",
    "FI Finland",
    "FO Faroe Islands",
    "FR France",
    "GB United Kingdom",
    "GG Guernsey",
    "GH Ghana",
    "GI Gibraltar",
    "GL Greenland",
    "GR Greece",
    "GT Guatemala",
    "GU Guam",
    "HK Hong Kong",
    "HR Croatia",
    "HU Hungary",
    "ID Indonesia",
    "IE Ireland",
    "IL Israel",
    "IM Isle of Man",
    "IN India",
    "IS Iceland",
    "IT Italy",
    "JE Jersey",
    "JO Jordan",
    "JP Japan",
    "KE Kenya",
    "KG Kyrgyzstan",
    "KH Cambodia",
    "KR South Korea",
    "KZ Kazakhstan",
    "LA Laos",
    "LB Lebanon",
    "LI Liechtenstein",
    "LK Sri Lanka",
    "LS Lesotho",
    "LT Lithuania",
    "LU Luxembourg",
    "LV Latvia",
    "MC Monaco",
    "ME Montenegro",
    "MG Madagascar",
    "MK North Macedonia",
    "MN Mongolia",
    "MO Macau",
    "MP Northern Mariana Islands",
    "MT Malta",
    "MX Mexico",
    "MY Malaysia",
    "NA Namibia",
    "NG Nigeria",
    "NL Netherlands",
    "NO Norway",
    "NP Nepal",
    "NZ New Zealand",
    "OM Oman",
    "PA Panama",
    "PE Peru",
    "PH Philippines",
    "PL Poland",
    "PR Puerto Rico",
    "PS Palestine",
    "PT Portugal",
    "PY Paraguay",
    "QA Qatar",
    "RE Reunion",
    "RO Romania",
    "RS Serbia",
    "RU Russia",
    "RW Rwanda",
    "SE Sweden",
    "SG Singapore",
    "SI Slovenia",
    "SJ Svalbard",
    "SK Slovakia",
    "SM San Marino",
    "SN Senegal",
    "SZ Eswatini",
    "TH Thailand",
    "TN Tunisia",
    "TR Turkey",
    "TW Taiwan",
    "UA Ukraine",
    "UG Uganda",
    "US United States",
    "UY Uruguay",
    "VI US Virgin Islands",
    "VN Vietnam",
    "ZA South Africa"
)

# Anciens noms de dossiers (v2, en français) -> nouveaux noms
$TypeMigration = @{
    "paysage" = "landscape"
    "langue" = "language"
    "architecture" = "architecture"
    "plaque" = "plate"
    "bollard" = "bollard"
    "poteau" = "pole"
    "panneau" = "sign"
    "marquage" = "road-lines"
    "telephone" = "phone"
    "voiture" = "car"
    "sol" = "soil"
    "drapeau" = "flag"
    "autre" = "other"
}
$ScopeMigration = @{ "_monde" = "_world"; "_clusters\cyrillique" = "_clusters\cyrillic" }

$Config = Get-Content (Join-Path $Root "config.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$Types = $Config.types | ForEach-Object { $_.key }
$Clusters = $Config.clusters.PSObject.Properties.Name

# Déplace le contenu de $From dans $To (fusion si $To existe déjà), puis supprime $From s'il est vide
function Merge-Folder($From, $To) {
    if (-not (Test-Path -LiteralPath $From)) { return }
    if ($From -eq $To) { return }
    if (-not (Test-Path -LiteralPath $To)) {
        Move-Item -LiteralPath $From -Destination $To
        return
    }
    foreach ($item in Get-ChildItem -LiteralPath $From -Force) {
        $dest = Join-Path $To $item.Name
        if ($item.PSIsContainer) { Merge-Folder $item.FullName $dest }
        elseif (-not (Test-Path -LiteralPath $dest)) { Move-Item -LiteralPath $item.FullName -Destination $dest }
        else { Write-Warning "Conflit, laissé en place : $($item.FullName)" }
    }
    if (-not (Get-ChildItem -LiteralPath $From -Force)) { Remove-Item -LiteralPath $From }
}

# 1. Migration des scopes (_monde -> _world, clusters)
foreach ($old in $ScopeMigration.Keys) { Merge-Folder (Join-Path $Images $old) (Join-Path $Images $ScopeMigration[$old]) }

# 2. Dossiers pays renommés en anglais, d'après le code ISO en tête
$EnName = @{}
foreach ($c in $Countries) { $EnName[$c.Substring(0, 2)] = $c }
foreach ($dir in Get-ChildItem -LiteralPath $Images -Directory | Where-Object { $_.Name -notlike "_*" }) {
    $iso = $dir.Name.Substring(0, [Math]::Min(2, $dir.Name.Length)).ToUpper()
    if ($EnName.ContainsKey($iso) -and $dir.Name -cne $EnName[$iso]) {
        Merge-Folder $dir.FullName (Join-Path $Images $EnName[$iso])
    }
}

# 3. Sous-dossiers de type renommés en anglais, dans tous les scopes
$Scopes = @(Get-ChildItem -LiteralPath $Images -Directory | Where-Object { $_.Name -notlike "_*" })
foreach ($s in "_multi", "_clusters") {
    $p = Join-Path $Images $s
    if (Test-Path $p) { $Scopes += Get-ChildItem -LiteralPath $p -Directory }
}
if (Test-Path (Join-Path $Images "_world")) { $Scopes += Get-Item (Join-Path $Images "_world") }
foreach ($scope in $Scopes) {
    foreach ($t in Get-ChildItem -LiteralPath $scope.FullName -Directory) {
        $parts = $t.Name.ToLower().Split("+") | ForEach-Object { if ($TypeMigration.ContainsKey($_)) { $TypeMigration[$_] } else { $_ } }
        $newName = $parts -join "+"
        if ($newName -cne $t.Name) { Merge-Folder $t.FullName (Join-Path $scope.FullName $newName) }
    }
}

# 4. Création des dossiers manquants
function New-TypeFolders($Parent) {
    foreach ($t in $Types) { New-Item -ItemType Directory -Force -Path (Join-Path $Parent $t) | Out-Null }
}
foreach ($c in $Countries) { New-TypeFolders (Join-Path $Images $c) }
foreach ($k in $Clusters)  { New-TypeFolders (Join-Path $Images "_clusters\$k") }
New-TypeFolders (Join-Path $Images "_world")
New-Item -ItemType Directory -Force -Path (Join-Path $Images "_multi") | Out-Null

Write-Host "Arborescence prête : $($Countries.Count) pays, $($Types.Count) types, $(@($Clusters).Count) cluster(s)."

# 5. Raccourci : la page en fenêtre d'application (Edge, sinon Chrome)
$Browser = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($Browser) {
    $Url = ([System.Uri](Join-Path $Root "index.html")).AbsoluteUri
    $Shell = New-Object -ComObject WScript.Shell
    $Link = $Shell.CreateShortcut((Join-Path $Root "GeoGuessr Atlas.lnk"))
    $Link.TargetPath = $Browser
    $Link.Arguments = "--app=`"$Url`" --window-size=1600,950"
    $Link.WorkingDirectory = $Root
    $Link.Save()
    Write-Host "Raccourci à jour : GeoGuessr Atlas.lnk"
}
