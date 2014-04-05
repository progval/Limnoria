#!/usr/bin/env python

###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import os
import sys
import tempfile
import subprocess

debug = '--debug' in sys.argv

path = os.path.dirname(__file__)
if debug:
    print('DEBUG: Changing dir from %r to %r' % (os.getcwd(), path))
if path:
    os.chdir(path)

version = None
try:
    proc = subprocess.Popen('git show HEAD --format=%ci', shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    version = proc.stdout.readline()
    if sys.version_info[0] >= 3:
        version = version.decode()
    version = version \
            .strip() \
            .split(' ')[0] \
            .replace('-', '.')
except:
    pass
if not version:
    from time import gmtime, strftime
    version = 'installed on ' + strftime("%Y-%m-%dT%H-%M-%S", gmtime())
try:
    os.unlink(os.path.join('src', 'version.py'))
except OSError: # Does not exist
    pass
fd = open(os.path.join('src', 'version.py'), 'a')
fd.write("version = '0.83.4.1+limnoria %s'\n" % version)
fd.close()

if sys.version_info < (2, 6, 0):
    sys.stderr.write("Supybot requires Python 2.6 or newer.")
    sys.stderr.write(os.linesep)
    sys.exit(-1)


import textwrap

clean = False
while '--clean' in sys.argv:
    clean = True
    sys.argv.remove('--clean')

import glob
import shutil
import os


plugins = [s for s in os.listdir('plugins') if
           os.path.exists(os.path.join('plugins', s, 'plugin.py'))]

def normalizeWhitespace(s):
    return ' '.join(s.split())

try:
    from distutils.core import setup
    from distutils.sysconfig import get_python_lib
except ImportError as e:
    s = normalizeWhitespace("""Supybot requires the distutils package to
    install. This package is normally included with Python, but for some
    unfathomable reason, many distributions to take it out of standard Python
    and put it in another package, usually caled 'python-dev' or python-devel'
    or something similar. This is one of the dumbest things a distribution can
    do, because it means that developers cannot rely on *STANDARD* Python
    modules to be present on systems of that distribution. Complain to your
    distribution, and loudly. If you how much of our time we've wasted telling
    people to install what should be included by default with Python you'd
    understand why we're unhappy about this.  Anyway, to reiterate, install the
    development package for Python that your distribution supplies.""")
    sys.stderr.write(os.linesep*2)
    sys.stderr.write(textwrap.fill(s))
    sys.stderr.write(os.linesep*2)
    sys.exit(-1)
try:
    from distutils.command.build_py import build_py_2to3
    class build_py(build_py_2to3):
        def run_2to3(self, files, options=None):
            from distutils import log
            from lib2to3.refactor import RefactoringTool, get_fixers_from_package
            if not files:
                return

            # Make this class local, to delay import of 2to3
            from lib2to3.refactor import RefactoringTool, get_fixers_from_package
            class DistutilsRefactoringTool(RefactoringTool):
                def refactor(self, files, *args, **kwargs):
                    self._total_files = len(files)
                    self._refactored_files = 0
                    super(DistutilsRefactoringTool, self).refactor(files,
                            *args, **kwargs)
                    del self._total_files
                    del self._refactored_files
                def refactor_file(self, filename, *args, **kwargs):
                    if self._total_files//10 != 0 and \
                            self._refactored_files % (self._total_files//10) == 0:
                        print('Refactoring files: %i%% (%i on %i).' %
                                (self._refactored_files/(self._total_files//10)*10,
                                 self._refactored_files, self._total_files))
                    self._refactored_files += 1
                    return super(DistutilsRefactoringTool, self).refactor_file(
                            filename, *args, **kwargs)
                def log_error(self, msg, *args, **kw):
                    log.error(msg, *args)

                def log_message(self, msg, *args):
                    log.info(msg, *args)

                def log_debug(self, msg, *args):
                    log.debug(msg, *args)

            fixer_names = ['fix_basestring',
                    'fix_dict',
                    'fix_imports',
                    'fix_long',
                    'fix_metaclass', 'fix_methodattrs',
                    'fix_numliterals',
                    'fix_types',
                    'fix_unicode', 'fix_urllib', 'fix_xrange']
            fixers = list(map(lambda x:'lib2to3.fixes.'+x, fixer_names))
            fixers += get_fixers_from_package('2to3')
            r = DistutilsRefactoringTool(fixers, options=options)
            r.refactor(files, write=True)
except ImportError:
    # 2.x
    from distutils.command.build_py import build_py


if clean:
    previousInstall = os.path.join(get_python_lib(), 'supybot')
    if os.path.exists(previousInstall):
        try:
            print('Removing current installation.')
            shutil.rmtree(previousInstall)
        except Exception as e:
            print('Couldn\'t remove former installation: %s' % e)
            sys.exit(-1)

packages = ['supybot',
            'supybot.locales',
            'supybot.utils',
            'supybot.drivers',
            'supybot.plugins',] + \
            ['supybot.plugins.'+s for s in plugins] + \
            [
             'supybot.plugins.Dict.local',
             'supybot.plugins.Math.local',
            ]

package_dir = {'supybot': 'src',
               'supybot.utils': 'src/utils',
               'supybot.locales': 'locales',
               'supybot.plugins': 'plugins',
               'supybot.drivers': 'src/drivers',
               'supybot.plugins.Dict.local': 'plugins/Dict/local',
               'supybot.plugins.Math.local': 'plugins/Math/local',
              }

package_data = {'supybot.locales': [s for s in os.listdir('locales/')]}

for plugin in plugins:
    package_dir['supybot.plugins.' + plugin] = 'plugins/' + plugin
    locales_path = 'plugins/' + plugin + '/locales/'
    locales_name = 'supybot.plugins.'+plugin
    if os.path.exists(locales_path):
        package_data.update({locales_name: ['locales/'+s for s in os.listdir(locales_path)]})

setup(
    # Metadata
    name='limnoria',
    provides=['supybot'],
    version=version,
    author='Valentin Lorentz',
    url='https://github.com/ProgVal/Limnoria',
    author_email='progval+limnoria@progval.net',
    download_url='http://builds.progval.net/limnoria/',
    description='A modified version of Supybot (an IRC bot and framework)',
    platforms=['linux', 'linux2', 'win32', 'cygwin', 'darwin'],
    long_description=normalizeWhitespace("""A robust, full-featured Python IRC
    bot with a clean and flexible plugin API.  Equipped with a complete ACL
    system for specifying user permissions with as much as per-command
    granularity.  Batteries are included in the form of numerous plugins
    already written."""),
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Natural Language :: English',
        'Natural Language :: Finnish',
        'Natural Language :: French',
        'Natural Language :: Hungarian',
        'Natural Language :: Italian',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        ],
    cmdclass = {'build_py': build_py},

    # Installation data
    packages=packages,

    package_dir=package_dir,

    package_data=package_data,

    scripts=['scripts/supybot',
             'scripts/supybot-test',
             'scripts/supybot-botchk',
             'scripts/supybot-wizard',
             'scripts/supybot-adduser',
             'scripts/supybot-plugin-doc',
             'scripts/supybot-plugin-create',
             ],
    data_files=[('share/man/man1', ['docs/man/supybot.1']),
                ('share/man/man1', ['docs/man/supybot-test.1']),
                ('share/man/man1', ['docs/man/supybot-botchk.1']),
                ('share/man/man1', ['docs/man/supybot-wizard.1']),
                ('share/man/man1', ['docs/man/supybot-adduser.1']),
                ('share/man/man1', ['docs/man/supybot-plugin-doc.1']),
                ('share/man/man1', ['docs/man/supybot-plugin-create.1']),
        ]
    )


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
