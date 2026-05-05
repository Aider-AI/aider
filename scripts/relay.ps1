#Requires -Version 5.1
<#
.SYNOPSIS
    Windows host entry point for aider-relay (KB-2026-039/043).

.DESCRIPTION
    Selects a polyglot execution environment, configures git credentials inside
    the container, and routes all build/test/git-write commands through it.

.EXAMPLE
    # New project — pull image, init, run relay:
    .\scripts\relay.ps1 `
        --repo C:\dev\my-java-project `
        --image ghcr.io/senanayake/polyglot-devcontainers-java:main `
        --init `
        --autonomous --max-turns 30 --turn-timeout 120 `
        --task-file .aider-relay\TASK.md

.EXAMPLE
    # Existing project — skip init:
    .\scripts\relay.ps1 `
        --repo C:\dev\my-java-project `
        --image ghcr.io/senanayake/polyglot-devcontainers-java:main `
        --autonomous --max-turns 30 --turn-timeout 120 `
        --task-file .aider-relay\TASK.md

.EXAMPLE
    # Pass extra env vars into the container:
    .\scripts\relay.ps1 `
        --repo C:\dev\my-project `
        --image ghcr.io/senanayake/polyglot-devcontainers-python-node:main `
        --container-env SOME_API_KEY=abc123 `
        --init --autonomous --max-turns 20 `
        --task-file .aider-relay\TASK.md
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot  = Split-Path -Parent $ScriptDir
$Templates = Join-Path $RepoRoot "templates"

# ── Parse args ────────────────────────────────────────────────────────────────
$RepoDir         = ""
$Image           = ""       # polyglot image ref → creates ephemeral container
$ContainerPath   = ""       # override mount target inside container
$KeepContainer   = $false
$InitProject     = $false   # run 'task init' before relay (new projects only)
$ContainerName   = ""       # devpod
$WorkspaceFolder = ""       # devcontainer CLI
$PodmanContainer = ""       # pre-existing named podman container
$ContainerEnvList = [System.Collections.Generic.List[string]]::new()
$PassArgs        = [System.Collections.Generic.List[string]]::new()

$i = 0
while ($i -lt $args.Count) {
    switch ($args[$i]) {
        "--repo"             { $RepoDir         = $args[++$i] }
        "--image"            { $Image            = $args[++$i] }
        "--container-path"   { $ContainerPath    = $args[++$i] }
        "--keep-container"   { $KeepContainer    = $true }
        "--init"             { $InitProject      = $true }
        "--container"        { $ContainerName    = $args[++$i] }
        "--workspace-folder" { $WorkspaceFolder  = $args[++$i] }
        "--podman-container" { $PodmanContainer  = $args[++$i] }
        "--container-env"    { $ContainerEnvList.Add($args[++$i]) }
        default              { $PassArgs.Add($args[$i]) }
    }
    $i++
}

# ── Change to target repo ─────────────────────────────────────────────────────
if ($RepoDir) { Set-Location $RepoDir }
$Cwd = (Get-Location).Path

# ── Validate gateway selection ────────────────────────────────────────────────
$GatewayCount = @($Image, $ContainerName, $WorkspaceFolder, $PodmanContainer) |
    Where-Object { $_ -ne "" } | Measure-Object | Select-Object -ExpandProperty Count
if ($GatewayCount -gt 1) {
    Write-Error "[RELAY] Provide only one of --image, --container, --workspace-folder, or --podman-container."
    exit 1
}

# ── Auto-forward git credentials from host if present ────────────────────────
# GH_TOKEN / GITHUB_TOKEN give the container git push capability (KB-2026-038).
foreach ($tokenKey in @("GH_TOKEN", "GITHUB_TOKEN")) {
    $tokenVal = [System.Environment]::GetEnvironmentVariable($tokenKey)
    if ($tokenVal -and -not ($ContainerEnvList | Where-Object { $_ -like "$tokenKey=*" })) {
        $ContainerEnvList.Add("$tokenKey=$tokenVal")
        Write-Host "[RELAY] Auto-forwarding $tokenKey from host."
    }
}

# Build -e flags for podman run
$PodmanEnvArgs = foreach ($e in $ContainerEnvList) { @("-e", $e) }

# ── Helper: configure git inside a running container ─────────────────────────
# Sets up credential store, safe.directory, and identity defaults.
function Set-ContainerGit {
    param([string]$Container)

    # safe.directory — avoids "dubious ownership" errors on mounted volumes
    podman exec $Container git config --global safe.directory "*" 2>$null

    # Identity defaults (only if not already configured in the image)
    podman exec $Container bash -c `
        'git config --global user.email >/dev/null 2>&1 || git config --global user.email "relay@aider-relay.local"' 2>$null
    podman exec $Container bash -c `
        'git config --global user.name >/dev/null 2>&1 || git config --global user.name "aider-relay"' 2>$null

    # Credential store — write GH_TOKEN / GITHUB_TOKEN via stdin to avoid quoting issues
    $token = $ContainerEnvList |
        Where-Object { $_ -like "GH_TOKEN=*" -or $_ -like "GITHUB_TOKEN=*" } |
        Select-Object -First 1
    if ($token) {
        $tokenValue = $token.Split("=", 2)[1]
        Write-Host "[RELAY] Configuring git credential store in container..."
        "https://x-access-token:$tokenValue@github.com" |
            podman exec -i $Container bash -c 'cat > ~/.git-credentials && chmod 600 ~/.git-credentials'
        podman exec $Container git config --global credential.helper store
        Write-Host "[RELAY] Git credentials ready."
    } else {
        Write-Host "[RELAY] Warning: no GH_TOKEN found — git push will fail inside container."
        Write-Host "  Set GH_TOKEN in your environment or pass --container-env GH_TOKEN=<token>."
    }
}

