import io
import logging

from src.utils.logger import get_logger


class TestGetLogger:
    def test_returns_logger_instance(self):
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)

    def test_same_name_returns_same_instance(self):
        l1 = get_logger("same")
        l2 = get_logger("same")
        assert l1 is l2

    def test_different_names_different_instances(self):
        l1 = get_logger("unique1")
        l2 = get_logger("unique2")
        assert l1 is not l2

    def test_default_level_is_info(self):
        logger = get_logger("level_test")
        assert logger.level == logging.INFO

    def test_output_format(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

        logger = get_logger("format_test")
        logger.addHandler(handler)
        logger.info("hello")

        output = stream.getvalue()
        assert "INFO" in output
        assert "hello" in output
