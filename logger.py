import logging
import json

class JsonFormatter(logging.Formatter):
    """
    Formats log records as JSON strings.
    """
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name
        }
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, 'details'):
            log_record.update(record.details)

        return json.dumps(log_record)

def get_logger(name: str):
    """
    Configures and returns a logger with a JSON formatter.
    """
    logger = logging.getLogger(name)
    if not logger.handlers: # Avoid adding handlers multiple times
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = JsonFormatter()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
