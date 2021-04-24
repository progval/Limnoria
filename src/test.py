###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2011, James McCoy
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

import gc
import os
import re
import sys
import time
import shutil
import urllib
import unittest
import functools
import threading

from . import (callbacks, conf, drivers, httpserver, i18n, ircdb, irclib,
        ircmsgs, ircutils, log, plugin, registry, utils, world)
from .utils import minisix

if minisix.PY2:
    from httplib import HTTPConnection
    from urllib import splithost, splituser
    from urllib import URLopener
else:
    from http.client import HTTPConnection
    from urllib.parse import splithost, splituser
    from urllib.request import URLopener

class verbosity:
    NONE = 0
    EXCEPTIONS = 1
    MESSAGES = 2

i18n.import_conf()
network = True
setuid = True

# This is the global list of suites that are to be run.
suites = []

timeout = 10

originalCallbacksGetHelp = callbacks.getHelp
lastGetHelp = 'x' * 1000
def cachingGetHelp(method, name=None, doc=None):
    global lastGetHelp
    lastGetHelp = originalCallbacksGetHelp(method, name, doc)
    return lastGetHelp
callbacks.getHelp = cachingGetHelp

real_time = time.time
mock_time_offset = 0

def mockTime():
    """Wrapper for time.time() that adds an offset, eg. for skipping after a
    timeout expired."""
    return real_time() + mock_time_offset

def timeFastForward(extra_offset):
    global mock_time_offset
    mock_time_offset += extra_offset

def setupMockTime():
    time.time = mockTime

def teardownMockTime():
    time.time = real_time

def retry(tries=3):
    assert tries > 0
    def decorator(f):
        @functools.wraps(f)
        def newf(self):
            try:
                f(self)
            except AssertionError as e:
                first_exception = e
            for _ in range(1, tries):
                try:
                    f(self)
                except AssertionError as e:
                    pass
                else:
                    break
            else:
                # All failed
                raise first_exception
        return newf
    return decorator

def getTestIrc(name='test'):
    irc = irclib.Irc(name)
    # Gotta clear the connect messages (USER, NICK, etc.)
    while irc.takeMsg():
        pass
    return irc

class TimeoutError(AssertionError):
    def __str__(self):
        return '%r timed out' % self.args[0]

class TestPlugin(callbacks.Plugin):
    def eval(self, irc, msg, args):
        """<text>

        This is the help for eval.  Since Owner doesn't have an eval command
        anymore, we needed to add this so as not to invalidate any of the tests
        that depended on that eval command.
        """
        try:
            irc.reply(repr(eval(' '.join(args))))
        except callbacks.ArgumentError:
            raise
        except Exception as e:
            irc.reply(utils.exnToString(e))
# Since we know we don't now need the Irc object, we just give None.  This
# might break if callbacks.Privmsg ever *requires* the Irc object.
TestInstance = TestPlugin(None)
conf.registerPlugin('TestPlugin', True, public=False)

class SupyTestCase(unittest.TestCase):
    """This class exists simply for extra logging.  It's come in useful in the
    past."""
    def setUp(self):
        log.critical('Beginning test case %s', self.id())
        threads = [t.getName() for t in threading.enumerate()]
        log.critical('Threads: %L', threads)
        setupMockTime()
        unittest.TestCase.setUp(self)

    def tearDown(self):
        for irc in world.ircs[:]:
            irc._reallyDie()
        teardownMockTime()

    if sys.version_info < (2, 7, 0):
        def assertIn(self, member, container, msg=None):
            """Just like self.assertTrue(a in b), but with a nicer default message."""
            if member not in container:
                standardMsg = '%s not found in %s' % (repr(member),
                                                      repr(container))
                self.fail(self._formatMessage(msg, standardMsg))

        def assertNotIn(self, member, container, msg=None):
            """Just like self.assertTrue(a not in b), but with a nicer default message."""
            if member in container:
                standardMsg = '%s unexpectedly found in %s' % (repr(member),
                                                            repr(container))
                self.fail(self._formatMessage(msg, standardMsg))

        def assertIs(self, expr1, expr2, msg=None):
            """Just like self.assertTrue(a is b), but with a nicer default message."""
            if expr1 is not expr2:
                standardMsg = '%s is not %s' % (repr(expr1),
                                                 repr(expr2))
                self.fail(self._formatMessage(msg, standardMsg))

        def assertIsNot(self, expr1, expr2, msg=None):
            """Just like self.assertTrue(a is not b), but with a nicer default message."""
            if expr1 is expr2:
                standardMsg = 'unexpectedly identical: %s' % (repr(expr1),)
                self.fail(self._formatMessage(msg, standardMsg))


