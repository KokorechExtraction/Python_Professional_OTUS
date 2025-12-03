import logging
import os
import sys
from typing import Literal


config: dict[str, str] = {"LOG_PATH": "mylog.log",}




def configure_logging(logger_name: str, config_file: dict[str, str], level_name: Literal["info", "error", "exception"] = "info") -> logging.Logger:

    levels = {"info": logging.INFO,
              "error": logging.ERROR,
              "exception": logging.ERROR,
              }

    logger = logging.getLogger(logger_name)

    if logger.handlers:
        return logger


    level = levels.get(level_name, logging.INFO)



    handler: logging.Handler = logging.FileHandler(os.path.join(config_file["LOG_PATH"]), encoding="utf-8") if config_file.get("LOG_PATH") else logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter(
        fmt='[%(asctime)s] %(levelname).1s %(name)s: %(message)s',
        datefmt='%Y.%m.%d %H:%M:%S',
    )
    handler.setFormatter(formatter)


    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

