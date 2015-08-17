###
# Copyright (c) 2011, Valentin Lorentz
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
import sys
import cgi
import socket
from threading import Thread
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

import supybot.log as log
import supybot.conf as conf
import supybot.world as world
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization()

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

class RealSupyHTTPServer(HTTPServer):
    # TODO: make this configurable
    timeout = 0.5
    running = False

    def __init__(self, address, protocol, callback):
        if protocol == 4:
            self.address_family = socket.AF_INET
        elif protocol == 6:
            self.address_family = socket.AF_INET6
        else:
            raise AssertionError(protocol)
        HTTPServer.__init__(self, address, callback)
        self.callbacks = {}

    def hook(self, subdir, callback):
        if subdir in self.callbacks:
            log.warning(('The HTTP subdirectory `%s` was already hooked but '
                    'has been claimed by another plugin (or maybe you '
                    'reloaded the plugin and it didn\'t properly unhook. '
                    'Forced unhook.') % subdir)
        self.callbacks[subdir] = callback
        callback.doHook(self, subdir)
    def unhook(self, subdir):
        callback = self.callbacks.pop(subdir) # May raise a KeyError. We don't care.
        callback.doUnhook(self)
        return callback

    def __str__(self):
        return 'server at %s %i' % self.server_address[0:2]

class TestSupyHTTPServer(RealSupyHTTPServer):
    def __init__(self, *args, **kwargs):
        self.callbacks = {}
    def serve_forever(self, *args, **kwargs):
        pass
    def shutdown(self, *args, **kwargs):
        pass

if world.testing:
    SupyHTTPServer = TestSupyHTTPServer
else:
    SupyHTTPServer = RealSupyHTTPServer

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
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
        else:
            content_length = int(self.headers.get('Content-Length', '0'))
            form = self.rfile.read(content_length)
        self.do_X('doPost', form=form)

    def do_HEAD(self):
        self.do_X('doHead')


    def log_message(self, format, *args):
        log.info('HTTP request: %s - %s' %
                (self.address_string(), format % args))

class SupyHTTPServerCallback(object):
    """This is a base class that should be overriden by any plugin that want
    to have a Web interface."""
    __metaclass__ = log.MetaFirewall
    __firewalled__ = {'doGet': None,
                      'doPost': None,
                      'doHead': None,
                      'doPut': None,
                      'doDelete': None,
                     }


    fullpath = False
    name = "Unnamed plugin"
    defaultResponse = _("""
    This is a default response of the Supybot HTTP server. If you see this
    message, it probably means you are developing a plugin, and you have
    neither overriden this message or defined an handler for this query.""")

    if sys.version_info[0] >= 3:
        def write(self, b):
            if isinstance(b, str):
                b = b.encode()
            self.wfile.write(b)
    else:
        def write(self, s):
            self.wfile.write(s)

    def doGet(self, handler, path, *args, **kwargs):
        handler.send_response(400)
        self.send_header('Content-Type', 'text/plain; charset=utf-8; charset=utf-8')
        self.send_header('Content-Length', len(self.defaultResponse))
        self.end_headers()
        self.wfile.write(self.defaultResponse.encode())

    doPost = doHead = doGet

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
    def doGet(self, handler, path, *args, **kwargs):
        handler.send_response(404)
        self.send_header('Content-Type', 'text/plain; charset=utf-8; charset=utf-8')
        self.send_header('Content-Length', len(self.response))
        self.end_headers()
        response = self.response
        if sys.version_info[0] >= 3:
            response = response.encode()
        self.wfile.write(response)

    doPost = doHead = doGet

class SupyIndex(SupyHTTPServerCallback):
    """Displays the index of available plugins."""
    name = "index"
    fullpath = True
    defaultResponse = _("Request not handled.")
    def doGet(self, handler, path):
        plugins = [x for x in handler.server.callbacks.items()]
        if plugins == []:
            plugins = _('No plugins available.')
        else:
            plugins = '<ul class="plugins"><li>%s</li></ul>' % '</li><li>'.join(
                    ['<a href="/%s/">%s</a>' % (x,y.name) for x,y in plugins])
        response = get_template('index.html') % {'list': plugins}
        handler.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        if sys.version_info[0] >= 3:
            response = response.encode()
        self.wfile.write(response)

class Static(SupyHTTPServerCallback):
    """Serves static files."""
    fullpath = True
    name = 'static'
    defaultResponse = _('Request not handled')
    def __init__(self, mimetype='text/plain; charset=utf-8'):
        super(Static, self).__init__()
        self._mimetype = mimetype
    def doGet(self, handler, path):
        response = get_template(path)
        handler.send_response(200)
        self.send_header('Content-type', self._mimetype)
        self.send_header('Content-Length', len(response))
        self.end_headers()
        if sys.version_info[0] >= 3:
            response = response.encode()
        self.wfile.write(response)

class Favicon(SupyHTTPServerCallback):
    """Services the favicon.ico file to browsers."""
    name = 'favicon'
    defaultResponse = _('Request not handled')
    def doGet(self, handler, path):
        response = None
        file_path = conf.supybot.servers.http.favicon()
        found = False
        if file_path:
            try:
                icon = open(file_path, 'rb')
                response = icon.read()
            except IOError:
                pass
            finally:
                icon.close()
        if response is not None:
            filename = file_path.rsplit(os.sep, 1)[1]
            if '.' in filename:
                ext = filename.rsplit('.', 1)[1]
            else:
                ext = 'ico'
            # I have no idea why, but this headers are already sent.
            # self.send_header('Content-Length', len(response))
            # self.send_header('Content-type', 'image/' + ext)
            # self.end_headers()
            self.wfile.write(response)
        else:
            response = _('No favicon set.')
            handler.send_response(404)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            if sys.version_info[0] >= 3:
                response = response.encode()
            self.wfile.write(response)

http_servers = []

def startServer():
    """Starts the HTTP server. Shouldn't be called from other modules.
    The callback should be an instance of a child of SupyHTTPServerCallback."""
    global http_servers
    addresses4 = [(4, (x, configGroup.port()))
            for x in configGroup.hosts4().split(' ') if x != '']
    addresses6 = [(6, (x, configGroup.port()))
            for x in configGroup.hosts6().split(' ') if x != '']
    http_servers = []
    for protocol, address in (addresses4 + addresses6):
        server = SupyHTTPServer(address, protocol, SupyHTTPRequestHandler)
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
    for server in http_servers:
        callback = server.unhook(subdir)
        if len(server.callbacks) <= 0 and not configGroup.keepAlive():
            server.shutdown()
            http_servers.remove(server)