class PluginTestCase(SupyTestCase):
    """Subclass this to write a test case for a plugin.  See
    plugins/Plugin/test.py for an example.
    """
    plugins = None
    cleanConfDir = True
    cleanDataDir = True
    config = {}
    timeout = None
    def __init__(self, methodName='runTest'):
        if self.timeout is None:
            self.timeout = timeout
        originalRunTest = getattr(self, methodName)
        def runTest(self):
            run = True
            if hasattr(self, 'irc') and self.irc:
                for cb in self.irc.callbacks:
                    cbModule = sys.modules[cb.__class__.__module__]
                    if hasattr(cbModule, 'deprecated') and cbModule.deprecated:
                        print('')
                        print('Ignored, %s is deprecated.' % cb.name())
                        run = False
            if run:
                originalRunTest()
        runTest = utils.python.changeFunctionName(runTest, methodName)
        setattr(self.__class__, methodName, runTest)
        SupyTestCase.__init__(self, methodName=methodName)
        self.originals = {}

    def setUp(self, nick='test', forceSetup=False):
        if not forceSetup and \
                self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn\'t run.
            return
        SupyTestCase.setUp(self)
        # Just in case, let's do this.  Too many people forget to call their
        # super methods.
        for irc in world.ircs[:]:
            irc._reallyDie()
        # Set conf variables appropriately.
        conf.supybot.reply.whenAddressedBy.chars.setValue('@')
        conf.supybot.reply.error.detailed.setValue(True)
        conf.supybot.reply.whenNotCommand.setValue(True)
        # Choose a random port for tests using the HTTP server
        conf.supybot.servers.http.port.setValue(0)
        self.myVerbose = world.myVerbose
        def rmFiles(dir):
            for filename in os.listdir(dir):
                file = os.path.join(dir, filename)
                if os.path.isfile(file):
                    os.remove(file)
                else:
                    shutil.rmtree(file)
        if self.cleanConfDir:
            rmFiles(conf.supybot.directories.conf())
        if self.cleanDataDir:
            rmFiles(conf.supybot.directories.data())
        ircdb.users.reload()
        ircdb.ignores.reload()
        ircdb.channels.reload()
        if self.plugins is None:
            raise ValueError('PluginTestCase must have a "plugins" attribute.')
        self.nick = nick
        self.prefix = ircutils.joinHostmask(nick, 'user', 'host.domain.tld')
        self.irc = getTestIrc()
        MiscModule = plugin.loadPluginModule('Misc')
        OwnerModule = plugin.loadPluginModule('Owner')
        ConfigModule = plugin.loadPluginModule('Config')
        plugin.loadPluginClass(self.irc, MiscModule)
        plugin.loadPluginClass(self.irc, OwnerModule)
        plugin.loadPluginClass(self.irc, ConfigModule)
        if isinstance(self.plugins, str):
            self.plugins = [self.plugins]
        else:
            for name in self.plugins:
                if name not in ('Owner', 'Misc', 'Config'):
                    module = plugin.loadPluginModule(name,
                                                     ignoreDeprecation=True)
                    plugin.loadPluginClass(self.irc, module)
        self.irc.addCallback(TestInstance)
        for (name, value) in self.config.items():
            group = conf.supybot
            parts = registry.split(name)
            if parts[0] == 'supybot':
                parts.pop(0)
            for part in parts:
                group = group.get(part)
            self.originals[group] = group()
            group.setValue(value)

    def tearDown(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            # Necessary because there's a test in here that shouldn't run.
            return
        for (group, original) in self.originals.items():
            group.setValue(original)
        ircdb.users.close()
        ircdb.ignores.close()
        ircdb.channels.close()
        SupyTestCase.tearDown(self)
        self.irc = None
        gc.collect()

    def _feedMsg(self, query, timeout=None, to=None, frm=None,
                 usePrefixChar=True, expectException=False):
        if to is None:
            to = self.irc.nick
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose >= verbosity.MESSAGES:
            print('') # Extra newline, so it's pretty.
        prefixChars = conf.supybot.reply.whenAddressedBy.chars()
        if not usePrefixChar and query[0] in prefixChars:
            query = query[1:]
        if minisix.PY2:
            query = query.encode('utf8') # unicode->str
        msg = ircmsgs.privmsg(to, query, prefix=frm)
        if self.myVerbose >= verbosity.MESSAGES:
            print('Feeding: %r' % msg)
        if not expectException and self.myVerbose >= verbosity.EXCEPTIONS:
            conf.supybot.log.stdout.setValue(True)
        self.irc.feedMsg(msg)
        fed = real_time()
        response = self.irc.takeMsg()
        while response is None and real_time() - fed < timeout:
            time.sleep(0.01) # So it doesn't suck up 100% cpu.
            drivers.run()
            response = self.irc.takeMsg()
        if self.myVerbose >= verbosity.MESSAGES:
            print('Response: %r' % response)
        if not expectException and self.myVerbose >= verbosity.EXCEPTIONS:
            conf.supybot.log.stdout.setValue(False)
        return response

    def getMsg(self, query, **kwargs):
        return self._feedMsg(query, **kwargs)

    def feedMsg(self, query, to=None, frm=None):
        """Just feeds it a message, that's all."""
        if to is None:
            to = self.irc.nick
        if frm is None:
            frm = self.prefix
        self.irc.feedMsg(ircmsgs.privmsg(to, query, prefix=frm))

    # These assertError/assertNoError are somewhat fragile.  The proper way to
    # do them would be to use a proxy for the irc object and intercept .error.
    # But that would be hard, so I don't bother.  When this breaks, it'll get
    # fixed, but not until then.
    def assertError(self, query, **kwargs):
        m = self._feedMsg(query, expectException=True, **kwargs)
        if m is None:
            raise TimeoutError(query)
        if lastGetHelp not in m.args[1]:
            self.assertTrue(m.args[1].startswith('Error:'),
                            '%r did not error: %s' % (query, m.args[1]))
        return m

    def assertSnarfError(self, query, **kwargs):
        return self.assertError(query, usePrefixChar=False, **kwargs)

    def assertNotError(self, query, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertFalse(m.args[1].startswith('Error:'),
                         '%r errored: %s' % (query, m.args[1]))
        self.assertFalse(lastGetHelp in m.args[1],
                         '%r returned the help string.' % query)
        return m

    def assertSnarfNotError(self, query, **kwargs):
        return self.assertNotError(query, usePrefixChar=False, **kwargs)

    def assertHelp(self, query, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        msg = m.args[1]
        if 'more message' in msg:
            msg = msg[0:-27] # Strip (XXX more messages)
        self.assertTrue(msg in lastGetHelp,
                        '%s is not the help (%s)' % (m.args[1], lastGetHelp))
        return m

    def assertNoResponse(self, query, timeout=None, **kwargs):
        if timeout is None:
            timeout = 0
            # timeout=0 does not wait at all for an answer after the command
            # function finished running. This is fine for non-threaded
            # plugins because they usually won't answer anything after that;
            # but not for threaded plugins.
            # TODO: also detect threaded commands
            for cb in self.irc.callbacks:
                if cb.threaded:
                    timeout = self.timeout
                    break
        m = self._feedMsg(query, timeout=timeout, **kwargs)
        self.assertFalse(m, 'Unexpected response: %r' % m)
        return m

    def assertSnarfNoResponse(self, query, timeout=None, **kwargs):
        return self.assertNoResponse(query, timeout=timeout,
                                     usePrefixChar=False, **kwargs)

    def assertResponse(self, query, expectedResponse, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertEqual(m.args[1], expectedResponse,
                         '%r != %r' % (expectedResponse, m.args[1]))
        return m

    def assertSnarfResponse(self, query, expectedResponse, **kwargs):
        return self.assertResponse(query, expectedResponse,
                                   usePrefixChar=False, **kwargs)

    def assertRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertTrue(re.search(regexp, m.args[1], flags),
                        '%r does not match %r' % (m.args[1], regexp))
        return m

    def assertSnarfRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertRegexp(query, regexp, flags=re.I,
                                 usePrefixChar=False, **kwargs)

    def assertNotRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertTrue(re.search(regexp, m.args[1], flags) is None,
                        '%r matched %r' % (m.args[1], regexp))
        return m

    def assertSnarfNotRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertNotRegexp(query, regexp, flags=re.I,
                                    usePrefixChar=False, **kwargs)

    def assertAction(self, query, expectedResponse=None, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertTrue(ircmsgs.isAction(m), '%r is not an action.' % m)
        if expectedResponse is not None:
            s = ircmsgs.unAction(m)
            self.assertEqual(s, expectedResponse,
                             '%r != %r' % (s, expectedResponse))
        return m

    def assertSnarfAction(self, query, expectedResponse=None, **kwargs):
        return self.assertAction(query, expectedResponse=None,
                                 usePrefixChar=False, **kwargs)

    def assertActionRegexp(self, query, regexp, flags=re.I, **kwargs):
        m = self._feedMsg(query, **kwargs)
        if m is None:
            raise TimeoutError(query)
        self.assertTrue(ircmsgs.isAction(m))
        s = ircmsgs.unAction(m)
        self.assertTrue(re.search(regexp, s, flags),
                        '%r does not match %r' % (s, regexp))

    def assertSnarfActionRegexp(self, query, regexp, flags=re.I, **kwargs):
        return self.assertActionRegexp(query, regexp, flags=re.I,
                                       usePrefixChar=False, **kwargs)

    _noTestDoc = ('Admin', 'Channel', 'Config',
                  'Misc', 'Owner', 'User', 'TestPlugin')
    def TestDocumentation(self):
        if self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            return
        for cb in self.irc.callbacks:
            name = cb.name()
            if ((name in self._noTestDoc) and \
               not name.lower() in self.__class__.__name__.lower()):
                continue
            self.assertTrue(sys.modules[cb.__class__.__name__].__doc__,
                            '%s has no module documentation.' % name)
            if hasattr(cb, 'isCommandMethod'):
                for attr in dir(cb):
                    if cb.isCommandMethod(attr) and \
                       attr == callbacks.canonicalName(attr):
                        self.assertTrue(getattr(cb, attr, None).__doc__,
                                        '%s.%s has no help.' % (name, attr))



class ChannelPluginTestCase(PluginTestCase):
    channel = '#test'
    def setUp(self, nick='test', forceSetup=False):
        if not forceSetup and \
                self.__class__ in (PluginTestCase, ChannelPluginTestCase):
            return
        PluginTestCase.setUp(self, nick, forceSetup)
        self.irc.feedMsg(ircmsgs.join(self.channel, prefix=self.prefix))
        m = self.irc.takeMsg()
        self.assertFalse(m is None, 'No message back from joining channel.')
        self.assertEqual(m.command, 'MODE')
        m = self.irc.takeMsg()
        self.assertFalse(m is None, 'No message back from joining channel.')
        self.assertEqual(m.command, 'MODE')
        m = self.irc.takeMsg()
        self.assertFalse(m is None, 'No message back from joining channel.')
        self.assertEqual(m.command, 'WHO')

    def _feedMsg(self, query, timeout=None, to=None, frm=None, private=False,
                 usePrefixChar=True, expectException=False):
        if to is None:
            if private:
                to = self.irc.nick
            else:
                to = self.channel
        if frm is None:
            frm = self.prefix
        if timeout is None:
            timeout = self.timeout
        if self.myVerbose >= verbosity.MESSAGES:
            print('') # Newline, just like PluginTestCase.
        prefixChars = conf.supybot.reply.whenAddressedBy.chars()
        if query[0] not in prefixChars and usePrefixChar:
            query = prefixChars[0] + query
        if minisix.PY2 and isinstance(query, unicode):
            query = query.encode('utf8') # unicode->str
        if not expectException and self.myVerbose >= verbosity.EXCEPTIONS:
            conf.supybot.log.stdout.setValue(True)
        msg = ircmsgs.privmsg(to, query, prefix=frm)
        if self.myVerbose >= verbosity.MESSAGES:
            print('Feeding: %r' % msg)
        self.irc.feedMsg(msg)
        fed = real_time()
        response = self.irc.takeMsg()
        while response is None and real_time() - fed < timeout:
            time.sleep(0.1)
            drivers.run()
            response = self.irc.takeMsg()
        if response is not None:
            if response.command == 'PRIVMSG':
                args = list(response.args)
                # Strip off nick: at beginning of response.
                if args[1].startswith(self.nick) or \
                   args[1].startswith(ircutils.nickFromHostmask(self.prefix)):
                    try:
                        args[1] = args[1].split(' ', 1)[1]
                    except IndexError:
                        # Odd.  We'll skip this.
                        pass
                ret = ircmsgs.privmsg(*args)
            else:
                ret = response
        else:
            ret = None
        if self.myVerbose >= verbosity.MESSAGES:
            print('Returning: %r' % ret)
        if not expectException and self.myVerbose >= verbosity.EXCEPTIONS:
            conf.supybot.log.stdout.setValue(False)
        return ret

    def feedMsg(self, query, to=None, frm=None, private=False):
        """Just feeds it a message, that's all."""
        if to is None:
            if private:
                to = self.irc.nick
            else:
                to = self.channel
        if frm is None:
            frm = self.prefix
        self.irc.feedMsg(ircmsgs.privmsg(to, query, prefix=frm))

class TestRequestHandler(httpserver.SupyHTTPRequestHandler):
    def __init__(self, rfile, wfile, *args, **kwargs):
        self._headers_mode = True
        self.rfile = rfile
        self.wfile = wfile
        self.handle_one_request()

    def send_response(self, code):
        assert self._headers_mode
        self._response = code
    def send_headers(self, name, value):
        assert self._headers_mode
        self._headers[name] = value
    def end_headers(self):
        assert self._headers_mode
        self._headers_mode = False

    def do_X(self, *args, **kwargs):
        assert httpserver.http_servers, \
                'The HTTP server is not started.'
        self.server = httpserver.http_servers[0]
        httpserver.SupyHTTPRequestHandler.do_X(self, *args, **kwargs)

httpserver.http_servers = [httpserver.TestSupyHTTPServer()]

# Partially stolen from the standard Python library :)
def open_http(url, data=None):
    """Use HTTP protocol."""
    user_passwd = None
    proxy_passwd= None
    if isinstance(url, str):
        host, selector = splithost(url)
        if host:
            user_passwd, host = splituser(host)
            host = urllib.unquote(host)
        realhost = host
    else:
        host, selector = url
        # check whether the proxy contains authorization information
        proxy_passwd, host = splituser(host)
        # now we proceed with the url we want to obtain
        urltype, rest = urllib.splittype(selector)
        url = rest
        user_passwd = None
        if urltype.lower() != 'http':
            realhost = None
        else:
            realhost, rest = splithost(rest)
            if realhost:
                user_passwd, realhost = splituser(realhost)
            if user_passwd:
                selector = "%s://%s%s" % (urltype, realhost, rest)
            if urllib.proxy_bypass(realhost):
                host = realhost

        #print "proxy via http:", host, selector
    if not host: raise IOError('http error', 'no host given')

    if proxy_passwd:
        import base64
        proxy_auth = base64.b64encode(proxy_passwd).strip()
    else:
        proxy_auth = None

    if user_passwd:
        import base64
        auth = base64.b64encode(user_passwd).strip()
    else:
        auth = None
    c = FakeHTTPConnection(host)
    if data is not None:
        c.putrequest('POST', selector)
        c.putheader('Content-Type', 'application/x-www-form-urlencoded')
        c.putheader('Content-Length', '%d' % len(data))
    else:
        c.putrequest('GET', selector)
    if proxy_auth: c.putheader('Proxy-Authorization', 'Basic %s' % proxy_auth)
    if auth: c.putheader('Authorization', 'Basic %s' % auth)
    if realhost: c.putheader('Host', realhost)
    for args in URLopener().addheaders: c.putheader(*args)
    c.endheaders()
    return c

class FakeHTTPConnection(HTTPConnection):
    _data = ''
    _headers = {}
    def __init__(self, rfile, wfile):
        HTTPConnection.__init__(self, 'localhost')
        self.rfile = rfile
        self.wfile = wfile
    def send(self, data):
        self.wfile.write(data)
    #def putheader(self, name, value):
    #    self._headers[name] = value
    #def connect(self, *args, **kwargs):
    #    self.sock = self.wfile
    #def getresponse(self, *args, **kwargs):
    #    pass

class HTTPPluginTestCase(PluginTestCase):
    def setUp(self):
        PluginTestCase.setUp(self, forceSetup=True)

    def request(self, url, method='GET', read=True, data={}):
        assert url.startswith('/')
        wfile = minisix.io.BytesIO()
        rfile = minisix.io.BytesIO()
        connection = FakeHTTPConnection(wfile, rfile)
        connection.putrequest(method, url)
        connection.endheaders()
        rfile.seek(0)
        handler = TestRequestHandler(rfile, wfile)
        wfile.seek(0)
        if read:
            return (handler._response, wfile.read())
        else:
            return handler._response

    def assertHTTPResponse(self, uri, expectedResponse, **kwargs):
        response = self.request(uri, read=False, **kwargs)
        self.assertEqual(response, expectedResponse)

    def assertNotHTTPResponse(self, uri, expectedResponse, **kwargs):
        response = self.request(uri, read=False, **kwargs)
        self.assertNotEqual(response, expectedResponse)

class ChannelHTTPPluginTestCase(ChannelPluginTestCase, HTTPPluginTestCase):
    def setUp(self):
        ChannelPluginTestCase.setUp(self, forceSetup=True)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