# ── Compute exec prefix and start / create container ─────────────────────────
$ExecPrefix    = ""
$EphemeralName = ""
$ActiveContainer = ""   # the container name for git setup and --init

if ($Image) {
    $RepoName      = (Get-Item $Cwd).Name
    $Timestamp     = Get-Date -Format "yyyyMMddHHmmss"
    $EphemeralName = "aider-relay-$RepoName-$Timestamp"
    $MountTarget   = if ($ContainerPath) { $ContainerPath } else { "/workspaces/$RepoName" }

    Write-Host "[RELAY] Image:     $Image"
    Write-Host "[RELAY] Container: $EphemeralName (ephemeral)"
    Write-Host "[RELAY] Mount:     $Cwd -> $MountTarget"

    & podman run -d --name $EphemeralName `
        -v "${Cwd}:${MountTarget}" -w $MountTarget `
        @PodmanEnvArgs $Image sleep infinity | Out-Null

    Write-Host "[RELAY] Container started."
    $ExecPrefix      = "podman exec $EphemeralName"
    $ActiveContainer = $EphemeralName

} elseif ($PodmanContainer) {
    if ((& podman container exists $PodmanContainer 2>$null; $LASTEXITCODE) -ne 0) {
        Write-Error "[RELAY] Podman container '$PodmanContainer' does not exist."
        exit 1
    }
    podman start $PodmanContainer 2>$null | Out-Null
    Write-Host "[RELAY] Gateway: podman container '$PodmanContainer'"
    $ExecPrefix      = "podman exec $PodmanContainer"
    $ActiveContainer = $PodmanContainer

} elseif ($ContainerName) {
    Write-Host "[RELAY] Gateway: devpod container '$ContainerName'"
    Write-Host "[RELAY] Ensuring container is running..."
    devpod up $ContainerName --ide none 2>&1 | Select-Object -Last 3
    $ExecPrefix = "devpod exec $ContainerName --"

} elseif ($WorkspaceFolder) {
    $ExecPrefix = "devcontainer exec --workspace-folder `"$WorkspaceFolder`" --"
    Write-Host "[RELAY] Gateway: devcontainer at '$WorkspaceFolder'"
}

# ── Configure git in container (podman modes only) ───────────────────────────
if ($ActiveContainer) {
    Set-ContainerGit -Container $ActiveContainer
}

# ── Run task init if requested ────────────────────────────────────────────────
if ($InitProject -and $ExecPrefix) {
    Write-Host "[RELAY] Running task init in container..."
    Invoke-Expression "$ExecPrefix task init"
    Write-Host "[RELAY] Init complete."
}

# ── Apply host trust boundary ─────────────────────────────────────────────────
if ($ExecPrefix) {
    $SettingsDst = Join-Path $Cwd ".claude\settings.json"
    New-Item -ItemType Directory -Force -Path (Split-Path $SettingsDst) | Out-Null
    Copy-Item (Join-Path $Templates "claude-settings.json") $SettingsDst -Force
    Write-Host "[RELAY] Wrote host trust boundary: $SettingsDst"
    $PassArgs.Add("--exec-prefix")
    $PassArgs.Add($ExecPrefix)
}

# ── Print task file preview ───────────────────────────────────────────────────
for ($j = 0; $j -lt $PassArgs.Count; $j++) {
    if ($PassArgs[$j] -eq "--task-file" -and $j + 1 -lt $PassArgs.Count) {
        $TaskFile = $PassArgs[$j + 1]
        $TaskPath = if ([System.IO.Path]::IsPathRooted($TaskFile)) {
            $TaskFile
        } else {
            Join-Path $Cwd $TaskFile
        }
        if (Test-Path $TaskPath) {
            Write-Host "[RELAY] Repo:      $Cwd"
            Write-Host "[RELAY] Task file: $TaskPath"
            Write-Host "[RELAY] --- first 8 lines ---"
            Get-Content $TaskPath | Select-Object -First 8 | ForEach-Object { "  $_" }
            Write-Host "[RELAY] ----------------------"
            Write-Host ""
        }
        break
    }
}

# ── Resolve Python / aider-relay invocation ───────────────────────────────────
function Invoke-Relay {
    param([string[]]$RelayArgs)
    if (Get-Command aider-relay -ErrorAction SilentlyContinue) {
        & aider-relay @RelayArgs; return
    }
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        & uv run --project $RepoRoot aider-relay @RelayArgs; return
    }
    $venvPy = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) {
        & $venvPy -m aider.relay.loop @RelayArgs; return
    }
    Write-Error "[RELAY] Cannot find aider-relay. Install with: cd $RepoRoot && uv pip install -e ."
    exit 1
}

# ── Run relay; clean up ephemeral container on exit ──────────────────────────
try {
    Invoke-Relay -RelayArgs $PassArgs.ToArray()
} finally {
    if ($EphemeralName -and -not $KeepContainer) {
        Write-Host "[RELAY] Removing ephemeral container $EphemeralName..."
        podman stop $EphemeralName 2>$null | Out-Null
        podman rm   $EphemeralName 2>$null | Out-Null
        Write-Host "[RELAY] Done."
    } elseif ($EphemeralName -and $KeepContainer) {
        Write-Host "[RELAY] Container $EphemeralName kept (--keep-container)."
        Write-Host "  Remove with: podman rm -f $EphemeralName"
    }
}
