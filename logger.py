# coding: utf-8
import logging
from datetime import datetime

datestring = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
logging.basicConfig(filename='scrapper__{}.log'.format(datestring), level=logging.INFO)

def custom_print(content: str, level: str = "info"):
    if level == "info":
        logging.info(content)
    elif level == "error":
        logging.error(content)
    elif level == "warning":
        logging.warning(content)
    elif level == "debug":
        logging.debug(content)
    else:
        logging.info(content)

    print(content)