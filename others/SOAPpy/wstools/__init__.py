#! /usr/bin/env python
"""WSDL parsing services package for Web Services for Python."""

ident = "$Id$"

import WSDLTools
import XMLname
from logging import getLogger as _getLogger
import logging.config as _config

LOGGING = 'logging.txt'
DEBUG = True

#
# If LOGGING configuration file is not found, turn off logging
# and use _noLogger class because logging module's performance
# is terrible.
#

try:
    _config.fileConfig(LOGGING)
except:
    DEBUG = False


class Base:
    def __init__(self, module=__name__):
        self.logger = _noLogger()
        if DEBUG is True:
            self.logger = _getLogger('%s-%s(%x)' %(module, self.__class__, id(self)))

class _noLogger:
    def __init__(self, *args): pass
    def warning(self, *args): pass
    def debug(self, *args): pass
    def error(self, *args): pass
