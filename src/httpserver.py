###
# Copyright (c) 2011-2024, Valentin Lorentz
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

"""
An embedded and centralized HTTP server for Supybot's plugins.
"""

import os
import socket
import urllib.parse
from threading import Thread

import supybot.log as log
import supybot.conf as conf
import supybot.world as world
import supybot.utils.minisix as minisix
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization()

if minisix.PY2:
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
else:
    from http.server import HTTPServer, BaseHTTPRequestHandler

configGroup = conf.supybot.servers.http

class RequestNotHandled(Exception):
    pass

DEFAULT_TEMPLATES = {
    'index.html': """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <title>""" + _('Supybot Web server index') + """</title>
  <link rel="stylesheet" type="text/css" href="/default.css" media="screen" />
 </head>
 <body class="purelisting">
  <h1>Supybot web server index</h1>
  <p>""" + _('Here is a list of the plugins that have a Web interface:') +\
  """
  </p>
  %(list)s
 </body>
</html>""",
    'generic/error.html': """\
<!DOCTYPE html>
<html>
 <head>
  <meta charset="UTF-8" />
  <title>%(title)s</title>
  <link rel="stylesheet" href="/default.css" />
 </head>
 <body class="error">
  <h1>Error</h1>
  <p>%(error)s</p>
 </body>
</html>""",
    'default.css': """\
body {
    background-color: #F0F0F0;
}

/************************************
 * Classes that plugins should use. *
 ************************************/

/* Error pages */
body.error {
    text-align: center;
}
body.error p {
    background-color: #FFE0E0;
    border: 1px #FFA0A0 solid;
}

/* Pages that only contain a list. */
.purelisting {
    text-align: center;
}
.purelisting ul {
    margin: 0;
    padding: 0;
}
.purelisting ul li {
    margin: 0;
    padding: 0;
    list-style-type: none;
}

/* Pages that only contain a table. */
.puretable {
    text-align: center;
}
.puretable table
{
    width: 100%;
    border-collapse: collapse;
    text-align: center;
}

.puretable table th
{
    /*color: #039;*/
    padding: 10px 8px;
    border-bottom: 2px solid #6678b1;
}

.puretable table td
{
    padding: 9px 8px 0px 8px;
    border-bottom: 1px solid #ccc;
}

""",
    'robots.txt': """""",
    }

def set_default_templates(defaults):
    for filename, content in defaults.items():
        path = conf.supybot.directories.data.web.dirize(filename)
        if os.path.isfile(path + '.example'):
            os.unlink(path + '.example')
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        with open(path + '.example', 'a') as fd:
            fd.write(content)
set_default_templates(DEFAULT_TEMPLATES)

def get_template(filename):
    path = conf.supybot.directories.data.web.dirize(filename)
    if os.path.isfile(path):
        with open(path, 'r') as fd:
            return fd.read()
    else:
        assert os.path.isfile(path + '.example'), path + '.example'
        with open(path + '.example', 'r') as fd:
            return fd.read()

class HttpHeader:
    __slots__ = ('name', 'value')

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        """Return printable representation."""
        return "HttpHeader(%r, %r)" % (self.name, self.value)

