#!/usr/bin/env python
# Author: Ruediger Birkner (Networked Systems Group at ETH Zurich)

import logging


def get_logger(name, loglevel):
    # LOGGING
    if loglevel == "INFO":
        log_level = logging.INFO
    elif loglevel == "DEBUG":
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # add handler
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    if len(logger.handlers) == 0:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
