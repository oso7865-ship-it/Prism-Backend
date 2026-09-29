"""Root-managed EC2 deployment entry point. Remote input contains no credentials."""

import argparse
import fcntl
import json
import os
import re
import stat
import subprocess
import sys
import time
import urllib.request
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

REPOSITORY = "ghcr.io/oso7865-ship-it/prism-backend-production"
SOURCE = "https://github.com/oso7865-ship-it/Prism-Backend"
SCHEMA_QUERY = """
import json
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine
from app.shared.config.settings import Settings
s = Settings(_env_file=None)
e = create_engine(s.database_url.get_secret_value(), connect_args={'connect_timeout': 10})
with e.connect() as c:
    current = list(MigrationContext.configure(c).get_current_heads())
target = ScriptDirectory.from_config(Config('alembic.ini')).get_heads()
print(json.dumps({'current': current, 'target': target}))
e.dispose()
"""


class DeployError(Exception):
    pass


def identity(image, revision, sequence):
    if not re.fullmatch(re.escape(REPOSITORY) + r"@sha256:[0-9a-f]{64}", image):
        raise DeployError("INVALID_IMAGE")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise DeployError("INVALID_REVISION")
    if not isinstance(sequence, int) or not 1 <= sequence < 2**53:
        raise DeployError("INVALID_SEQUENCE")


def protected_file(path, secret=False, root_owned=False):
    path = Path(path)
    if not path.is_absolute() or path.is_symlink():
        raise DeployError("UNSAFE_FILE_PATH")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_mode & (0o077 if secret else 0o022):
        raise DeployError("UNSAFE_FILE_PERMISSIONS")
    if root_owned and info.st_uid != 0:
        raise DeployError("FILE_MUST_BE_ROOT_OWNED")
    for parent in path.parents:
        if parent.is_symlink() or parent.stat().st_mode & 0o022:
            raise DeployError("UNSAFE_PARENT_DIRECTORY")
        if root_owned and parent.stat().st_uid != 0:
            raise DeployError("PARENT_MUST_BE_ROOT_OWNED")
    return path


def load_config(path):
    config = json.loads(protected_file(path, secret=True, root_owned=True).read_text())
    if config.get("enabled") is not True:
        raise DeployError("DEPLOYMENT_NOT_ACTIVATED")
    if config.get("image_repository") != REPOSITORY:
        raise DeployError("UNEXPECTED_REGISTRY")
    if config.get("migration_policy") not in {"unchanged", "upgrade"}:
        raise DeployError("INVALID_MIGRATION_POLICY")
    protected_file(config["runtime_env"], secret=True)
    if str(config["runtime_env"]).endswith(".pending"):
        raise DeployError("INCOMPLETE_RUNTIME_CONFIGURATION")
    protected_file(config["database_ca"])
    protected_file(config["compose_file"], root_owned=True)
    protected_file(Path(config["docker_config"]) / "config.json", secret=True, root_owned=True)
    if config.get("readiness_url") != "https://api-prismquest.p-e.kr/health/ready":
        raise DeployError("UNEXPECTED_READINESS_URL")
    state = Path(config["state_dir"])
    if str(state) != "/var/lib/prism-deploy":
        raise DeployError("UNEXPECTED_STATE_DIRECTORY")
    state.mkdir(mode=0o700, exist_ok=True)
    if state.is_symlink() or state.stat().st_uid != 0 or state.stat().st_mode & 0o077:
        raise DeployError("UNSAFE_STATE_DIRECTORY")
    return config


def save_state(path, value):
    pending = path.with_suffix(".pending")
    fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as file:
        json.dump(value, file)
        file.write("\n")
        file.flush()
        os.fsync(file.fileno())
    os.replace(pending, path)


