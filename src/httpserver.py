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

import cgi
from threading import Event, Thread
from cStringIO import StringIO
from SocketServer import ThreadingMixIn
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
# For testing purposes
from SocketServer import StreamRequestHandler

import supybot.log as log
import supybot.conf as conf
import supybot.world as world
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization()

configGroup = conf.supybot.servers.http

class RequestNotHandled(Exception):
    pass

class RealSupyHTTPServer(HTTPServer):
    # TODO: make this configurable
    timeout = 0.5
    callbacks = {}
    running = False
    def hook(self, subdir, callback):
        if subdir in self.callbacks:
            raise KeyError('This subdir is already hooked.')
        else:
            self.callbacks[subdir] = callback
    def unhook(self, subdir):
        callback = self.callbacks.pop(subdir) # May raise a KeyError. We don't care.
        callback.doUnhook(self)
        return callback

class TestSupyHTTPServer(RealSupyHTTPServer):
    def __init__(self, *args, **kwargs):
        pass
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
        getattr(callback, callbackMethod)(self,
                '/' + '/'.join(self.path.split('/')[2:]),
                *args, **kwargs)

    def do_GET(self):
        self.do_X('doGet')

    def do_POST(self):
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD':'POST',
                     'CONTENT_TYPE':self.headers['Content-Type'],
                     })
        self.do_X('doPost', form=form)

    def do_HEAD(self):
        self.do_X('doHead')


    def log_message(self, format, *args):
        log.info('HTTP request: %s - %s' %
                (self.address_string(), format % args))

class SupyHTTPServerCallback:
    """This is a base class that should be overriden by any plugin that want
    to have a Web interface."""
    name = "Unnamed plugin"
    defaultResponse = _("""
    This is a default response of the Supybot HTTP server. If you see this
    message, it probably means you are developing a plugin, and you have
    neither overriden this message or defined an handler for this query.""")

    def doGet(self, handler, path, *args, **kwargs):
        handler.send_response(400)
        self.send_header('Content_type', 'text/plain')
        self.send_header('Content-Length', len(self.defaultResponse))
        self.end_headers()
        self.wfile.write(self.defaultResponse)

    doPost = doHead = doGet

    def doUnhook(self, handler):
        """Method called when unhooking this callback."""
        pass

class Supy404(SupyHTTPServerCallback):
    """A 404 Not Found error."""
    name = "Error 404"
    response = _("""
    I am a pretty clever IRC bot, but I suck at serving Web pages, particulary
    if I don't know what to serve.
    What I'm saying is you just triggered a 404 Not Found, and I am not
    trained to help you in such a case.""")
    def doGet(self, handler, path, *args, **kwargs):
        handler.send_response(404)
        self.send_header('Content_type', 'text/plain')
        self.send_header('Content-Length', len(self.response))
        self.end_headers()
        self.wfile.write(self.response)

    doPost = doHead = doGet

class SupyIndex(SupyHTTPServerCallback):
    """Displays the index of available plugins."""
    name = "index"
    defaultResponse = _("Request not handled.")
    template = """
    <html>
     <head>
      <title>""" + _('Supybot Web server index') + """</title>
     </head>
     <body>
      <p>""" + _('Here is a list of the plugins that have a Web interface:') +\
      """
      </p>
      %s
     </body>
    </html>"""
    def doGet(self, handler, path):
        plugins = [x for x in handler.server.callbacks.items()]
        if plugins == []:
            plugins = _('No plugins available.')
        else:
            plugins = '<ul><li>%s</li></ul>' % '</li><li>'.join(
                    ['<a href="/%s">%s</a>' % (x,y.name) for x,y in plugins])
        response = self.template % plugins
        handler.send_response(200)
        self.send_header('Content_type', 'text/html')
        self.send_header('Content-Length', len(response))
        self.end_headers()
        self.wfile.write(response)

httpServer = None

def startServer():
    """Starts the HTTP server. Shouldn't be called from other modules.
    The callback should be an instance of a child of SupyHTTPServerCallback."""
    global httpServer
    log.info('Starting HTTP server.')
    address = (configGroup.host(), configGroup.port())
    httpServer = SupyHTTPServer(address, SupyHTTPRequestHandler)
    Thread(target=httpServer.serve_forever, name='HTTP Server').start()

def stopServer():
    """Stops the HTTP server. Should be run only from this module or from
    when the bot is dying (ie. from supybot.world)"""
    global httpServer
    if httpServer is not None:
        log.info('Stopping HTTP server.')
        httpServer.shutdown()
        httpServer = None

if configGroup.keepAlive():
    startServer()

def hook(subdir, callback):
    """Sets a callback for a given subdir."""
    if httpServer is None:
        startServer()
    httpServer.hook(subdir, callback)

def unhook(subdir):
    """Unsets the callback assigned to the given subdir, and return it."""
    global httpServer
    assert httpServer is not None
    callback = httpServer.unhook(subdir)
    if len(httpServer.callbacks) <= 0 and not configGroup.keepAlive():
        stopServer()
