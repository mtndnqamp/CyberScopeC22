import logging
import tempfile
import unittest
from pathlib import Path

from cyberscope.reporting.log import configure_logger


class LoggingTests(unittest.TestCase):
    def test_reconfiguration_closes_previous_file_handler(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.log"
            second_path = Path(directory) / "second.log"
            logger = configure_logger(first_path)
            previous = next(item for item in logger.handlers if isinstance(item, logging.FileHandler))
            configure_logger(second_path)
            self.assertIsNone(previous.stream)
            configure_logger()  # close the final file before TemporaryDirectory cleanup


if __name__ == "__main__":
    unittest.main()
