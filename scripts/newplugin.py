#!/usr/bin/env python

import os
import sys
import shutil

if len(sys.argv) < 2:
    print 'Usage: %s <plugin name>' % sys.argv[0]
    sys.exit(-1)

shutil.copy('plugins/template.py', 'plugins/%s.py' % sys.argv[1])
# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
