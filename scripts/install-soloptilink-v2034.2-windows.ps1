# =============================================================================
# SoloptiLinkAI v2034.2 - Windows Install Script
# Verified: 2026-05-18 via GitHub Actions windows-latest (run 26011000174)
# Usage   : iex ((iwr -useb "https://raw.githubusercontent.com/shibukai03/my-claude-bot/main/scripts/install-soloptilink-v2034.2-windows.ps1").Content)
# =============================================================================

$V = "2034.2"
$ErrorActionPreference = "Stop"
$tempDir = Join-Path $env:TEMP "sl-update-$V"
try {
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
    Set-Location $tempDir

    Write-Host "[1/6] Downloading tar.gz..."
    iwr -useb "https://github.com/onukih-design/soloptilink-releases/releases/download/v$V/soloptilink-update-v$V.tar.gz" -OutFile "sl.tar.gz"
    if (-not (Test-Path "sl.tar.gz") -or (Get-Item "sl.tar.gz").Length -lt 1MB) { throw "tar.gz download failed (size too small)" }

    Write-Host "[2/6] Downloading binary..."
    $BIN_ARCH = if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64') { 'arm64' } else { 'amd64' }
    New-Item -ItemType Directory -Force -Path "$HOME\.soloptilink","$HOME\.claude\skills" | Out-Null
    iwr -useb "https://github.com/onukih-design/soloptilink-releases/releases/download/v$V/soloptilink-windows-$BIN_ARCH.exe" -OutFile "$HOME\.soloptilink\soloptilink.exe"
    if (-not (Test-Path "$HOME\.soloptilink\soloptilink.exe") -or (Get-Item "$HOME\.soloptilink\soloptilink.exe").Length -lt 1MB) { throw "binary download failed for $BIN_ARCH" }

    Write-Host "[3/6] Extracting tarball..."
    & tar -xzf "sl.tar.gz" -C "$HOME\.soloptilink" --strip-components=1 --exclude='._*'
    if ($LASTEXITCODE -ne 0) { throw "tar extract failed (exit=$LASTEXITCODE)" }
    if (-not (Test-Path "$HOME\.soloptilink\lib\license-guard.sh")) { throw "lib/license-guard.sh not found after extraction" }
    if (-not (Test-Path "$HOME\.soloptilink\chain.sh")) { throw "chain.sh not found after extraction" }

    Write-Host "[4/6] Syncing skills to Claude Code..."
    Copy-Item -Recurse -Force "$HOME\.soloptilink\skills\*" "$HOME\.claude\skills\"
    $skillCount = (Get-ChildItem "$HOME\.claude\skills" -ErrorAction SilentlyContinue).Count

    Write-Host "[5/6] CRLF -> LF normalization on .sh files..."
    Get-ChildItem "$HOME\.soloptilink" -Filter "*.sh" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
            if ($bytes -contains 13) {
                $text = [System.IO.File]::ReadAllText($_.FullName) -replace "`r`n","`n" -replace "`r","`n"
                [System.IO.File]::WriteAllText($_.FullName, $text, [System.Text.UTF8Encoding]::new($false))
            }
        } catch {}
    }

    Write-Host "[6/6] Version check..."
    $versionOut = & "$HOME\.soloptilink\soloptilink.exe" --version 2>&1
    Write-Host "  $versionOut"
    if ($versionOut -notmatch "v$V") { throw "Version mismatch: '$versionOut' does not contain v$V" }

    Write-Host ""
    Write-Host "================================================"
    Write-Host "  SoloptiLinkAI v$V install complete"
    Write-Host "================================================"
    Write-Host "  ~/.soloptilink/  : $((Get-ChildItem "$HOME\.soloptilink").Count) items"
    Write-Host "  ~/.claude/skills/: $skillCount skills"
    Write-Host ""
    Write-Host "Next: open Claude Code and run /soloptilink-boost"
}
catch {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "  FAILED: $_" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    exit 1
}
finally {
    if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }
}
