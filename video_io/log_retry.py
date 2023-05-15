import logging

from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LogRetry(Retry):
    def increment(self, *args, method=None, url=None, **kwargs):
        new_retry = super().increment(*args, **kwargs)
        logger.warning(
            "Incremented Retry for (method=%s) (url='%s'), %r", method, url, new_retry
        )
        return new_retry
