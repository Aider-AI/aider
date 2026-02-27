import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SLMSettings:
    """Configuration for the SLM (Strategic Liquidity Manager) service.

    This service is meant to run on Fly.io and consume Fly's internal NATS log stream
    (nats://[fdaa::3]:4223).
    """

    # Fly log stream auth: username=org slug, password=fly token.
    fly_org: str | None
    fly_api_token: str | None

    # The Fly app name of the *trading bot* whose logs we want to subscribe to.
    slm_bot_app_name: str | None

    # Internal Fly NATS endpoint.
    nats_url: str

    # NATS subject to subscribe to. If not explicitly set, we subscribe to the
    # Fly log subject for the bot app: logs.<app>.>
    nats_subject: str | None

    # Optional queue group name for HA.
    nats_queue: str | None

    # Where the target repo to edit lives inside the SLM machine.
    repo_path: str

    # Optional URL to clone into repo_path if repo_path doesn't exist.
    repo_git_url: str | None

    # Read-only rules injected into the Aider session.
    rules_path: str

    # Aider defaults (override via env).
    aider_model: str | None
    aider_editor_model: str | None
    aider_weak_model: str | None
    aider_architect: bool

    # GitHub sync
    github_token: str | None
    push_remote: str
    push_branch: str

    # Approval gate
    require_approval: bool

    # Sanity checks (commands can be overridden)
    cargo_check_cmd: str
    forge_test_cmd: str

    # Optional bot health check target via Fly private networking.
    bot_internal_url: str | None

    @classmethod
    def from_env(cls) -> "SLMSettings":
        bot_app = os.getenv("SLM_BOT_APP_NAME")
        nats_subject = os.getenv("SLM_NATS_SUBJECT")
        if not nats_subject and bot_app:
            nats_subject = f"logs.{bot_app}.>"

        return cls(
            fly_org=os.getenv("FLY_ORG"),
            fly_api_token=os.getenv("FLY_API_TOKEN"),
            slm_bot_app_name=bot_app,
            nats_url=os.getenv("NATS_URL", "nats://[fdaa::3]:4223"),
            nats_subject=nats_subject,
            nats_queue=os.getenv("SLM_NATS_QUEUE"),
            repo_path=os.getenv("SLM_REPO_PATH", "/data/repo"),
            repo_git_url=os.getenv("SLM_REPO_GIT_URL"),
            rules_path=os.getenv("SLM_RULES_PATH", "/app/blockchain_rules.md"),
            aider_model=os.getenv("SLM_AIDER_MODEL") or os.getenv("AIDER_MODEL"),
            aider_editor_model=os.getenv("SLM_AIDER_EDITOR_MODEL"),
            aider_weak_model=os.getenv("SLM_AIDER_WEAK_MODEL"),
            aider_architect=os.getenv("SLM_AIDER_ARCHITECT", "true").lower()
            not in ("0", "false", "no"),
            github_token=os.getenv("SLM_GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN"),
            push_remote=os.getenv("SLM_GIT_REMOTE", "origin"),
            push_branch=os.getenv("SLM_GIT_BRANCH", "main"),
            require_approval=os.getenv("SLM_REQUIRE_APPROVAL", "true").lower()
            not in ("0", "false", "no"),
            cargo_check_cmd=os.getenv(
                "SLM_CARGO_CHECK_CMD", "cargo check --workspace --all-targets"
            ),
            forge_test_cmd=os.getenv("SLM_FORGE_TEST_CMD", "forge test"),
            bot_internal_url=os.getenv("SLM_BOT_INTERNAL_URL"),
        )
