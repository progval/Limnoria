###
# Copyright (c) 2015, Valentin Lorentz
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

import re
import sys
import time
import uuid
import functools

import supybot.gpg as gpg
import supybot.conf as conf
import supybot.utils as utils
import supybot.ircdb as ircdb
from supybot.commands import *
import supybot.utils.minisix as minisix
import supybot.plugins as plugins
import supybot.commands as commands
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
if minisix.PY3:
    import http.client as http_client
else:
    import httplib as http_client
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('GPG')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

def check_gpg_available(f):
    if gpg.available:
        return f
    else:
        if not gpg.found_gnupg_lib:
            def newf(self, irc, *args):
                irc.error(_('gnupg features are not available because '
                    'the python-gnupg library is not installed.'))
        elif not gpg.found_gnupg_bin:
            def newf(self, irc, *args):
                irc.error(_('gnupg features are not available because '
                    'the gnupg executable is not installed.'))
        else:
            # This case should never happen.
            def newf(self, irc, *args):
                irc.error(_('gnupg features are not available.'))
        newf.__doc__ = f.__doc__
        newf.__name__ = f.__name__
        return newf

if hasattr(http_client, '_MAXHEADERS'):
    safe_getUrl = utils.web.getUrl
else:
    def safe_getUrl(url):
        try:
            return commands.process(utils.web.getUrl, url,
                    timeout=10, heap_size=10*1024*1024,
                    pn='GPG')
        except (commands.ProcessTimeoutError, MemoryError):
            raise utils.web.Error(_('Page is too big or the server took '
                    'too much time to answer the request.'))

class GPG(callbacks.Plugin):
    """Provides authentication based on GPG keys."""
    class key(callbacks.Commands):
        @check_gpg_available
        def add(self, irc, msg, args, user, keyid, keyserver):
            """<key id> <key server>

            Add a GPG key to your account."""
            if keyid in user.gpgkeys:
                irc.error(_('This key is already associated with your '
                    'account.'))
                return
            result = gpg.keyring.recv_keys(keyserver, keyid)
            reply = format(_('%n imported, %i unchanged, %i not imported.'),
                    (result.imported, _('key')),
                    result.unchanged,
                    result.not_imported,
                    [x['fingerprint'] for x in result.results])
            if result.imported == 1:
                user.gpgkeys.append(keyid)
                irc.reply(reply)
            else:
                irc.error(reply)
        add = wrap(add, ['user',
                         ('somethingWithoutSpaces',
                             _('You must give a valid key id')),
                         ('somethingWithoutSpaces',
                             _('You must give a valid key server'))])

        @check_gpg_available
        def remove(self, irc, msg, args, user, fingerprint):
            """<fingerprint>

            Remove a GPG key from your account."""
            try:
                keyids = [x['keyid'] for x in gpg.keyring.list_keys()
                        if x['fingerprint'] == fingerprint]
                if len(keyids) == 0:
                    raise ValueError
                for keyid in keyids:
                    try:
                        user.gpgkeys.remove(keyid)
                    except ValueError:
                        user.gpgkeys.remove('0x' + keyid)
                gpg.keyring.delete_keys(fingerprint)
                irc.replySuccess()
            except ValueError:
                irc.error(_('GPG key not associated with your account.'))
        remove = wrap(remove, ['user', 'somethingWithoutSpaces'])

        @check_gpg_available
        def list(self, irc, msg, args, user):
            """takes no arguments

            List your GPG keys."""
            keyids = user.gpgkeys
            if len(keyids) == 0:
                irc.reply(_('No key is associated with your account.'))
            else:
                irc.reply(format('%L', keyids))
        list = wrap(list, ['user'])

    class signing(callbacks.Commands):
        def __init__(self, *args):
            super(GPG.signing, self).__init__(*args)
            self._tokens = {}

        def _expire_tokens(self):
            now = time.time()
            self._tokens = dict(filter(lambda x_y: x_y[1][1]>now,
                self._tokens.items()))

        @check_gpg_available
        def gettoken(self, irc, msg, args):
            """takes no arguments

            Send you a token that you'll have to sign with your key."""
            self._expire_tokens()
            token = '{%s}' % str(uuid.uuid4())
            lifetime = conf.supybot.plugins.GPG.auth.sign.TokenTimeout()
            self._tokens.update({token: (msg.prefix, time.time()+lifetime)})
            irc.reply(_('Your token is: %s. Please sign it with your '
                'GPG key, paste it somewhere, and call the \'auth\' '
                'command with the URL to the (raw) file containing the '
                'signature.') % token)
        gettoken = wrap(gettoken, [])

        _auth_re = re.compile(r'-----BEGIN PGP SIGNED MESSAGE-----\r?\n'
                r'Hash: .*\r?\n\r?\n'
                r'\s*({[0-9a-z-]+})\s*\r?\n'
                r'-----BEGIN PGP SIGNATURE-----\r?\n.*'
                r'\r?\n-----END PGP SIGNATURE-----',
                re.S)
        
        @check_gpg_available
        def auth(self, irc, msg, args, url):
            """<url>

            Check the GPG signature at the <url> and authenticates you if
            the key used is associated to a user."""
            self._expire_tokens()
            content = safe_getUrl(url)
            if minisix.PY3 and isinstance(content, bytes):
                content = content.decode()
            match = self._auth_re.search(content)
            if not match:
                irc.error(_('Signature or token not found.'), Raise=True)
            data = match.group(0)
            token = match.group(1)
            if token not in self._tokens:
                irc.error(_('Unknown token. It may have expired before you '
                    'submit it.'), Raise=True)
            if self._tokens[token][0] != msg.prefix:
                irc.error(_('Your hostname/nick changed in the process. '
                    'Authentication aborted.'), Raise=True)
            verified = gpg.keyring.verify(data)
            if verified and verified.valid:
                keyid = verified.pubkey_fingerprint[-16:]
                prefix, expiry = self._tokens.pop(token)
                found = False
                for (id, user) in ircdb.users.items():
                    if keyid in [x[-len(keyid):] for x in user.gpgkeys]:
                        try:
                            user.addAuth(msg.prefix)
                        except ValueError:
                            irc.error(_('Your secure flag is true and your '
                                      'hostmask doesn\'t match any of your '
                                      'known hostmasks.'), Raise=True)
                        ircdb.users.setUser(user, flush=False)
                        irc.reply(_('You are now authenticated as %s.') %
                                user.name)
                        return
                irc.error(_('Unknown GPG key.'), Raise=True)
            else:
                irc.error(_('Signature could not be verified. Make sure '
                    'this is a valid GPG signature and the URL is valid.'))
        auth = wrap(auth, ['url'])


Class = GPG


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
