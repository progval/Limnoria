###
# Copyright (c) 2012, Valentin Lorentz
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
import os.path
import subprocess
import sys

import supybot.log as log
import supybot.conf as conf
import supybot.world as world

try:
    import gnupg
except ImportError:
    # As we do not want Supybot to depend on GnuPG, we will use it only if
    # it is available. Otherwise, we just don't allow user auth through GPG.
    log.debug('Cannot import gnupg, using fallback.')
    gnupg = None
try:
    if gnupg:
        gnupg.GPG(gnupghome=None)
except TypeError:
    # This is the 'gnupg' library, not 'python-gnupg'.
    gnupg = None


# Check for different versions of GPG as the behaviour differs
# slightly.  Use shutil.which in Python 3.3 and above, otherwise use
# distutils.spawn.find_executable.  If the binary is installed
# somewhereweird and not in the $PATH then a bot owner may need to
# hard-code gpgbin to the full path to their GPG installation.  Tries
# to use GPG 1.4 primarily, except on Windows because gpg4win is the
# most popular version and it uses GPG 2.0.
#
# An alternative method would utilise os.path.walk to traverse the
# entire directory structure to look for the GPG binary.  This,
# however, would result in a significant delay in loading times
# (depending on the size of the filesystem) and, ideally should be
# avoided where possible.  It can be added later if there is demand.
svi = sys.version_info

if float("{0}.{1}".format(svi[0], svi[1])) >= 3.3:
    import shutil
    which = shutil.which
else:
    import distutils.spawn
    which = distutils.spawn.find_executable

if sys.platform == "win32":
    gpg1bin = which("gpg.exe")
    gpg2bin = which("gpg2.exe")
else:
    gpg1bin = which("gpg")
    gpg2bin = which("gpg2")

if os.path.exists(gpg1bin):
    gpgbin = gpg1bin
elif os.path.exists(gpg2bin):
    gpgbin = gpg2bin
else:
    try:
        if sys.platform == "win32":
            gpgbin = "gpg2.exe"
        else:
            gpgbin = "gpg"
    except:
        gpgbin = None


# It's not enough to just check for python-gnupg, it needs a backend:
available = (gnupg is not None and gpgbin is not None)

# Once the GPG binary has been located, check the version and set
# relevant variables accordingly.
gpgcheck0 = subprocess.Popen([gpgbin, "--version"],
                             stdout=subprocess.PIPE).communicate()[0]
gpgcheck = gpgcheck0.decode("utf-8").split()[2]

if gpgcheck.startswith("1.4"):
    pubring = "pubring.gpg"
    secring = "secring.gpg"
    agent = "False"
elif gpgcheck.startswith("2.0"):
    pubring = "pubring.gpg"
    secring = "secring.gpg"
    agent = "True"
elif gpgcheck.startswith("2.1"):
    pubbox = "pubring.kbx"
    pubring = []
    secring = []
    agent = "True"


def fallback(default_return=None):
    """Decorator.
    Does nothing if gnupg is loaded. Otherwise, returns the supplied
    default value."""
    def decorator(f):
        if available:
            def newf(*args, **kwargs):
                return f(*args, **kwargs)
        else:
            def newf(*args, **kwargs):
                return default_return
        return newf
    return decorator


@fallback()
def loadKeyring():
    global keyring
    path = os.path.abspath(conf.supybot.directories.data.dirize('GPGkeyring'))
    if not os.path.isdir(path):
        log.info('Creating directory %s' % path)
        os.mkdir(path, 0700)
    assert os.path.isdir(path)
    keyring = gnupg.GPG(gnupghome=path, use_agent=agent, keyring=pubring,
                        secret_keyring=secring, gpgbinary=gpgbin)
loadKeyring()

# Reload the keyring if path changed
conf.supybot.directories.data.addCallback(loadKeyring)
