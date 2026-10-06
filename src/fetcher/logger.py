import logging
import logging.handlers

from fetcher.repository.settings import settings

db_logger = logging.getLogger("db")

db_logger.setLevel(settings.DB_LOG_LEVEL)
db_logger.propagate = False
db_logger.addHandler(logging.StreamHandler())
db_logger.handlers[0].setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
db_logger.handlers[0].setLevel(settings.DB_LOG_LEVEL)

db_logger.addHandler(
    logging.handlers.RotatingFileHandler(
        "db.log",
        maxBytes=1024 * 1024 * 10,  # 10 MB
        backupCount=10,
    )
)
db_logger.handlers[1].setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
db_logger.handlers[1].setLevel(settings.DB_LOG_LEVEL)


main_logger = logging.getLogger("main")
main_logger.setLevel(settings.MAIN_LOG_LEVEL)
main_logger.propagate = False
main_logger.addHandler(logging.StreamHandler())
main_logger.handlers[0].setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
main_logger.handlers[0].setLevel(settings.MAIN_LOG_LEVEL)
main_logger.addHandler(
    logging.handlers.RotatingFileHandler(
        "main.log",
        maxBytes=1024 * 1024 * 10,  # 10 MB
        backupCount=10,
    )
)
main_logger.handlers[1].setFormatter(
    logging.Formatter(
        fmt="[%(asctime)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
main_logger.handlers[1].setLevel(settings.MAIN_LOG_LEVEL)
