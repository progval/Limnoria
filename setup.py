#!/usr/bin/env python3

###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
# Copyright (c) 2021, Ian Wienand
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
import time
import textwrap
import warnings
import subprocess

def normalizeWhitespace(s):
    return ' '.join(s.split())

try:
    from setuptools import setup
except ImportError:
    s = normalizeWhitespace("""Limnoria requires the setuptools package to
    install. This package is pretty standard, and often installed alongside
    Python, but it is missing on your system.
    Try installing it with your package manager, it is usually called
    'python3-setuptools'; or with '%s -m pip install setuptools'.
    If that does not work, try installing python3-pip
    instead, either with your package manager or by following these
    instructions: https://pip.pypa.io/en/stable/installation/ (replace
    'python' with 'python3' in all the commands)"""
    % sys.executable)
    sys.stderr.write(os.linesep*2)
    sys.stderr.write(textwrap.fill(s))
    sys.stderr.write(os.linesep*2)
    sys.exit(-1)

warnings.filterwarnings('always', category=DeprecationWarning)

debug = '--debug' in sys.argv

path = os.path.dirname(__file__)
if debug:
    print('DEBUG: Changing dir from %r to %r' % (os.getcwd(), path))
if path:
    os.chdir(path)

VERSION_FILE = os.path.join('src', 'version.py')
version = None
try:
    if 'SOURCE_DATE_EPOCH' in os.environ:
        date = int(os.environ['SOURCE_DATE_EPOCH'])
    else:
        proc = subprocess.Popen('git show HEAD --format=%ct', shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        date = proc.stdout.readline()
        date = date.decode()
        date = int(date.strip())
    version = ".".join(str(i).zfill(2) for i in
            time.strptime(time.asctime(time.gmtime(date)))[:3])
except:
    if os.path.isfile(VERSION_FILE):
        sys.path.insert(0, '') # Missing when installing from an sdist created
                               # by recent setuptools versions?!
        try:
            from src.version import version
        finally:
            sys.path.pop(0)
    else:
        version = 'installed on ' + time.strftime("%Y-%m-%dT%H-%M-%S", time.gmtime())
try:
    os.unlink(VERSION_FILE)
except OSError: # Does not exist
    pass
if version:
    fd = open(os.path.join('src', 'version.py'), 'a')
    fd.write("version = '%s'\n" % version)
    fd.write('try: # For import from setup.py\n')
    fd.write('    import supybot.utils.python\n')
    fd.write('    supybot.utils.python._debug_software_version = version\n')
    fd.write('except ImportError:\n')
    fd.write('    pass\n')
    fd.close()

if sys.version_info < (3, 6, 0):
    sys.stderr.write("Limnoria requires Python 3.6 or newer.")
    sys.stderr.write(os.linesep)
    sys.exit(-1)

plugins = [s for s in os.listdir('plugins') if
           os.path.exists(os.path.join('plugins', s, 'plugin.py'))]

packages = ['supybot',
            'supybot.locales',
            'supybot.utils',
            'supybot.drivers',
            'supybot.plugins',
            'supybot.scripts',
            ] + \
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
    plugin_name = 'supybot.plugins.' + plugin
    package_dir[plugin_name] = 'plugins/' + plugin
    pot_path = 'plugins/' + plugin + 'messages.pot'
    locales_path = 'plugins/' + plugin + '/locales/'

    files = []

    if os.path.exists(pot_path):
        files.append('messages.pot')

    if os.path.exists(locales_path):
        files.extend(['locales/'+s for s in os.listdir(locales_path)])

    if files:
        package_data.update({plugin_name: files})

scripts = [
    '',
    '-test',
    '-botchk',
    '-wizard',
    '-adduser',
    '-reset-password',
    '-plugin-doc',
    '-plugin-create',
]

setup(
    # Metadata
    name='limnoria',
    provides=['supybot'],
    version=version,
    author='Valentin Lorentz',
    url='https://limnoria.net/',
    author_email='progval+limnoria@progval.net',
    download_url='https://pypi.python.org/pypi/limnoria',
    description=(
        'A multipurpose Python IRC bot, designed for flexibility and '
        'robustness , while being easy to install, set up, and maintain.'
    ),
    platforms=['linux', 'linux2', 'win32', 'cygwin', 'darwin'],
    long_description=normalizeWhitespace("""A robust, full-featured Python IRC
    bot with a clean and flexible plugin API.  Equipped with a complete ACL
    system for specifying user permissions with as much as per-command
    granularity.  Batteries are included in the form of numerous plugins
    already written."""),
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Natural Language :: Finnish',
        'Natural Language :: French',
        'Natural Language :: Hungarian',
        'Natural Language :: Italian',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],

    # Installation data
    packages=packages,

    package_dir=package_dir,

    package_data=package_data,

    entry_points={
        'console_scripts': [
            '%s%s = supybot.scripts.limnoria%s:main'
            % (prefix, name, name.replace('-', '_'))
            for name in scripts
            for prefix in ('supybot', 'limnoria')
        ]
    },

    data_files=[
        ('share/man/man1', [
            'man/%s%s.1' % (prefix, name)
            for name in scripts
            for prefix in ('supybot', 'limnoria')
        ]),
    ],
)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
