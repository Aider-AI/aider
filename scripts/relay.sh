#!/usr/bin/env bash
# relay.sh — Linux/macOS entry point for aider-relay (KB-2026-039/043).
#
# Usage:
#   # New project — pull image, init, run relay:
#   bash scripts/relay.sh \
#     --repo /workspaces/my-java-project \
#     --image ghcr.io/senanayake/polyglot-devcontainers-java:main \
#     --init \
#     --autonomous --max-turns 30 --turn-timeout 120 \
#     --task-file .aider-relay/TASK.md
#
#   # Existing project — skip --init:
#   bash scripts/relay.sh \
#     --repo /workspaces/my-java-project \
#     --image ghcr.io/senanayake/polyglot-devcontainers-java:main \
#     --autonomous --max-turns 30 --turn-timeout 120 \
#     --task-file .aider-relay/TASK.md
#
#   # Pre-existing named container:
#   bash scripts/relay.sh \
#     --repo /workspaces/polyglot-devcontainers \
#     --podman-container polyglot-devcontainers \
#     --autonomous --max-turns 30 \
#     --task-file .aider-relay/TASK.md
#
# GH_TOKEN / GITHUB_TOKEN are auto-forwarded from host env if present.
# Pass additional container env vars with: --container-env KEY=VALUE
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATES_DIR="$SCRIPT_DIR/../templates"

REPO_DIR=""
IMAGE=""
CONTAINER_PATH=""
KEEP_CONTAINER=false
INIT_PROJECT=false
CONTAINER_NAME=""
WORKSPACE_FOLDER=""
PODMAN_CONTAINER=""
CONTAINER_ENV_ARGS=()   # -e KEY=VALUE pairs for podman run
PASS_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)             REPO_DIR="$2";                              shift 2 ;;
        --image)            IMAGE="$2";                                 shift 2 ;;
        --container-path)   CONTAINER_PATH="$2";                        shift 2 ;;
        --keep-container)   KEEP_CONTAINER=true;                        shift   ;;
        --init)             INIT_PROJECT=true;                          shift   ;;
        --container)        CONTAINER_NAME="$2";                        shift 2 ;;
        --workspace-folder) WORKSPACE_FOLDER="$2";                      shift 2 ;;
        --podman-container) PODMAN_CONTAINER="$2";                      shift 2 ;;
        --container-env)    CONTAINER_ENV_ARGS+=("-e" "$2");            shift 2 ;;
        *)                  PASS_ARGS+=("$1");                          shift   ;;
    esac
done

if [[ -n "$REPO_DIR" ]]; then cd "$REPO_DIR"; fi
CWD="$(pwd)"

