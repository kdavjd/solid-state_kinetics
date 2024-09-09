import logging


def configure_logger(log_level: int = logging.INFO) -> logging.Logger:
    logger_ = logging.getLogger(__name__)
    logger_.setLevel(log_level)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s : %(message)s", datefmt="%H:%M:%S")
    handler.setFormatter(formatter)
    logger_.addHandler(handler)
    return logger_


logger = configure_logger()
