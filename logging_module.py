import os
import logging
import traceback

logging.basicConfig(filename=os.path.join(os.path.dirname(__file__), 'app.log'), level=logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)

def log(level, message):
    if level == 'info':
        logging.info(message)
    elif level == 'warning':
        logging.warning(message)
    elif level == 'error':
        logging.error(message)
    elif level == 'exception':
        logging.exception(message)
    else:
        pass
        logging.debug(message)
