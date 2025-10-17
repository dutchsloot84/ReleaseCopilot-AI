"""Tests for the coverage PR comment command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest import CaptureFixture

from releasecopilot.cli import __main__ as cli_main


@pytest.fixture()
def coverage_report(tmp_path: Path) -> Path:
    report = tmp_path / "coverage.json"
    payload = {
        'totals': {'percent_covered': 88.2, 'covered_lines': 88, 'num_statements': 100},
        'files': {
            'src/releasecopilot/utils/coverage.py': {'summary': {'covered_lines': 44, 'num_statements': 50}},
            'src/releasecopilot/cli/__main__.py': {'summary': {'covered_lines': 44, 'num_statements': 50}},
        },
    }
    report.write_text(json.dumps(payload), encoding='utf-8')
    return report


def test_pr_comment_dry_run(monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str], coverage_report: Path) -> None:
    captured: dict[str, float] = {}

    def _fake_build(coverage: float, *, minimum: float = 70.0, paths: tuple[str, ...] | None = None):
        captured["coverage"] = coverage
        captured["minimum"] = minimum
        captured["paths"] = paths
        return "comment-body"

    monkeypatch.setattr(cli_main, "build_comment", _fake_build)

    exit_code = cli_main.main(
        [
            'pr-comment',
            'coverage',
            '--file',
            str(coverage_report),
            '--dry-run',
            '--minimum',
            '70',
            '--paths',
            'src/releasecopilot/utils/coverage.py',
        ]
    )

    assert exit_code == 0
    assert captured['coverage'] == pytest.approx(88.0)
    assert captured['minimum'] == 70.0
    assert captured['paths'] == ('src/releasecopilot/utils/coverage.py',)
    assert capsys.readouterr().out.strip() == "comment-body"


def test_pr_comment_posts_comment(monkeypatch: pytest.MonkeyPatch, coverage_report: Path) -> None:
    posted: dict[str, object] = {}

    def _fake_sync(token: str, repo: str, pr_number: int, body: str) -> None:
        posted.update(token=token, repo=repo, pr_number=pr_number, body=body)

    def _fake_build(coverage: float, *, minimum: float = 70.0, paths: tuple[str, ...] | None = None) -> str:
        return f"coverage={coverage:.1f} minimum={minimum:.1f}"

    monkeypatch.setattr(cli_main, "_sync_comment", _fake_sync)
    monkeypatch.setattr(cli_main, "build_comment", _fake_build)

    exit_code = cli_main.main(
        [
            'pr-comment',
            'coverage',
            '--file',
            str(coverage_report),
            '--token',
            'token-123',
            '--repo',
            'octo/repo',
            '--pr-number',
            '42',
            '--paths',
            'src/releasecopilot/utils/coverage.py',
            'src/releasecopilot/cli/__main__.py',
        ]
    )

    assert exit_code == 0
    assert posted["token"] == "token-123"
    assert posted["repo"] == "octo/repo"
    assert posted["pr_number"] == 42
    assert str(posted['body']).startswith('coverage=88.0 minimum=70.0')


def test_pr_comment_infers_pr_from_event(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, coverage_report: Path) -> None:
    posted: dict[str, object] = {}

    def _fake_sync(token: str, repo: str, pr_number: int, body: str) -> None:
        posted.update(token=token, repo=repo, pr_number=pr_number, body=body)

    def _fake_build(coverage: float, *, minimum: float = 70.0, paths: tuple[str, ...] | None = None) -> str:
        return "body"

    monkeypatch.setattr(cli_main, "_sync_comment", _fake_sync)
    monkeypatch.setattr(cli_main, "build_comment", _fake_build)

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"number": 99}), encoding="utf-8")

    exit_code = cli_main.main(
        [
            'pr-comment',
            'coverage',
            '--file',
            str(coverage_report),
            '--token',
            'ghs_xxx',
            '--repo',
            'octo/repo',
            '--event-path',
            str(event_path),
            '--paths',
            'src/releasecopilot/utils/coverage.py',
        ]
    )

    assert exit_code == 0
    assert posted["pr_number"] == 99


def test_sync_comment_handles_existing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict | None]] = []

    def _fake_request(method: str, url: str, token: str, data: dict | None = None):
        calls.append((method, url, data))
        if method == 'GET':
            return {'items': [{'body': cli_main.COMMENT_MARKER, 'url': 'https://api.example.com/comment/1'}]}
        return {}

    monkeypatch.setattr(cli_main, '_github_request', _fake_request)

    cli_main._sync_comment('token', 'octo/repo', 7, 'body')

    assert calls[1][0] == 'PATCH'
    assert calls[1][1] == 'https://api.example.com/comment/1'
    assert calls[1][2] == {'body': 'body'}


def test_sync_comment_creates_new_comment(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict | None]] = []

    def _fake_request(method: str, url: str, token: str, data: dict | None = None):
        calls.append((method, url, data))
        if method == 'GET':
            return {'items': []}
        return {}

    monkeypatch.setattr(cli_main, '_github_request', _fake_request)

    cli_main._sync_comment('token', 'octo/repo', 8, 'body')

    assert calls[1][0] == 'POST'
    assert calls[1][2] == {'body': 'body'}


def test_parse_event_and_extract_pr_number(tmp_path: Path) -> None:
    payload = {'number': 321}
    event_path = tmp_path / 'event.json'
    event_path.write_text(json.dumps(payload), encoding='utf-8')

    event = cli_main._parse_event(event_path)
    assert cli_main._extract_pr_number(event) == 321
