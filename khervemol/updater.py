"""Automatic updates from the GitHub repository.

KherveMol is run from a source checkout (PyCharm, ``python KherveMol.py``),
so an update is simply the newest commits of the branch you are on. A few
seconds after it starts — and every half hour while it stays open — the
app fetches ``origin`` in the background. If the branch is behind and can
be brought up to date *safely* (nothing edited locally, no commits of your
own, a plain fast-forward) it does so by itself, tells you what changed
(the commit subjects, grouped by their ``feat:`` / ``fix:`` prefix) and
offers to restart into the new version. A checkout with local changes or
its own commits is never touched: you are told an update exists and why
it was not applied.

Help ▸ Check for Updates… does the same on demand, and Help ▸ Update
Automatically turns the background check off. An install that is not a git
checkout (a copy without ``.git``) looks at the newest GitHub *release*
instead and, if it is newer, offers the release page.

The git and version logic is plain functions with no Qt, exercised by the
tests against temporary repositories. Nothing runs during tests or when the
app is started with ``KHERVEMOL_NO_UPDATE=1``.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PyQt5.QtCore import QObject, QProcess, QSettings, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QLabel,
                             QMessageBox, QTextBrowser, QVBoxLayout)

from . import APP_NAME, __version__

REPO = "gkerherve/KherveMol"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
ROOT = Path(__file__).resolve().parent.parent

SETTINGS = ("Kherve", "KherveMol")
KEY_AUTO = "update_auto"              # default on
STARTUP_DELAY_MS = 4000
INTERVAL_MS = 30 * 60 * 1000          # while the app stays open
GIT_TIMEOUT = 40                      # seconds per git command

#: commit prefix -> changelog heading; ``None`` drops the commit
COMMIT_GROUPS = {"feat": "New", "fix": "Fixed", "perf": "Improved",
                 "style": "Improved", "refactor": "Improved",
                 "docs": None, "test": None}
GROUP_ORDER = ("New", "Fixed", "Improved", "Other")


class UpdateError(Exception):
    """An update step that failed; the message says why."""


# ------------------------------------------------------------------ git
def is_git_checkout(root=ROOT) -> bool:
    return (Path(root) / ".git").exists()


def _git(root, *args, timeout=GIT_TIMEOUT) -> str:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    try:
        out = subprocess.run(["git", *args], cwd=str(root), env=env,
                             capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise UpdateError("git is not installed or not on the PATH.")
    except subprocess.TimeoutExpired:
        raise UpdateError(f"git {args[0]} timed out (no network?).")
    if out.returncode != 0:
        detail = (out.stderr or out.stdout).strip().splitlines()
        raise UpdateError(detail[-1] if detail else f"git {args[0]} failed")
    return out.stdout.strip()


@dataclass
class Status:
    """Where a checkout stands against its upstream."""
    branch: str = ""
    upstream: str = ""
    behind: int = 0
    ahead: int = 0
    dirty: bool = False
    local_sha: str = ""
    remote_sha: str = ""
    subjects: list = field(default_factory=list)   # what is new upstream

    @property
    def available(self) -> bool:
        return self.behind > 0

    @property
    def can_fast_forward(self) -> bool:
        """Safe to apply without asking: strictly behind, nothing local."""
        return self.behind > 0 and self.ahead == 0 and not self.dirty

    def why_not(self) -> str:
        """Why an available update was not applied by itself."""
        if self.dirty:
            return ("You have uncommitted changes in this checkout, so it "
                    "was left alone. Commit or stash them, then update.")
        if self.ahead:
            return (f"This branch has {self.ahead} commit(s) that are not on "
                    f"{self.upstream}, so it cannot fast-forward. Merge or "
                    "rebase it yourself.")
        return ""


def default_upstream(root, branch: str) -> str:
    """The remote branch to compare against: the configured upstream, else
    ``origin/<branch>``, else ``origin/master``."""
    try:
        return _git(root, "rev-parse", "--abbrev-ref", f"{branch}@{{u}}")
    except UpdateError:
        pass
    for cand in (f"origin/{branch}", "origin/master"):
        try:
            _git(root, "rev-parse", "--verify", "--quiet", cand)
            return cand
        except UpdateError:
            continue
    raise UpdateError(f"No remote branch to compare '{branch}' with.")


def check(root=ROOT, fetch: bool = True) -> Status:
    """Fetch the remote and describe how far this checkout is behind."""
    if not is_git_checkout(root):
        raise UpdateError("Not a git checkout.")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        raise UpdateError("A detached HEAD is not updated automatically.")
    if fetch:
        _git(root, "fetch", "--quiet", "origin")
    upstream = default_upstream(root, branch)
    behind, ahead = (int(x) for x in _git(
        root, "rev-list", "--left-right", "--count",
        f"{upstream}...HEAD").split())
    dirty = bool(_git(root, "status", "--porcelain",
                      "--untracked-files=no"))
    st = Status(branch=branch, upstream=upstream, behind=behind,
                ahead=ahead, dirty=dirty,
                local_sha=_git(root, "rev-parse", "--short", "HEAD"),
                remote_sha=_git(root, "rev-parse", "--short", upstream))
    if behind:
        st.subjects = _git(root, "log", "--format=%s", "--no-merges",
                           f"HEAD..{upstream}").splitlines()
    return st


def fast_forward(root, status: Status) -> str:
    """Bring the checkout up to date; returns the new short sha. Refuses
    anything but a clean fast-forward."""
    if not status.can_fast_forward:
        raise UpdateError(status.why_not() or "Nothing to update.")
    _git(root, "merge", "--ff-only", "--quiet", status.upstream)
    return _git(root, "rev-parse", "--short", "HEAD")


# --------------------------------------------------------------- changelog
def group_subjects(subjects) -> dict:
    """{heading: [subject, ...]} from commit subjects, by ``feat:`` /
    ``fix:`` … prefix; docs and test commits are left out."""
    groups = {}
    for subject in subjects:
        m = re.match(r"^(\w+)(?:\([^)]*\))?!?:\s*(.+)$", subject)
        if m:
            key = m.group(1).lower()
            heading = COMMIT_GROUPS.get(key, "Other")
            text = m.group(2)
        else:
            heading, text = "Other", subject
        if heading is None:
            continue
        groups.setdefault(heading, []).append(text[:1].upper() + text[1:])
    return groups


def changelog_markdown(subjects) -> str:
    groups = group_subjects(subjects)
    parts = []
    for heading in GROUP_ORDER:
        items = groups.get(heading)
        if items:
            parts.append(f"**{heading}**\n" + "\n".join(f"- {t}"
                                                        for t in items))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- releases
def parse_version(text):
    """(0, 1, N) from ``0.1.N``, ``v0.1.N`` or ``0.1.N+sha``; else None."""
    m = re.match(r"^\D*(\d+)\.(\d+)\.(\d+)", str(text or ""))
    return tuple(int(x) for x in m.groups()) if m else None


def newer_release(latest_tag: str, current: str = __version__) -> bool:
    a, b = parse_version(latest_tag), parse_version(current)
    return a is not None and b is not None and a > b


def fetch_latest_release(timeout=10):
    """(tag, html_url) of the newest GitHub release, or None."""
    req = urllib.request.Request(RELEASES_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception as exc:                          # noqa: BLE001
        raise UpdateError(f"Could not reach GitHub: {exc}")
    tag = data.get("tag_name")
    return (tag, data.get("html_url") or RELEASES_PAGE) if tag else None


# -------------------------------------------------------------- settings
def auto_enabled(settings=None) -> bool:
    value = (settings or QSettings(*SETTINGS)).value(KEY_AUTO, True)
    return value in (True, "true", "True", 1, "1")


def restart_command():
    """The command that starts this same app again."""
    main = sys.modules.get("__main__")
    spec = getattr(main, "__spec__", None)
    if spec is not None and spec.name:
        pkg = spec.name.rsplit(".", 1)[0] if spec.name.endswith(
            ".__main__") else spec.name
        return sys.executable, ["-m", pkg] + sys.argv[1:]
    return sys.executable, list(sys.argv)


# ----------------------------------------------------------------- worker
class CheckWorker(QThread):
    """Fetch (and, when allowed, fast-forward) off the UI thread."""

    finished_check = pyqtSignal(object, object, str)   # Status, new sha, error

    def __init__(self, apply: bool, root=ROOT):
        super().__init__()
        self._apply, self._root = apply, root

    def run(self):
        try:
            if is_git_checkout(self._root):
                st = check(self._root)
                new = None
                if self._apply and st.can_fast_forward:
                    new = fast_forward(self._root, st)
                self.finished_check.emit(st, new, "")
            else:
                self.finished_check.emit(None, None, "")
        except UpdateError as exc:
            self.finished_check.emit(None, None, str(exc))
        except Exception as exc:                       # noqa: BLE001
            self.finished_check.emit(None, None, f"{type(exc).__name__}: {exc}")


class ReleaseWorker(QThread):
    finished_check = pyqtSignal(object, str)           # (tag, url) | None, err

    def run(self):
        try:
            self.finished_check.emit(fetch_latest_release(), "")
        except UpdateError as exc:
            self.finished_check.emit(None, str(exc))


class UpdateDialog(QDialog):
    """What changed, and whether to restart into it."""

    def __init__(self, title, intro, notes_md, restart_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(460, 320)
        box = QVBoxLayout(self)
        label = QLabel(intro)
        label.setWordWrap(True)
        box.addWidget(label)
        if notes_md:
            view = QTextBrowser()
            view.setMarkdown(notes_md)
            box.addWidget(view, 1)
        buttons = QDialogButtonBox()
        self.restart_btn = None
        if restart_text:
            self.restart_btn = buttons.addButton(
                restart_text, QDialogButtonBox.AcceptRole)
        buttons.addButton("Later" if restart_text else "Close",
                          QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        box.addWidget(buttons)


# -------------------------------------------------------------- controller
class Updater(QObject):
    """The Help-menu front end and the background check, owned by a
    MainWindow."""

    def __init__(self, window, root=ROOT):
        super().__init__(window)
        self._window = window
        self._root = root
        self._worker = None
        self._manual = False
        self._timer = None
        self.auto_action = None

    # ---- menu / settings
    def add_menu_actions(self, menu):
        menu.addAction("Check for &Updates…", self.check_now)
        act = menu.addAction("Update &Automatically")
        act.setCheckable(True)
        act.setChecked(auto_enabled())
        act.setToolTip("Look for new commits on GitHub a few seconds after "
                       "start and every half hour, and apply a safe "
                       "fast-forward by itself")
        act.toggled.connect(self.set_auto)
        self.auto_action = act

    def set_auto(self, on: bool):
        QSettings(*SETTINGS).setValue(KEY_AUTO, bool(on))

    def schedule(self, delay_ms: int = STARTUP_DELAY_MS):
        """Start the background checks (called once by the app, never from
        tests)."""
        if os.environ.get("KHERVEMOL_NO_UPDATE"):
            return
        QTimer.singleShot(delay_ms, lambda: self._start(manual=False))
        self._timer = QTimer(self)
        self._timer.timeout.connect(lambda: self._start(manual=False))
        self._timer.start(INTERVAL_MS)

    def check_now(self):
        self._start(manual=True)

    # ---- running a check
    def _status(self, text, ms=8000):
        try:
            self._window.statusBar().showMessage(text, ms)
        except (AttributeError, RuntimeError):
            pass

    def _start(self, manual: bool):
        if self._worker is not None:
            if manual:
                self._status("Already checking for updates…")
            return
        if not manual and not auto_enabled():
            return
        self._manual = manual
        if manual:
            self._status("Checking for updates…", 0)
        if is_git_checkout(self._root):
            worker = CheckWorker(apply=auto_enabled() or False,
                                 root=self._root)
            worker.finished_check.connect(self._git_done)
        else:
            worker = ReleaseWorker()
            worker.finished_check.connect(self._release_done)
        worker.finished.connect(self._cleanup)
        self._worker = worker
        worker.start()

    def _cleanup(self):
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None

    # ---- results (git checkout)
    def _git_done(self, st, new_sha, error):
        manual = self._manual
        if manual:
            self._status("")
        if error:
            if manual:
                QMessageBox.warning(self._window, "Check for Updates",
                                    f"Could not check for updates.\n\n{error}")
            return
        if st is None or not st.available:
            if manual:
                QMessageBox.information(
                    self._window, "Check for Updates",
                    f"{APP_NAME} {__version__} is up to date"
                    + (f" ({st.upstream})." if st else "."))
            return
        notes = changelog_markdown(st.subjects)
        if new_sha:
            self._updated(st, new_sha, notes)
        elif st.can_fast_forward:
            # automatic updating is off: ask (a manual check, or a queued one)
            self._offer(st, notes)
        elif manual:
            dlg = UpdateDialog("Update available",
                               f"{len(st.subjects)} new commit(s) on "
                               f"{st.upstream}, but {st.why_not()}",
                               notes, "", self._window)
            dlg.exec_()
        else:
            self._status(f"An update is available on {st.upstream} — "
                         f"{st.why_not()}", 15000)

    def _updated(self, st, new_sha, notes):
        self._status(f"{APP_NAME} updated to {new_sha} — restart to use it.",
                     0)
        dlg = UpdateDialog(
            "KherveMol updated",
            f"KherveMol was brought up to date ({st.local_sha} → {new_sha}, "
            f"{st.behind} new commit(s)). Restart to use the new version.",
            notes, "Restart now", self._window)
        if dlg.exec_() == QDialog.Accepted:
            self.restart()

    def _offer(self, st, notes):
        dlg = UpdateDialog(
            "Update available",
            f"{st.behind} new commit(s) are available on {st.upstream}. "
            "Update now?", notes, "Update and restart", self._window)
        if dlg.exec_() != QDialog.Accepted:
            return
        try:
            new = fast_forward(self._root, st)
        except UpdateError as exc:
            QMessageBox.warning(self._window, "Update failed", str(exc))
            return
        self._status(f"Updated to {new}.", 0)
        self.restart()

    # ---- results (no git: releases)
    def _release_done(self, found, error):
        manual = self._manual
        if manual:
            self._status("")
        if error:
            if manual:
                QMessageBox.warning(self._window, "Check for Updates",
                                    f"Could not check for updates.\n\n{error}")
            return
        if found and newer_release(found[0]):
            dlg = UpdateDialog(
                "Update available",
                f"{APP_NAME} {found[0]} is available (you have "
                f"{__version__}).", "", "Open the release page",
                self._window)
            if dlg.exec_() == QDialog.Accepted:
                from PyQt5.QtCore import QUrl
                from PyQt5.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(found[1]))
        elif manual:
            QMessageBox.information(
                self._window, "Check for Updates",
                f"{APP_NAME} {__version__} is up to date.")

    # ---- restart
    def restart(self):
        """Start a fresh copy of the app and quit this one."""
        program, args = restart_command()
        if QProcess.startDetached(program, args, str(self._root)):
            QApplication.quit()
        else:
            QMessageBox.information(
                self._window, "Restart",
                "Please close and start KherveMol again to use the update.")
