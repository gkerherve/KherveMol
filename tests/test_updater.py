"""Auto-update: git status, safe fast-forward, changelog, restart command.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

import subprocess

import pytest

from khervemol import updater


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:"
                        "/usr/local/bin:/opt/homebrew/bin", "HOME": str(cwd)})


@pytest.fixture
def repos(tmp_path):
    """(upstream work tree, a clone of it) with one commit each."""
    bare = tmp_path / "remote.git"
    _git(tmp_path, "init", "--bare", "-b", "master", str(bare))
    work = tmp_path / "work"
    _git(tmp_path, "clone", str(bare), str(work))
    (work / "a.txt").write_text("one\n")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "feat: first")
    _git(work, "push", "origin", "HEAD:master")
    mine = tmp_path / "mine"
    _git(tmp_path, "clone", str(bare), str(mine))
    return work, mine


def _push(work, text, message):
    (work / "a.txt").write_text(text)
    _git(work, "commit", "-am", message)
    _git(work, "push", "origin", "HEAD:master")


def test_up_to_date_checkout_has_nothing_to_do(repos):
    _work, mine = repos
    st = updater.check(mine)
    assert not st.available and st.behind == 0 and not st.dirty


def test_behind_checkout_is_fast_forwarded(repos):
    work, mine = repos
    _push(work, "two\n", "feat: add two")
    _push(work, "three\n", "fix: repair three")
    st = updater.check(mine)
    assert st.behind == 2 and st.can_fast_forward
    assert st.subjects == ["fix: repair three", "feat: add two"]
    new = updater.fast_forward(mine, st)
    assert (mine / "a.txt").read_text() == "three\n"
    assert new == st.remote_sha
    assert not updater.check(mine).available


def test_local_changes_are_never_touched(repos):
    work, mine = repos
    _push(work, "two\n", "feat: two")
    (mine / "a.txt").write_text("my edit\n")
    st = updater.check(mine)
    assert st.available and st.dirty and not st.can_fast_forward
    assert "uncommitted" in st.why_not()
    with pytest.raises(updater.UpdateError):
        updater.fast_forward(mine, st)
    assert (mine / "a.txt").read_text() == "my edit\n"


def test_own_commits_block_the_update(repos):
    work, mine = repos
    _push(work, "two\n", "feat: two")
    (mine / "b.txt").write_text("mine\n")
    _git(mine, "add", "-A")
    _git(mine, "commit", "-m", "wip")
    st = updater.check(mine)
    assert st.behind == 1 and st.ahead == 1 and not st.can_fast_forward
    assert "commit" in st.why_not()


def test_not_a_git_checkout_and_no_network(tmp_path):
    assert not updater.is_git_checkout(tmp_path)
    with pytest.raises(updater.UpdateError):
        updater.check(tmp_path)


def test_changelog_groups_by_prefix():
    md = updater.changelog_markdown([
        "feat: reaction film", "fix: clipped buttons", "docs: readme",
        "style: smaller icons", "polish the thing", "test: more"])
    assert md.index("**New**") < md.index("**Fixed**") < md.index(
        "**Improved**") < md.index("**Other**")
    assert "Reaction film" in md and "Readme" not in md
    assert "Smaller icons" in md and "Polish the thing" in md


def test_version_comparison():
    assert updater.parse_version("v0.1.42") == (0, 1, 42)
    assert updater.parse_version("0.1.7+abc123") == (0, 1, 7)
    assert updater.newer_release("v0.1.99", "0.1.5+x")
    assert not updater.newer_release("v0.1.5", "0.1.5+x")
    assert not updater.newer_release("nonsense", "0.1.5")


def test_restart_command_reruns_the_same_entry():
    import sys
    program, args = updater.restart_command()
    assert program == sys.executable
    # started with -m: restart with -m again, never the package's __main__.py
    # as a bare script (its relative imports would break)
    assert args[0] == "-m" or args[0] == sys.argv[0]


def test_menu_and_setting(qapp):
    from PyQt5.QtCore import QSettings
    from khervemol.mainwindow import MainWindow
    w = MainWindow()
    assert w.updater.auto_action.isCheckable()
    w.updater.set_auto(False)
    assert not updater.auto_enabled()
    w.updater.set_auto(True)
    assert updater.auto_enabled()
    QSettings(*updater.SETTINGS).remove(updater.KEY_AUTO)


def test_updating_flow_on_a_real_checkout(repos, qapp, monkeypatch):
    """The worker fetches and fast-forwards; the controller reports it."""
    work, mine = repos
    _push(work, "two\n", "feat: two")
    got = []
    worker = updater.CheckWorker(apply=True, root=mine)
    worker.finished_check.connect(lambda st, new, err: got.append((st, new,
                                                                  err)))
    worker.run()                              # synchronously, no thread
    st, new, err = got[0]
    assert err == "" and st.behind == 1 and new == st.remote_sha
    assert (mine / "a.txt").read_text() == "two\n"
