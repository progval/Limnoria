#!/usr/bin/env python
import os
import sys
import shutil
from glob import glob
try:
    from lib2to3.main import main
except ImportError:
    print('Error: you need the 2to3 tool to run this script.')
os.chdir(os.path.join(os.path.dirname(__file__), '..'))
try:
    os.unlink('src/version.py')
except OSError:
    pass
try:
    shutil.rmtree('py3k')
except OSError:
    pass
os.mkdir('py3k')
for dirname in ('locales', 'docs', 'plugins', 'src', 'test', 'scripts'):
    shutil.copytree(dirname, os.path.join('py3k', dirname))
for filename in ('setup.py',):
    shutil.copyfile(filename, os.path.join('py3k', filename))
os.chdir('py3k')

files = ['run.py', 'src', 'plugins', 'test', 'setup.py'] + glob('scripts/*')
args = ['-wn']
fixers = []
for fix in ['all', 'def_iteritems', 'def_itervalues', 'def_iterkeys', 'reload', 'import']:
    fixers += ['-f', fix]
sys.argv = files + args + fixers + sys.argv
sys.argc = len(sys.argv)

from . import fix_def_iteritems, fix_def_itervalues, fix_def_iterkeys, fix_reload, fix_import

# Hacks
sys.modules['lib2to3.fixes.fix_def_iteritems'] = fix_def_iteritems
sys.modules['lib2to3.fixes.fix_def_itervalues'] = fix_def_itervalues
sys.modules['lib2to3.fixes.fix_def_iterkeys'] = fix_def_iterkeys
sys.modules['lib2to3.fixes.fix_reload'] = fix_reload
sys.modules['lib2to3.fixes.fix_import'] = fix_import

sys.exit(main("lib2to3.fixes"))
