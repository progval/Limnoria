#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

import sys

if sys.version_info < (2, 3, 0):
    sys.stderr.write("Supybot requires Python 2.3 or newer.\n")
    sys.exit(-1)

import glob
import shutil
import os.path

from distutils.core import setup
from distutils.sysconfig import get_python_lib

srcFiles = glob.glob(os.path.join('src', '*.py'))
otherFiles = glob.glob(os.path.join('others', '*.py'))
pluginFiles = glob.glob(os.path.join('plugins', '*.py'))

## previousInstall = os.path.join(get_python_lib(), 'supybot')
## if os.path.exists(previousInstall):
##     try:
##         shutil.rmtree(previousInstall)
##     except Exception, e:
##         print 'Couldn\'t remove former installation: %s' % e
##         print 'Remove by hand and then run this script.'
##         sys.exit(-1)

setup(
    # Metadata
    name='supybot',
    version='0.77.2',
    url='http://supybot.sf.net/',
    author='Jeremy Fincher',
    author_email='jemfinch@users.sf.net',
    #description='A highly robust and full-featured IRC library and bot.',
    description='A flexible and extensible Python IRC bot and framework.',
    long_description="""A full-featured Python IRC bot with a clean and
    flexible plugin API.  Equipped with a complete ACL system for specifying
    user permissions with as much as per-command granularity.  Batteries are
    included in the form of numerous plugins already written.""",
    download_url='http://www.sf.net/project/showfiles.php?group_id=58965',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
    ],
    
    # Installation data
    packages=['supybot',
              'supybot.src',
              'supybot.others',
              'supybot.plugins',
              'supybot.others.IMDb',],
    package_dir={'supybot': os.curdir,
                 'supybot.src': 'src',
                 'supybot.others': 'others',
                 'supybot.plugins': 'plugins',
                 'supybot.others.IMDb': os.path.join('others', 'IMDb'),},
    scripts=['scripts/supybot',
             'scripts/supybot-wizard',
             'scripts/supybot-adduser',
             'scripts/supybot-newplugin']
    )


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
