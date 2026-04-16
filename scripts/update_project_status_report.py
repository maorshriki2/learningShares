"""Update PROJECT_STATUS_REPORT_HE.md programmatically.

Usage (from repo root):
    python scripts/update_project_status_report.py
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class GitInfo:
    branch: str
    origin_url: str
    recent_commits: list[tuple[str, str]]  # (YYYY-MM-DD, subject)


def _run_git(repo_root: Path, args: list[str]) -> str:
    out = subprocess.check_output(
        ["git", *args],
        cwd=str(repo_root),
        stderr=subprocess.STDOUT,
        text=True,
    )
    return out.strip()


def _detect_git_info(repo_root: Path, commits_n: int = 10) -> GitInfo:
    branch = _run_git(repo_root, ["branch", "--show-current"])
    origin_url = _run_git(repo_root, ["remote", "get-url", "origin"])
    raw = _run_git(
        repo_root,
        ["log", f"-n{commits_n}", "--date=short", "--pretty=format:%ad|%s"],
    )

    recent_commits: list[tuple[str, str]] = []
    if raw:
        for line in raw.splitlines():
            if "|" not in line:
                continue
            d, subj = line.split("|", 1)
            recent_commits.append((d.strip(), subj.strip()))

    return GitInfo(branch=branch, origin_url=origin_url, recent_commits=recent_commits)


def _repo_slug_from_origin(origin_url: str) -> str:
    # Supports:
    # - https://github.com/org/repo.git
    # - git@github.com:org/repo.git
    url = origin_url.strip()
    m = re.search(r"github\.com[:/](?P<slug>[^/]+/[^/.]+)", url)
    if not m:
        return url
    return m.group("slug")


def _update_report_text(text: str, git: GitInfo, today: date) -> str:
    lines = text.splitlines(keepends=False)

    # Update date line
    date_idx = next((i for i, ln in enumerate(lines) if ln.startswith("תאריך:")), None)
    if date_idx is not None:
        lines[date_idx] = f"תאריך: {today.isoformat()} (עודכן אוטומטית)  "

    # Update source/branch line (best-effort)
    repo_slug = _repo_slug_from_origin(git.origin_url)
    source_prefix = "מקור קוד:"
    source_idx = next((i for i, ln in enumerate(lines) if ln.startswith(source_prefix)), None)
    if source_idx is not None:
        lines[source_idx] = f"מקור קוד: GitHub — `{repo_slug}` (ענף `{git.branch}`)"

    # Replace "תיקונים ושיפורים אחרונים" section content with recent commits
    start_idx = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("## תיקונים ושיפורים אחרונים"):
            start_idx = i
            break

    if start_idx is not None:
        end_idx = None
        for j in range(start_idx + 1, len(lines)):
            if lines[j].startswith("## "):
                end_idx = j
                break
        if end_idx is None:
            end_idx = len(lines)

        section_header = lines[start_idx]
        new_section: list[str] = [section_header, ""]

        if git.recent_commits:
            for d, subj in git.recent_commits:
                new_section.append(f"- {d} — {subj}")
        else:
            new_section.append("- (לא נמצאו קומיטים להצגה)")

        new_section.append("")  # keep blank line before next heading
        lines = lines[:start_idx] + new_section + lines[end_idx:]

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report_path = repo_root / "PROJECT_STATUS_REPORT_HE.md"
    if not report_path.exists():
        raise FileNotFoundError(str(report_path))

    git = _detect_git_info(repo_root=repo_root, commits_n=12)
    updated = _update_report_text(
        report_path.read_text(encoding="utf-8"),
        git=git,
        today=date.today(),
    )
    report_path.write_text(updated, encoding="utf-8")
    print(f"Updated: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

