# coding: utf-8
import inspect
import logging
import traceback
from datetime import datetime
from logging.config import dictConfig

datestring = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")


def init_logging():
    dictConfig({
        'version': 1,
        'formatters': {
            'default': {
                'format': '[%(asctime)s] %(levelname)s  %(message)s',
            },
            'libs': {
                'format': 'LIB ----> [%(asctime)s] %(levelname)s  %(message)s (%(funcName)s:%(lineno)s)',
            }
        },
        'handlers': {
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'maxBytes': 1024 * 1024 * 10,  # 10 MB
                'backupCount': 4,  # mantém os 4 arquivos de log anteriores
                'filename': 'scrapper__{}.log'.format(datestring),
                'formatter': 'default'
            },
            'terminal': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'default'
            },
            'root': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stdout',
                'formatter': 'libs'
            },
        },
        'loggers': {
            'scrapper': {
                'level': "DEBUG",
                'handlers': ['file', 'terminal'],
                'propagate': False
            },
            'root': {
                'level': "DEBUG",
                'handlers': ['root']
            }
        },
    })


def logs():
    # Quando debug/info/error são chamados, eles entram pra stack. Até esta função entra. Então preciso ir direto para a
    # 3ª posição da stack (que começa do 0), que é a função que chamou debug/info/error
    frames_to_skip = 2
    logger = logging.getLogger('scrapper')
    frame, filename, line_number, function_name, lines, index = inspect.getouterframes(
        inspect.currentframe())[frames_to_skip]

    libs_offset = 12
    nesting_level = len(traceback.extract_stack()) - libs_offset

    line = lines[0]
    indentation_level = line.find(line.lstrip())

    if nesting_level < 0:
        nesting_level = len(traceback.extract_stack())

    return logger, nesting_level, indentation_level, filename, line_number


def debug(msg: any):
    logger, nesting_level, indentation_level, filename, line_number = logs()
    logger.debug('{}{} {} ({}:{})'.format(
        '.' * nesting_level,
        "»" * (indentation_level // 4),
        str(msg),
        filename,
        line_number
    ))


def info(msg: str):
    logger, nesting_level, indentation_level, filename, line_number = logs()
    logger.info('{}{} {} ({}:{})'.format(
        '.' * nesting_level,
        "»" * (indentation_level // 4),
        msg,
        filename,
        line_number
    ))


def error(msg: str):
    logger, nesting_level, indentation_level, filename, line_number = logs()
    logger.error('{}{} {} ({}:{})'.format(
        '.' * nesting_level,
        "»" * (indentation_level // 4),
        msg,
        filename,
        line_number
    ))
