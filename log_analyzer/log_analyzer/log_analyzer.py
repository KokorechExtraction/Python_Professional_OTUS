# log_format ui_short '$remote_addr  $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import argparse
import gzip
import json
import logging
import os
import re
import sys

from collections.abc import Callable, Iterator
from json import dumps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from statistics import median
from types import TracebackType
from typing import Any

import structlog

config: dict[str, int | str] = {"REPORT_SIZE": 1000, "REPORT_DIR": "./reports", "LOG_DIR": "./log"}

FILE_NAME_PATTERN = re.compile(r"nginx-access-ui.log-(\d+)(\.\S+)?$")
# FILE_NAME_PATTERN = re.compile(r'nginx-access-ui.log-(\d+)(\.gz)?$')
LOG_PATTERN = re.compile(
    r'^\S+\s+\S+\s+\S+\s+\[[^]]*]\s+"([^"]*)"\s+\S+\s+\S+\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+"[^"]*"\s+(\d+\.\d+)'
)
REQUEST_PATTERN = re.compile(r"^\S+\s+(\S+)")


def handle_exception(
    exc_type: type[BaseException], exc_value: BaseException, exc_traceback: TracebackType | None
) -> Any:
    log.error(
        "Oh shit! I'm sorry! This shit was interrupted by leather bag",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def configure_structlog(log_path: str | None, level: str = "info") -> None:
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "error": logging.ERROR,
    }

    log_level = level_map.get(level.lower(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    handler: logging.Handler = (
        RotatingFileHandler(
            filename=os.path.join(log_path + "/log.json"),
            maxBytes=10_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        if log_path
        else logging.StreamHandler(sys.stdout)
    )

    root_logger.addHandler(handler)

    structlog_processors: list[Callable[..., Any]] = [
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ]

    structlog.configure(
        processors=structlog_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def config_parser(default_config: dict[str, int | str]) -> dict[str, int | str] | None:
    parser = argparse.ArgumentParser(description="Скрипт для загрузки конфига из файла")
    parser.add_argument(
        "--config",
        help="Путь к файлу конфигурации",
        default=r"C:\Users\admin\PycharmProjects\Python_Professional_OTUS\log_analyzer\config\config.json",
    )
    args = parser.parse_args()
    config_path = args.config

    if os.path.exists(config_path) and os.path.isfile(config_path):
        with open(config_path, encoding="utf-8") as file:
            new_config = json.load(file)
            config.update(new_config)
            return default_config
    else:
        log.error("Oh shit! I'm sorry! There is no such file")
        return None


def parse_line(line: str) -> dict[str, str] | None:
    pattern_match = LOG_PATTERN.match(line)

    if not pattern_match:
        log.error("Oh shit! I'm sorry! There is no such line", line=line)
        return None

    request = pattern_match.group(1)
    request_match = REQUEST_PATTERN.match(request)
    if not request_match:
        log.error("Oh shit! I'm sorry! There is no such line", request=request)
        return None

    request_time = pattern_match.group(2)

    return {"url": request_match.group(1), "request_time": request_time}


def report_maker(
    source: Iterator[str], parser: Callable[[str], dict[str, str] | None], report_size: int
) -> list[dict[str, int | float | str]]:
    urls: dict[str, list[float]] = {}
    result: list[dict[str, int | float | str]] = []

    count_all: int = 0
    time_all: int | float = 0

    for line in source:
        parsed_line = parser(line)
        if not parsed_line:
            continue

        url = parsed_line["url"]

        times = float(parsed_line["request_time"])

        urls.setdefault(url, []).append(times)

    for url, time in urls.items():
        count: int = len(time)
        time_sum: float = sum(time)
        time_avg: float = time_sum / count
        time_max: float = max(time)
        time_med: float = median(time)
        count_all += count
        time_all += time_sum

        result.append(
            {
                "url": url,
                "count": count,
                "time_sum": round(time_sum, 3),
                "time_avg": round(time_avg, 3),
                "time_max": time_max,
                "time_med": round(time_med, 3),
            }
        )

    for some_url in result:
        if count_all > 0:
            some_url.update({"count_perc": round(((int(some_url["count"]) * 100) / count_all), 3)})
        if time_all > 0:
            some_url.update(
                {"time_perc": round(((float(some_url["time_sum"]) * 100) / time_all), 3)}
            )

    return sorted(result, key=lambda d: d["time_sum"], reverse=True)[:report_size]


def read_lines(path: str | None, encoding: str = "utf-8") -> Iterator[str]:
    if not path:
        log.error("Oh shit! I'm sorry! There is no such path to log file")
        return None
    log.info("Yeah, beach! This script is starting to read some shit!")
    with (
        gzip.open(path, "rt", encoding=encoding)
        if Path(path).suffix == ".gz"
        else open(path, encoding=encoding) as file
    ):
        yield from file


def find_latest_log(path: str) -> str | None:
    log_files = [
        os.path.join(path + file) for file in os.listdir(path) if FILE_NAME_PATTERN.match(file)
    ]
    log_files = [file for file in log_files if os.path.isfile(file)]
    if log_files:
        return max(log_files)
    else:
        log.info("There is no shit you are looking for")
        return None


def write_report(file: str, template: str, data: str) -> None:
    with open(template, encoding="utf-8") as f:
        body = f.read()
    body = body.replace("$table_json", data)
    os.makedirs(os.path.dirname(file), exist_ok=True)
    with open(file, "w", encoding="utf-8") as f:
        f.write(body)


def main() -> None:
    if not config_parser(config):
        sys.exit()

    try:
        log_file = find_latest_log(os.path.join(str(config["LOG_DIR"]) + "/"))
    except FileNotFoundError as e:
        log.error("Oh shit! I'm sorry! There is no such path to log file", e=e)
        sys.exit()
    if not log_file:
        log.error("Oh shit! I'm sorry! There is no file to analyze")
    report = report_maker(read_lines(log_file), parse_line, int(config["REPORT_SIZE"]))

    write_report(
        os.path.join(str(config["REPORT_DIR"]) + "/report.html"),
        "C:/Users/admin/PycharmProjects/Python_Professional_OTUS/log_analyzer/templates/report.html",
        dumps(report),
    )


if __name__ == "__main__":
    configure_structlog(str(config["LOG_DIR"]), level="info")
    log = structlog.get_logger()
    sys.excepthook = handle_exception
    main()