class HttpHeaders:
    """Copy of `cgi.FieldStorage
    <https://github.com/python/cpython/blob/v3.12.3/Lib/cgi.py#L512-L594>`
    before it was removed from the stdlib.
    """
    __slots__ = ('list',)
    def __init__(self, headers):
        self.list = headers

    def __repr__(self):
        return 'HttpHeaders(%r)' % self.list

    def __iter__(self):
        return iter(self.keys())

    def __getattr__(self, name):
        if name != 'value':
            raise AttributeError(name)
        if self.file:
            self.file.seek(0)
            value = self.file.read()
            self.file.seek(0)
        elif self.list is not None:
            value = self.list
        else:
            value = None
        return value

    def __getitem__(self, key):
        """Dictionary style indexing."""
        if self.list is None:
            raise TypeError("not indexable")
        found = []
        for item in self.list:
            if item.name == key: found.append(item)
        if not found:
            raise KeyError(key)
        if len(found) == 1:
            return found[0]
        else:
            return found

    def getvalue(self, key, default=None):
        """Dictionary style get() method, including 'value' lookup."""
        if key in self:
            value = self[key]
            if isinstance(value, list):
                return [x.value for x in value]
            else:
                return value.value
        else:
            return default

    def getfirst(self, key, default=None):
        """ Return the first value received."""
        if key in self:
            value = self[key]
            if isinstance(value, list):
                return value[0].value
            else:
                return value.value
        else:
            return default

    def getlist(self, key):
        """ Return list of received values."""
        if key in self:
            value = self[key]
            if isinstance(value, list):
                return [x.value for x in value]
            else:
                return [value.value]
        else:
            return []

    def keys(self):
        """Dictionary style keys() method."""
        if self.list is None:
            raise TypeError("not indexable")
        return list(set(item.name for item in self.list))

    def __contains__(self, key):
        """Dictionary style __contains__ method."""
        if self.list is None:
            raise TypeError("not indexable")
        return any(item.name == key for item in self.list)

    def __len__(self):
        """Dictionary style len(x) support."""
        return len(self.keys())

    def __bool__(self):
        if self.list is None:
            raise TypeError("Cannot be converted to bool.")
        return bool(self.list)


class SupyHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_X(self, callbackMethod, *args, **kwargs):
        if self.path == '/':
            callback = SupyIndex()
        elif self.path in ('/robots.txt',):
            callback = Static('text/plain; charset=utf-8')
        elif self.path in ('/default.css',):
            callback = Static('text/css')
        elif self.path == '/favicon.ico':
            callback = Favicon()
        else:
            subdir = self.path.split('/')[1]
            try:
                callback = self.server.callbacks[subdir]
            except KeyError:
                callback = Supy404()

        # Some shortcuts
        for name in ('send_response', 'send_header', 'end_headers', 'rfile',
                'wfile', 'headers'):
            setattr(callback, name, getattr(self, name))
        # We call doX, because this is more supybotic than do_X.
        path = self.path
        if not callback.fullpath:
            path = '/' + path.split('/', 2)[-1]
        getattr(callback, callbackMethod)(self, path,
                *args, **kwargs)

    def do_GET(self):
        self.do_X('doGet')

    def do_POST(self):
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if self.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            length = min(100000, int(self.headers.get('Content-Length', '100000')))
            qs = self.rfile.read(length).decode()
            form = HttpHeaders([
                HttpHeader(k, v) for (k, v) in urllib.parse.parse_qsl(qs)
            ])
        else:
            content_length = int(self.headers.get('Content-Length', '0'))
            form = self.rfile.read(content_length)
        self.do_X('doPost', form=form)

    def do_HEAD(self):
        self.do_X('doHead')

    def address_string(self):
        s = BaseHTTPRequestHandler.address_string(self)

        # Strip IPv4-mapped IPv6 addresses such as ::ffff:127.0.0.1
        prefix = '::ffff:'
        if s.startswith(prefix):
            s = s[len(prefix):]

        return s

    def log_message(self, format, *args):
        log.info('HTTP request: %s - %s' %
                (self.address_string(), format % args))

class SupyHTTPServerCallback(log.Firewalled):
    """This is a base class that should be overriden by any plugin that want
    to have a Web interface."""
    __firewalled__ = {'doGet': None,
                      'doPost': None,
                      'doHead': None,
                      'doPut': None,
                      'doDelete': None,
                     }


    fullpath = False
    name = "Unnamed plugin"
    public = True
    """Whether the callback should be listed in the root index."""
    defaultResponse = _("""
    This is a default response of the Supybot HTTP server. If you see this
    message, it probably means you are developing a plugin, and you have
    neither overriden this message or defined an handler for this query.""")

    if minisix.PY3:
        def write(self, b):
            if isinstance(b, str):
                b = b.encode()
            self.wfile.write(b)
    else:
        def write(self, s):
            self.wfile.write(s)

    def doGetOrHead(self, handler, path, write_content):
        response = self.defaultResponse.encode()
        handler.send_response(405)
        self.send_header('Content-Type', 'text/plain; charset=utf-8; charset=utf-8')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        if write_content:
            self.wfile.write(response)

    def doGet(self, handler, path):
        self.doGetOrHead(handler, path, write_content=True)
    def doHead(self, handler, path):
        self.doGetOrHead(handler, path, write_content=False)

    def doPost(self, handler, path, form=None):
        self.doGetOrHead(handler, path, write_content=True)

    def doWellKnown(self, handler, path):
        """Handles GET request to /.well-known/"""
        return None

    def doHook(self, handler, subdir):
        """Method called when hooking this callback."""
        pass
    def doUnhook(self, handler):
        """Method called when unhooking this callback."""
        pass

