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

found_gnupg_lib = False
found_gnupg_bin = False
try:
    import gnupg
except ImportError:
    # As we do not want Supybot to depend on GnuPG, we will use it only if
    # it is available. Otherwise, we just don't allow user auth through GPG.
    log.debug('Cannot import gnupg, disabling GPG support.')
    gnupg = None
try:
    if gnupg:
        gnupg.GPG(gnupghome=None)
        found_gnupg_lib = found_gnupg_bin = True
except TypeError:
    # This is the 'gnupg' library, not 'python-gnupg'.
    gnupg = None
    log.error('Cannot use GPG. gnupg (a Python package) is installed, '
              'but python-gnupg (an other Python package) should be '
              'installed instead.')
except OSError:
    gnupg = None
    found_gnupg_lib = True
    log.error('Cannot use GPG. python-gnupg is installed but cannot '
              'find the gnupg executable.')


available = (gnupg is not None)

def loadKeyring():
    if not available:
        return
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
