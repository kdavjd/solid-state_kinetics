import logging
import sys
import unittest

from src.core.logger_config import configure_logger

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TestLogger(unittest.TestCase):
    def test_logger_configuration(self):
        log = configure_logger()
        assert isinstance(log, logging.Logger)
        assert log.level == logging.INFO


if __name__ == "__main__":
    unittest.main()
