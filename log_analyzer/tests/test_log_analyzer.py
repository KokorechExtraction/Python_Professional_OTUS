import json
import sys

import pytest


import log_analyzer.log_analyzer.log_analyzer as m


def test_parse_line(sample_line, logger, monkeypatch):
    monkeypatch.setattr(m, "log", logger, raising=False)

    parsed = m.parse_line(sample_line)
    assert parsed is not None
    assert parsed["url"] == "/api/v2/user"
    assert isinstance(parsed["request_time"], str)
    assert parsed["request_time"] == pytest.approx(0.123, rel=0, abs=1e-3)


def test_parse_line_bad_format(logger, monkeypatch):
    monkeypatch.setattr(m, "log", logger, raising=False)
    bad = "this line does not match your regex\n"
    assert m.parse_line(bad) is None


def test_report_maker(sample_line, sample_line_other_url, logger, monkeypatch):
    monkeypatch.setattr(m, "log", logger, raising=False)

    data = [sample_line, sample_line_other_url, sample_line]
    report = m.report_maker(data, m.parse_line, report_size=100)

    urls = {row["url"]: row for row in report}
    assert "/api/v2/user" in urls
    row = urls["/api/v2/user"]

    assert row["count"] == 3
    assert row["time_sum"] == pytest.approx(0.123 + 0.377 + 0.123, abs=1e-3)
    assert row["time_avg"] == pytest.approx((0.123 + 0.377 + 0.123) / 3, abs=1e-3)
    assert row["time_max"] == pytest.approx(0.377, abs=1e-3)

    assert row["time_med"] == pytest.approx(0.123, abs=1e-3)

    assert "count_perc" in row and "time_perc" in row
    assert 0 <= row["count_perc"] <= 100
    assert 0 <= row["time_perc"] <= 100


def test_read_lines_plain_file(plain_log_file, logger, monkeypatch):
    monkeypatch.setattr(m, "log", logger, raising=False)
    lines = list(m.read_lines(plain_log_file))
    assert len(lines) == 2
    assert lines[0].endswith("0.123\n")


def test_read_lines_gz_file(gz_log_file, logger, monkeypatch):
    monkeypatch.setattr(m, "log", logger, raising=False)
    lines = list(m.read_lines(gz_log_file))
    assert len(lines) == 1
    assert lines[0].endswith("0.123\n")


def test_find_latest_log(tmp_path, monkeypatch):
    d = tmp_path
    (d / "nginx-access-ui.log-20250101").write_text("", encoding="utf-8")
    (d / "nginx-access-ui.log-20250102.gz").write_bytes(b"")
    (d / "some-other-file.txt").write_text("x", encoding="utf-8")

    latest = m.find_latest_log(str(d) + "/")
    assert latest is not None

    assert latest.endswith("nginx-access-ui.log-20250102.gz")


def test_write_report(tmp_path, template_file):
    out = tmp_path / "reports" / "report.html"
    payload = json.dumps([{"url": "/x", "count": 1, "time_sum": 0.1}])

    m.write_report(str(out), template_file, payload)

    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "$table_json" not in text
    assert payload in text


def test_config_parser_merges(tmp_path, monkeypatch, logger):
    cfg = tmp_path / "config.json"
    cfg.write_text(
        json.dumps(
            {
                "REPORT_SIZE": 42,
                "REPORT_DIR": str(tmp_path / "rep"),
                "LOG_DIR": str(tmp_path / "logs"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["prog", "--config", str(cfg)])

    #
    monkeypatch.setattr(m, "log", logger, raising=False)

    default = dict(m.config)
    result = m.config_parser(default)

    assert result == default
    assert m.config["REPORT_SIZE"] == 42
    assert m.config["REPORT_DIR"] == str(tmp_path / "rep")
    assert m.config["LOG_DIR"] == str(tmp_path / "logs")


def test_config_parser_missing_file(monkeypatch, logger):
    monkeypatch.setattr(sys, "argv", ["prog", "--config", "/definitely/missing.json"])
    monkeypatch.setattr(m, "log", logger, raising=False)

    assert m.config_parser(dict(m.config)) is None
