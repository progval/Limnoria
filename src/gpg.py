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

import supybot.log as log
import supybot.conf as conf

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
except OSError:
    gnupg = None
    log.error('Cannot use GPG. python-gnupg is installed but cannot '
              'find the gnupg executable.')


available = (gnupg is not None)

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
        os.mkdir(path, 0o700)
    assert os.path.isdir(path)
    keyring = gnupg.GPG(gnupghome=path)
loadKeyring()

# Reload the keyring if path changed
conf.supybot.directories.data.addCallback(loadKeyring)
