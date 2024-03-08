import logging
import sys
import unittest

from script import foobar

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class TestStub(unittest.TestCase):

    def test_stub(self):
        logger.debug('Test stub passed')
        assert True

    def test_whatever(self):
        assert foobar(123) == 'deadbeef'

    def test_failure(self):
        with self.assertRaises(TypeError):
            None / 1  # pylint: disable=W0104


if __name__ == '__main__':
    unittest.main()