class Supy404(SupyHTTPServerCallback):
    """A 404 Not Found error."""
    name = "Error 404"
    fullpath = True
    response = _("""
    I am a pretty clever IRC bot, but I suck at serving Web pages, particulary
    if I don't know what to serve.
    What I'm saying is you just triggered a 404 Not Found, and I am not
    trained to help you in such a case.""")
    def doGetOrHead(self, handler, path, write_content):
        response = self.response
        if minisix.PY3:
            response = response.encode()
        handler.send_response(404)
        self.send_header('Content-Type', 'text/plain; charset=utf-8; charset=utf-8')
        self.send_header('Content-Length', len(self.response))
        self.end_headers()
        if write_content:
            self.wfile.write(response)

class SupyIndex(SupyHTTPServerCallback):
    """Displays the index of available plugins."""
    name = "index"
    defaultResponse = _("Request not handled.")
    def doGetOrHead(self, handler, path, write_content):
        plugins = [
            (name, cb)
            for (name, cb) in handler.server.callbacks.items()
            if cb.public]
        if plugins == []:
            plugins = _('No plugins available.')
        else:
            plugins = '<ul class="plugins"><li>%s</li></ul>' % '</li><li>'.join(
                    ['<a href="/%s/">%s</a>' % (x,y.name) for x,y in plugins])
        response = get_template('index.html') % {'list': plugins}
        if minisix.PY3:
            response = response.encode()
        handler.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        if write_content:
            self.wfile.write(response)

class Static(SupyHTTPServerCallback):
    """Serves static files."""
    fullpath = True
    name = 'static'
    defaultResponse = _('Request not handled')
    def __init__(self, mimetype='text/plain; charset=utf-8'):
        super(Static, self).__init__()
        self._mimetype = mimetype
    def doGetOrHead(self, handler, path, write_content):
        response = get_template(path[1:]) # strip leading /
        if minisix.PY3:
            response = response.encode()
        handler.send_response(200)
        self.send_header('Content-type', self._mimetype)
        self.send_header('Content-Length', len(response))
        self.end_headers()
        if write_content:
            self.wfile.write(response)

class Favicon(SupyHTTPServerCallback):
    """Services the favicon.ico file to browsers."""
    name = 'favicon'
    defaultResponse = _('Request not handled')
    def doGetOrHead(self, handler, path, write_content):
        response = None
        file_path = conf.supybot.servers.http.favicon()
        if file_path:
            try:
                icon = open(file_path, 'rb')
                response = icon.read()
            except IOError:
                pass
            finally:
                icon.close()
        if response is not None:
            # I have no idea why, but this headers are already sent.
            # filename = file_path.rsplit(os.sep, 1)[1]
            # if '.' in filename:
            #     ext = filename.rsplit('.', 1)[1]
            # else:
            #     ext = 'ico'
            # self.send_header('Content-Length', len(response))
            # self.send_header('Content-type', 'image/' + ext)
            # self.end_headers()
            if write_content:
                self.wfile.write(response)
        else:
            response = _('No favicon set.')
            if minisix.PY3:
                response = response.encode()
            handler.send_response(404)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            if write_content:
                self.wfile.write(response)

class SupyWellKnown(SupyHTTPServerCallback):
    """Serves /.well-known/ resources."""
    name = 'well-known'
    defaultResponse = _('Request not handled')
    public = False

    def doGetOrHead(self, handler, path, write_content):
        for callback in handler.server.callbacks.values():
            resp = callback.doWellKnown(handler, path)
            if resp:
                (status, headers, content) = resp
                handler.send_response(status)
                for header in headers.items():
                    self.send_header(*header)
                self.end_headers()
                if write_content:
                    self.wfile.write(content)
                return

        handler.send_response(404)
        self.end_headers()
        self.wfile.write(b"Error 404. There is nothing to see here.")


