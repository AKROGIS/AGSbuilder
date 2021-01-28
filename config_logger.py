# -*- coding: utf-8 -*-
"""
Configuration parameters for the default logging system.

This is a logger configuration dictionary.
It is defined in https://docs.python.org/2/library/logging.config.html
"""

from __future__ import absolute_import, division, print_function, unicode_literals


config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "brief": {
            "format": "%(name)-12s: %(levelname)-8s %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s %(name)-12s %(levelname)-8s %(message)s",
            "datefmt": "%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        # command line arguments (--verbose and --debug will change the level of *first* handler to INFO and DEBUG)
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "brief",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": "publisher.log",
        },
        "email": {
            "class": "buffering_smtp_handler.BufferingSMTPHandler",  # Bundle 100 messages into a single email
            "level": "ERROR",
            "formatter": "detailed",
            "mailhost": "mailer.itc.nps.gov",
            "fromaddr": "regan_sarwas@nps.gov",
            "toaddrs": ["regan_sarwas@nps.gov"],
            "subject": "Errors running the ArcGIS Service Builder/Publisher",
        },
    },
    "root": {
        "level": "NOTSET",
        "handlers": ["console", "file"],  # , 'email']  # only send emails in production
    },
}
