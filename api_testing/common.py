import logging
import os
import sys
from typing import Literal

config: dict[str, str] = {"LOG_PATHs": "mylog.log",}

def configure_logging(config_file: dict[str, str], level_name: Literal["info", "error", "exception"] = "info"):

    levels = {"info": logging.INFO,
              "error": logging.ERROR,
              "exception": logging.ERROR,
              }

    logger_prime = logging.getLogger()

    level = levels.get(level_name, logging.INFO)
    handler: logging.Handler = logging.FileHandler(os.path.join(config_file["LOG_PATH"]), encoding="utf-8") if config_file.get("LOG_PATH") else logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname).1s %(name)s: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )
    handler.setFormatter(formatter)
    logger_prime.setLevel(level)
    logger_prime.addHandler(handler)


configure_logging(config)