DEFAULT_CALLBACKS = {'.well-known': SupyWellKnown()}


class RealSupyHTTPServer(HTTPServer):
    # TODO: make this configurable
    timeout = 0.5
    running = False

    def __init__(self, address, protocol, callback):
        self.protocol = protocol
        if protocol == 4:
            self.address_family = socket.AF_INET
        elif protocol == 6:
            self.address_family = socket.AF_INET6
        else:
            raise AssertionError(protocol)
        HTTPServer.__init__(self, address, callback)
        self.callbacks = DEFAULT_CALLBACKS.copy()

    def server_bind(self):
        if self.protocol == 6:
            v = conf.supybot.servers.http.singleStack()
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, v)
        HTTPServer.server_bind(self)

    def hook(self, subdir, callback):
        if subdir in self.callbacks:
            log.warning(('The HTTP subdirectory `%s` was already hooked but '
                    'has been claimed by another plugin (or maybe you '
                    'reloaded the plugin and it didn\'t properly unhook. '
                    'Forced unhook.') % subdir)
        self.callbacks[subdir] = callback
        callback.doHook(self, subdir)
    def unhook(self, subdir):
        callback = self.callbacks.pop(subdir, None)
        if callback:
            callback.doUnhook(self)
        return callback

    def __str__(self):
        return 'server at %s %i' % self.server_address[0:2]

class TestSupyHTTPServer(RealSupyHTTPServer):
    def __init__(self, *args, **kwargs):
        self.callbacks = {}
        self.server_address = ("0.0.0.0", 0)
    def serve_forever(self, *args, **kwargs):
        pass
    def shutdown(self, *args, **kwargs):
        pass

if world.testing or world.documenting:
    SupyHTTPServer = TestSupyHTTPServer
else:
    SupyHTTPServer = RealSupyHTTPServer

http_servers = []

def startServer():
    """Starts the HTTP server. Shouldn't be called from other modules.
    The callback should be an instance of a child of SupyHTTPServerCallback."""
    global http_servers
    addresses4 = [(4, (x, configGroup.port()))
            for x in configGroup.hosts4() if x != '']
    addresses6 = [(6, (x, configGroup.port()))
            for x in configGroup.hosts6() if x != '']
    http_servers = []
    for protocol, address in (addresses4 + addresses6):
        try:
            server = SupyHTTPServer(address, protocol, SupyHTTPRequestHandler)
        except OSError as e:
            log.error(
                'Failed to start HTTP server with protocol %s at address: %s',
                protocol, address, e)
            if e.args[0] == 98:
                log.error(
                    'This means the port (and address) is already in use by an '
                    'other process. Either find the process using the port '
                    'and stop it, or change the port configured in '
                    'supybot.servers.http.port.')
            continue
        except:
            log.exception(
                "Failed to start HTTP server with protocol %s at address",
                protocol, address)
            continue
        Thread(target=server.serve_forever, name='HTTP Server').start()
        http_servers.append(server)
        log.info('Starting HTTP server: %s' % str(server))

def stopServer():
    """Stops the HTTP server. Should be run only from this module or from
    when the bot is dying (ie. from supybot.world)"""
    global http_servers
    for server in http_servers:
        log.info('Stopping HTTP server: %s' % str(server))
        server.shutdown()
        server = None

if configGroup.keepAlive():
    startServer()

def hook(subdir, callback):
    """Sets a callback for a given subdir."""
    if not http_servers:
        startServer()
    assert isinstance(http_servers, list)
    for server in http_servers:
        server.hook(subdir, callback)

def unhook(subdir):
    """Unsets the callback assigned to the given subdir, and return it."""
    global http_servers
    assert isinstance(http_servers, list)
    for server in list(http_servers):
        server.unhook(subdir)
        if len(set(server.callbacks) - set(DEFAULT_CALLBACKS)) <= 0 \
                and not configGroup.keepAlive():
            server.shutdown()
            http_servers.remove(server)
