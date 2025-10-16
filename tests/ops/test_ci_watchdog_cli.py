from pathlib import Path

from scripts.github import ci_watchdog

from tests.github.test_ci_watchdog import freeze_utc_now, load_fixture, mock_session


def test_cli_generates_artifacts(monkeypatch, tmp_path):
    mapping = {
        'https://api.github.com/repos/example/repo/pulls?{"direction": "desc", "per_page": "50", "sort": "updated", "state": "open"}': load_fixture(
            "pulls.json"
        ),
        "https://api.github.com/repos/example/repo/commits/abc123/check-runs": load_fixture(
            "check_runs_abc123.json"
        ),
    }

    freeze_utc_now(
        monkeypatch,
        ci_watchdog._dt.datetime(
            2024, 5, 1, 14, 0, tzinfo=ci_watchdog._dt.timezone.utc
        ),
    )
    mock_session(monkeypatch, mapping)

    output_report = tmp_path / "report.md"
    metrics_path = tmp_path / "metrics.json"
    status_path = tmp_path / "status.json"
    monkeypatch.setenv("WATCHDOG_STATUS_OUTPUT", str(status_path))

    ci_watchdog.main(
        [
            "--repo",
            "example/repo",
            "--max-age-hours",
            "72",
            "--render",
            "--output",
            str(output_report),
            "--metrics",
            str(metrics_path),
        ]
    )

    assert output_report.read_text(encoding="utf-8") == (
        Path(__file__).parent.parent / "golden" / "watchdog" / "report.md"
    ).read_text(encoding="utf-8")
    metrics = metrics_path.read_text(encoding="utf-8")
    assert "failures_scanned" in metrics
    status = status_path.read_text(encoding="utf-8")
    assert '"number": 42' in status
