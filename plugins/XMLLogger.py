#!/usr/bin/python

###
# Copyright (c) 2004, Jeremiah Fincher
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
Logs all the messages the bot receives to XML.
"""

__revision__ = "$Id$"
__author__ = 'Jeremy Fincher (jemfinch) <jemfinch@users.sf.net>'

import plugins

import os.path

import conf
import utils
import world
import ircmsgs
import privmsgs
import registry
import callbacks

conf.registerPlugin('XMLLogger')
conf.registerGlobalValue(conf.supybot.plugins.XMLLogger, 'prettyPrint',
    registry.Boolean(False, """Determines whether the XML messages should be
    pretty-printed in the log file, or just written one per line."""))
conf.registerGlobalValue(conf.supybot.plugins.XMLLogger, 'includeTime',
    registry.Boolean(True, """Determines whether the time the message was
    converted to XML should be logged as well; this should be relatively close
    to the time at which the message was received."""))

def configure(advanced):
    # This will be called by setup.py to configure this module.  Advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from questions import expect, anything, something, yn
    conf.registerPlugin('XMLLogger', True)


class XMLLogger(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        logDir = conf.supybot.directories.log()
        self.fd = file(os.path.join(logDir, 'xml.log'), 'a')
        self.boundFlushMethod = self.fd.flush
        world.flushers.append(self.boundFlushMethod)

    def die(self):
        if self.boundFlushMethod in world.flushers:
            world.flushers.remove(self.boundFlushMethod)
        else:
            if not world.dying:
                self.log.warning('My flusher wasn\'t in world.flushers: %r',
                                 world.flushers)
        self.fd.close()
        
    def writeMsg(self, msg):
        pretty = self.registryValue('prettyPrint')
        includeTime = self.registryValue('includeTime')
        s = ircmsgs.toXml(msg, pretty=pretty, includeTime=includeTime)
        self.fd.write(s)

    def inFilter(self, irc, msg):
        self.writeMsg(msg)
        return msg

    def outFilter(self, irc, msg):
        self.writeMsg(msg)
        return msg

Class = XMLLogger

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
