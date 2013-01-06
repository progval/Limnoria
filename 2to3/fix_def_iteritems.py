"""Fixer for iteritems -> items methods."""
# Author: Valentin Lorentz

# Code modified from fix_nonzero by Collin Winter

from lib2to3 import fixer_base
from lib2to3.fixer_util import Name, syms

class FixDefIteritems(fixer_base.BaseFix):
    BM_compatible = True
    PATTERN = """
    classdef< 'class' any+ ':'
              suite< any*
                     funcdef< 'def' name='iteritems'
                              parameters< '(' NAME ')' > any+ >
                     any* > >
    """

    def transform(self, node, results):
        name = results["name"]
        new = Name("items", prefix=name.prefix)
        name.replace(new)