# ── Validate gateway selection ────────────────────────────────────────────────
GATEWAY_COUNT=$(( (${#IMAGE} > 0) + (${#CONTAINER_NAME} > 0) + \
                  (${#WORKSPACE_FOLDER} > 0) + (${#PODMAN_CONTAINER} > 0) ))
if [[ $GATEWAY_COUNT -gt 1 ]]; then
    echo "[RELAY] Error: provide only one of --image, --container, --workspace-folder, or --podman-container."
    exit 1
fi

# ── Auto-forward git credentials from host ────────────────────────────────────
for token_key in GH_TOKEN GITHUB_TOKEN; do
    token_val="${!token_key:-}"
    if [[ -n "$token_val" ]]; then
        # Only add if not already explicitly provided via --container-env
        already=false
        for arg in "${CONTAINER_ENV_ARGS[@]:-}"; do
            [[ "$arg" == "${token_key}="* ]] && already=true && break
        done
        if [[ "$already" == "false" ]]; then
            CONTAINER_ENV_ARGS+=("-e" "${token_key}=${token_val}")
            echo "[RELAY] Auto-forwarding $token_key from host."
        fi
    fi
done

# ── Helper: configure git inside a running container ─────────────────────────
configure_container_git() {
    local container="$1"

    # safe.directory — avoids "dubious ownership" errors on mounted volumes
    podman exec "$container" git config --global safe.directory "*" 2>/dev/null || true

    # Identity defaults (only if not already configured)
    podman exec "$container" bash -c \
        'git config --global user.email >/dev/null 2>&1 || git config --global user.email "relay@aider-relay.local"' 2>/dev/null || true
    podman exec "$container" bash -c \
        'git config --global user.name >/dev/null 2>&1 || git config --global user.name "aider-relay"' 2>/dev/null || true

    # Credential store — write token via stdin to avoid quoting/escaping issues
    local token_value=""
    for arg in "${CONTAINER_ENV_ARGS[@]}"; do
        if [[ "$arg" == GH_TOKEN=* || "$arg" == GITHUB_TOKEN=* ]]; then
            token_value="${arg#*=}"
            break
        fi
    done

    if [[ -n "$token_value" ]]; then
        echo "[RELAY] Configuring git credential store in container..."
        printf 'https://x-access-token:%s@github.com\n' "$token_value" \
            | podman exec -i "$container" bash -c 'cat > ~/.git-credentials && chmod 600 ~/.git-credentials'
        podman exec "$container" git config --global credential.helper store
        echo "[RELAY] Git credentials ready."
    else
        echo "[RELAY] Warning: no GH_TOKEN found — git push will fail inside container."
        echo "  Set GH_TOKEN in your environment or pass --container-env GH_TOKEN=<token>."
    fi
}

# ── Compute exec prefix and start / create container ─────────────────────────
EXEC_PREFIX=""
EPHEMERAL_NAME=""
ACTIVE_CONTAINER=""   # set for podman modes; used for git setup and --init

if [[ -n "$IMAGE" ]]; then
    REPO_NAME="$(basename "$CWD")"
    TIMESTAMP="$(date +%Y%m%d%H%M%S)"
    EPHEMERAL_NAME="aider-relay-${REPO_NAME}-${TIMESTAMP}"
    MOUNT_TARGET="${CONTAINER_PATH:-/workspaces/$REPO_NAME}"

    echo "[RELAY] Image:     $IMAGE"
    echo "[RELAY] Container: $EPHEMERAL_NAME (ephemeral)"
    echo "[RELAY] Mount:     $CWD -> $MOUNT_TARGET"

    podman run -d \
        --name "$EPHEMERAL_NAME" \
        -v "${CWD}:${MOUNT_TARGET}" \
        -w "$MOUNT_TARGET" \
        "${CONTAINER_ENV_ARGS[@]}" \
        "$IMAGE" \
        sleep infinity

    echo "[RELAY] Container started."
    EXEC_PREFIX="podman exec $EPHEMERAL_NAME"
    ACTIVE_CONTAINER="$EPHEMERAL_NAME"

elif [[ -n "$PODMAN_CONTAINER" ]]; then
    if ! podman container exists "$PODMAN_CONTAINER" 2>/dev/null; then
        echo "[RELAY] Error: podman container '$PODMAN_CONTAINER' does not exist."
        exit 1
    fi
    podman start "$PODMAN_CONTAINER" 2>/dev/null || true
    echo "[RELAY] Gateway: podman container '$PODMAN_CONTAINER'"
    EXEC_PREFIX="podman exec $PODMAN_CONTAINER"
    ACTIVE_CONTAINER="$PODMAN_CONTAINER"

elif [[ -n "$CONTAINER_NAME" ]]; then
    echo "[RELAY] Gateway: devpod container '$CONTAINER_NAME'"
    echo "[RELAY] Ensuring container is running..."
    devpod up "$CONTAINER_NAME" --ide none 2>&1 | tail -3 || true
    EXEC_PREFIX="devpod exec $CONTAINER_NAME --"

elif [[ -n "$WORKSPACE_FOLDER" ]]; then
    EXEC_PREFIX="devcontainer exec --workspace-folder $WORKSPACE_FOLDER --"
    echo "[RELAY] Gateway: devcontainer at '$WORKSPACE_FOLDER'"
fi

# ── Configure git in container (podman modes only) ───────────────────────────
if [[ -n "$ACTIVE_CONTAINER" ]]; then
    configure_container_git "$ACTIVE_CONTAINER"
fi

# ── Run task init if requested ────────────────────────────────────────────────
if [[ "$INIT_PROJECT" == "true" && -n "$EXEC_PREFIX" ]]; then
    echo "[RELAY] Running task init in container..."
    $EXEC_PREFIX task init
    echo "[RELAY] Init complete."
fi

# ── Cleanup trap for ephemeral containers ────────────────────────────────────
cleanup() {
    if [[ -n "$EPHEMERAL_NAME" && "$KEEP_CONTAINER" == "false" ]]; then
        echo "[RELAY] Removing ephemeral container $EPHEMERAL_NAME..."
        podman stop "$EPHEMERAL_NAME" 2>/dev/null || true
        podman rm   "$EPHEMERAL_NAME" 2>/dev/null || true
        echo "[RELAY] Done."
    elif [[ -n "$EPHEMERAL_NAME" && "$KEEP_CONTAINER" == "true" ]]; then
        echo "[RELAY] Container $EPHEMERAL_NAME kept (--keep-container)."
        echo "  Remove with: podman rm -f $EPHEMERAL_NAME"
    fi
}
trap cleanup EXIT

# ── Apply host trust boundary ─────────────────────────────────────────────────
if [[ -n "$EXEC_PREFIX" ]]; then
    SETTINGS_DST="$CWD/.claude/settings.json"
    mkdir -p "$(dirname "$SETTINGS_DST")"
    cp "$TEMPLATES_DIR/claude-settings.json" "$SETTINGS_DST"
    echo "[RELAY] Wrote host trust boundary: $SETTINGS_DST"
    PASS_ARGS+=("--exec-prefix" "$EXEC_PREFIX")
fi

# ── Print task file preview ───────────────────────────────────────────────────
for i in "${!PASS_ARGS[@]}"; do
    if [[ "${PASS_ARGS[$i]}" == "--task-file" ]]; then
        TASK_FILE="${PASS_ARGS[$((i+1))]}"
        echo "[RELAY] Repo:      $CWD"
        echo "[RELAY] Task file: $(realpath "$TASK_FILE")"
        echo "[RELAY] --- first 8 lines ---"
        head -8 "$TASK_FILE" | sed 's/^/  /'
        echo "[RELAY] ----------------------"
        echo ""
        break
    fi
done

# ── Run relay ─────────────────────────────────────────────────────────────────
if command -v aider-relay &>/dev/null; then
    aider-relay "${PASS_ARGS[@]}"
elif command -v uv &>/dev/null; then
    uv run --project "$SCRIPT_DIR/.." aider-relay "${PASS_ARGS[@]}"
elif [[ -f "$SCRIPT_DIR/../.venv/bin/activate" ]]; then
    source "$SCRIPT_DIR/../.venv/bin/activate"
    python -m aider.relay.loop "${PASS_ARGS[@]}"
else
    echo "[RELAY] Cannot find aider-relay. Install with: uv pip install -e ."
    exit 1
fi
