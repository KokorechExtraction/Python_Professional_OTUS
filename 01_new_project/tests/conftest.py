import gzip

import pytest
import structlog


@pytest.fixture(scope="session")
def logger():
    return structlog.get_logger()


@pytest.fixture
def sample_line():
    return (
        "1.2.3.4 - 10.0.0.1 [10/Oct/2025:13:55:36 +0300] "
        '"GET /api/v2/user HTTP/1.1" 200 123 "-" "curl/7.88.1" "-" "req-123" "rb-456" 0.123\n'
    )


@pytest.fixture
def sample_line_other_url():
    return (
        "5.6.7.8 - 10.0.0.2 [10/Oct/2025:13:55:40 +0300] "
        '"POST /api/v2/user HTTP/1.1" 200 256 "-" "python-requests/2.32" "-" "req-124" "rb-457" 0.377\n'
    )


@pytest.fixture
def plain_log_file(tmp_path, sample_line, sample_line_other_url):
    p = tmp_path / "nginx-access-ui.log-20250102"
    p.write_text(sample_line + sample_line_other_url, encoding="utf-8")
    return str(p)


@pytest.fixture
def gz_log_file(tmp_path, sample_line):
    p = tmp_path / "nginx-access-ui.log-20250101.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        f.write(sample_line)
    return str(p)


@pytest.fixture
def template_file(tmp_path):
    t = tmp_path / "templates" / "report.html"
    t.parent.mkdir(parents=True, exist_ok=True)
    t.write_text("<html><body>$table_json</body></html>", encoding="utf-8")
    return str(t)
