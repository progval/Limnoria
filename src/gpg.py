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

available = (gnupg is not None)

# Check for different versions of GPG as the behaviour differs
# slightly.  Assuming gpg executable is in the path, may expand later
# to check gor both gpg and gpg2.  Try to find GPG 1.4 first as it
# will generally work more consistently on servers and is ideal for a
# bot.  There may be unexpected results from setting "keyring" as a
# global, but initial tests indicate it works - this cannot be
# guaranteed, however.
for path in os.environ["PATH"].split(":"):
    if os.path.exists(path + "/" + "gpg"):
        gpgbin = path + "/" + "gpg"
    elif os.path.exists(path + "/" + "gpg2"):
        gpgbin = path + "/" + "gpg2"
    elif os.path.exists(path + "/" + "gpg.exe"):
        gpgbin = path + "/" + "gpg.exe"
    elif os.path.exists(path + "/" + "gpg2.exe"):
        gpgbin = path + "/" + "gpg2.exe"
    else:
        gpgbin = "gpg"  # if it reaches this point, expect failures.

gpgcheck0 = subprocess.Popen([gpgbin, "--version"],
                             stdout=subprocess.PIPE).communicate()[0]
gpgcheck1 = gpgcheck0.decode("utf-8")
gpgcheck = gpgcheck1.split()[2]

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
    pubring = []  # GPG 2.1.x now hands the keyrings over to gpg-agent
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
