import logging

logging.basicConfig(
    level=logging.CRITICAL,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),           # log to console
        logging.FileHandler('app.log')     # log to file
    ]
)

MAIN_LOGGER = logging.getLogger("Demo")
