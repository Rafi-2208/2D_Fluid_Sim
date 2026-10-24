import logging
import threading
import time
from pathlib import Path


APP_LOGGER = logging.getLogger("fluid_sim")
APP_LOGGER.setLevel(logging.DEBUG)
APP_LOGGER.propagate = False

_NATIVE_LEVELS = {
    1: logging.INFO,
    2: logging.WARNING,
    3: logging.ERROR,
}
_native_log_lock = threading.Lock()
_native_log_state = {}


class _ComponentFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "component"):
            record.component = "Python"
        return True


APP_LOGGER.addFilter(_ComponentFilter())


def configure_logging():
    if APP_LOGGER.handlers:
        return APP_LOGGER

    log_path = Path.cwd() / "simulation.log"

    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(component)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    APP_LOGGER.addHandler(handler)
    APP_LOGGER.info("Logging started; file=%s", log_path)
    return APP_LOGGER


def log_native(level, component, message):
    log_level = _NATIVE_LEVELS.get(level, logging.WARNING)
    native_component = component.decode("utf-8", errors="replace") if component else "Native"
    native_message = message.decode("utf-8", errors="replace") if message else ""
    key = (native_component, log_level, native_message)
    now = time.monotonic()
    with _native_log_lock:
        last_logged, suppressed_count = _native_log_state.get(key, (0.0, 0))
        if last_logged and now - last_logged < 10.0:
            _native_log_state[key] = (last_logged, suppressed_count + 1)
            return
        if suppressed_count:
            APP_LOGGER.log(
                log_level,
                "%s (repeated %d times in %.1f seconds)",
                native_message,
                suppressed_count,
                now - last_logged,
                extra={"component": native_component},
            )
        else:
            APP_LOGGER.log(log_level, native_message, extra={"component": native_component})
        _native_log_state[key] = (now, 0)
