"""Download a checksum-verified official Gitleaks binary and scan git (no Python deps)."""

import argparse
import hashlib
import platform
import subprocess
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.30.1"
IMAGE = "ghcr.io/gitleaks/gitleaks@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f"
ROOT = Path(__file__).resolve().parents[1]


def main():
    """功能：使用固定版本 Gitleaks 扫描暂存区或 Git 历史，强制脱敏输出。

    输入：命令行 --staged/--docker；隐式使用当前仓库、网络或本机 Docker。
    输出：通过 SystemExit 返回扫描退出码；原生模式缓存并校验工具，失败不视为扫描通过。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--docker", action="store_true", help="Use pinned official container image")
    args = parser.parse_args()
    if args.docker:
        command = [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "--mount",
            f"type=bind,src={ROOT},dst=/repo,readonly",
            IMAGE,
            "git",
            "/repo",
            "--no-banner",
            "--redact",
            "--verbose",
        ]
        if args.staged:
            command.append("--staged")
        raise SystemExit(subprocess.run(command, cwd=ROOT).returncode)
    system = platform.system().lower()
    arch = {"amd64": "x64", "x86_64": "x64", "aarch64": "arm64", "arm64": "arm64"}.get(
        platform.machine().lower()
    )
    if system not in ("windows", "linux", "darwin") or arch is None:
        raise SystemExit("Unsupported platform; install Gitleaks manually")
    extension = "zip" if system == "windows" else "tar.gz"
    name = f"gitleaks_{VERSION}_{system}_{arch}.{extension}"
    base = f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}/"
    tools = ROOT / "runtime" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    # Verify even cached binaries against freshly retrieved checksums by re-extracting the archive.
    checksums = (
        urllib.request.urlopen(base + f"gitleaks_{VERSION}_checksums.txt", timeout=60)
        .read()
        .decode()
    )
    expected = next(
        (
            line.split()[0]
            for line in checksums.splitlines()
            if line.split()[-1].lstrip("*") == name
        ),
        None,
    )
    if expected is None:
        raise SystemExit("Official release checksum not found")
    archive = tools / name
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        with urllib.request.urlopen(base + name, timeout=60) as response:
            archive.write_bytes(response.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
        raise SystemExit("Gitleaks archive checksum mismatch")
    binary = "gitleaks.exe" if system == "windows" else "gitleaks"
    if extension == "zip":
        with zipfile.ZipFile(archive) as bundle:
            data = bundle.read(binary)
    else:
        with tarfile.open(archive) as bundle:
            data = bundle.extractfile(binary).read()
    target = tools / binary
    target.write_bytes(data)
    target.chmod(0o700)
    command = [str(target), "git", "--no-banner", "--redact", "--verbose"]
    if args.staged:
        command.append("--staged")
    raise SystemExit(subprocess.run(command, cwd=ROOT).returncode)


if __name__ == "__main__":
    try:
        main()
    except (urllib.error.URLError, OSError):
        raise SystemExit(
            "Scanner download failed; check network or run with --docker. Scan NOT completed."
        ) from None
