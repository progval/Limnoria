# Based on fix_intern.py. Original copyright:
# Copyright 2006 Georg Brandl.
# Licensed to PSF under a Contributor Agreement.

"""Fixer for intern().

intern(s) -> sys.intern(s)"""

# Local imports
from lib2to3 import pytree
from lib2to3 import fixer_base
from lib2to3.fixer_util import Name, Attr, touch_import


class FixReload(fixer_base.BaseFix):
    BM_compatible = True
    order = "pre"

    PATTERN = """
    power< 'reload'
           after=any*
    >
    """

    def transform(self, node, results):
        touch_import('imp', 'reload', node)
        return node
