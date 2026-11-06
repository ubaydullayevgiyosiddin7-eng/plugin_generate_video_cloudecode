# Links every skill in this repo into Claude Code. Safe to run again.
$root = Resolve-Path (Join-Path $PSScriptRoot '..\skills')
$target = Join-Path $env:USERPROFILE '.claude\skills'
New-Item -ItemType Directory -Force $target | Out-Null
Get-ChildItem $root -Directory | ForEach-Object {
    $link = Join-Path $target $_.Name
    if (Test-Path $link) {
        "bor: $($_.Name)"
    } else {
        New-Item -ItemType Junction -Path $link -Target $_.FullName | Out-Null
        "ulandi: $($_.Name)"
    }
}