@contextmanager
def deployment_lock(state):
    fd = os.open(state / "deploy.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise DeployError("DEPLOYMENT_ALREADY_RUNNING") from exc
        yield


class Docker:
    def __init__(self, config, sequence):
        self.config = config
        self.task_name = f"prism-deploy-task-{sequence}"
        self.env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "HOME": "/root",
            "DOCKER_CONFIG": config["docker_config"],
            "PRISM_ENV_FILE": config["runtime_env"],
            "PRISM_DB_CA_FILE": config["database_ca"],
        }

    def run(self, args, image, timeout=90):
        try:
            result = subprocess.run(
                ["/usr/bin/docker", *args],
                env={**self.env, "PRISM_IMAGE": image},
                cwd="/",
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise DeployError("DOCKER_OPERATION_TIMEOUT") from exc
        if result.returncode:
            raise DeployError("DOCKER_OPERATION_FAILED")
        return result.stdout

    def compose(self, args, image, timeout=90):
        return self.run(
            [
                "compose",
                "--env-file",
                "/dev/null",
                "--project-name",
                "prism",
                "-f",
                self.config["compose_file"],
                *args,
            ],
            image,
            timeout,
        )

    def task(self, args, image, timeout=90):
        try:
            return self.compose(
                ["run", "--rm", "--no-deps", "--name", self.task_name, "api", *args],
                image,
                timeout,
            )
        finally:
            # Remove only this deployment's one-shot task, including after a CLI timeout.
            try:
                self.run(["rm", "-f", self.task_name], image, 20)
            except DeployError:
                pass

    def pull(self, image, revision):
        self.run(["pull", image], image, 300)
        labels = json.loads(
            self.run(["image", "inspect", "--format", "{{json .Config.Labels}}", image], image)
        )
        if (
            not isinstance(labels, dict)
            or labels.get("org.opencontainers.image.revision") != revision
            or labels.get("org.opencontainers.image.source") != SOURCE
        ):
            raise DeployError("IMAGE_PROVENANCE_MISMATCH")

    def preflight(self, image):
        self.compose(["config", "--quiet"], image)
        self.task(["python", "-m", "app.shared.config.preflight", "--image", image], image)

    def schema(self, image):
        value = json.loads(self.task(["python", "-c", SCHEMA_QUERY], image))
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("current"), list)
            or not isinstance(value.get("target"), list)
        ):
            raise DeployError("INVALID_SCHEMA_STATE")
        if len(value["current"]) > 1 or len(value["target"]) != 1:
            raise DeployError("AMBIGUOUS_SCHEMA_HEAD")
        if any(
            not isinstance(head, str) or not re.fullmatch(r"[a-zA-Z0-9_]+", head)
            for head in value["current"] + value["target"]
        ):
            raise DeployError("INVALID_SCHEMA_REVISION")
        return value

    def running_image(self, image):
        ids = self.compose(["ps", "--all", "--quiet", "api"], image).split()
        if not ids:
            return None
        if len(ids) != 1:
            raise DeployError("AMBIGUOUS_SERVICE_STATE")
        current = self.run(["inspect", "--format", "{{.Config.Image}}", ids[0]], image).strip()
        if not re.fullmatch(re.escape(REPOSITORY) + r"@sha256:[0-9a-f]{64}", current):
            raise DeployError("UNMANAGED_EXISTING_IMAGE")
        return current

    def migrate(self, image):
        self.task(["alembic", "upgrade", "head"], image, 300)

    def start(self, image):
        self.compose(["up", "-d", "--no-deps", "--pull", "never", "api"], image, 120)

    def healthy(self, image):
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            try:
                self.compose(
                    [
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "-c",
                        "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready',timeout=3)",
                    ],
                    image,
                    10,
                )
                with urllib.request.urlopen(self.config["readiness_url"], timeout=5) as response:
                    if (
                        response.status == 200
                        and response.url == self.config["readiness_url"]
                        and json.loads(response.read(4096)).get("status") == "ready"
                    ):
                        return
            except (DeployError, OSError, ValueError, AttributeError):
                pass
            time.sleep(3)
        raise DeployError("READINESS_FAILED")


def execute(config, image, revision, sequence, docker):
    identity(image, revision, sequence)
    state = Path(config["state_dir"])
    with deployment_lock(state):
        attempts = state / "attempt.json"
        if attempts.exists():
            previous_attempt = json.loads(attempts.read_text())
            if sequence < previous_attempt["sequence"] or (
                sequence == previous_attempt["sequence"] and image != previous_attempt["image"]
            ):
                raise DeployError("STALE_DEPLOYMENT")
        record = {
            "sequence": sequence,
            "image": image,
            "revision": revision,
            "status": "RUNNING",
            "stage": "prepare",
            "at": datetime.now(UTC).isoformat(),
        }
        save_state(attempts, record)
        previous = None
        before = None
        swapped = False
        try:
            docker.pull(image, revision)
            docker.preflight(image)
            previous = docker.running_image(image)
            before = docker.schema(image)
            if before["current"] != before["target"]:
                if config["migration_policy"] != "upgrade" or not config.get(
                    "backup_restore_verified_at"
                ):
                    raise DeployError("SCHEMA_CHANGE_REQUIRES_BACKUP_READY_CONFIGURATION")
                verified = datetime.fromisoformat(config["backup_restore_verified_at"])
                if verified.tzinfo is None or verified > datetime.now(UTC):
                    raise DeployError("INVALID_BACKUP_VERIFICATION_RECORD")
            record["stage"] = "migration"
            docker.migrate(image)
            after = docker.schema(image)
            if after["current"] != before["target"]:
                raise DeployError("MIGRATION_HEAD_MISMATCH")
            record["stage"] = "rollout"
            swapped = True
            docker.start(image)
            docker.healthy(image)
            record.update(
                status="SUCCESS", stage="complete", schema=after["current"], previous_image=previous
            )
            save_state(state / "current.json", record)
        except Exception:
            record["status"] = "FAILED"
            if swapped and previous and previous != image:
                try:
                    current_schema = docker.schema(image)
                    old_schema = docker.schema(previous)
                    if (
                        current_schema["current"] != before["current"]
                        or old_schema["target"] != before["current"]
                    ):
                        record["rollback"] = "BLOCKED_SCHEMA_CHANGED"
                    else:
                        docker.start(previous)
                        docker.healthy(previous)
                        record["rollback"] = "RESTORED_PREVIOUS_IMAGE"
                except Exception:
                    record["rollback"] = "FAILED_REQUIRES_OPERATOR"
            raise
        finally:
            save_state(attempts, record)
            print(json.dumps(record), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--sequence", required=True, type=int)
    args = parser.parse_args()
    try:
        identity(args.image, args.revision, args.sequence)
        if os.geteuid() != 0:
            raise DeployError("ROOT_REQUIRED")
        config = load_config("/etc/prism/deploy.json")
        execute(config, args.image, args.revision, args.sequence, Docker(config, args.sequence))
        return 0
    except (DeployError, OSError, ValueError, KeyError, TypeError) as exc:
        reason = (
            str(exc) if isinstance(exc, DeployError) else "DEPLOYMENT_CONFIGURATION_OR_STATE_ERROR"
        )
        print(json.dumps({"status": "FAIL", "reason": reason}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
