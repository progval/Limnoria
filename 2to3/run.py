#! /usr/bin/python2.7
import sys
from lib2to3.main import main

import fix_def_iteritems, fix_def_itervalues, fix_def_iterkeys, fix_reload

# Hacks
sys.modules['lib2to3.fixes.fix_def_iteritems'] = fix_def_iteritems
sys.modules['lib2to3.fixes.fix_def_itervalues'] = fix_def_itervalues
sys.modules['lib2to3.fixes.fix_def_iterkeys'] = fix_def_iterkeys
sys.modules['lib2to3.fixes.fix_reload'] = fix_reload

sys.exit(main("lib2to3.fixes"))
