#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

__revision__ = "$Id$"

import os

import conf
import utils
import ircdb
import ircutils
import privmsgs
import callbacks

class Dictionary(object):
    """This is a dictionary to handle configuration for individual channels,
    including a default configuration for channels that haven't modified their
    configuration from the default.
    """
    def __init__(self, seq):
        self.helps = {}
        self.types = {}
        self.defaults = {}
        self.originalNames = {}
        self.unparsedValues = {}
        self.channels = ircutils.IrcDict()
        for (name, type, default, help) in seq:
            if ',' in name:
                raise ValueError, 'There can be no commas in the name.'
            original = name
            name = callbacks.canonicalName(name)
            self.originalNames[name] = original
            self.helps[name] = utils.normalizeWhitespace(help)
            self.types[name] = type
            self.defaults[name] = default

    def get(self, name, channel=None):
        name = callbacks.canonicalName(name)
        if channel is not None:
            try:
                return self.channels[channel][name]
            except KeyError:
                return self.defaults[name]
        else:
            return self.defaults[name]

    def set(self, name, value, channel=None):
        name = callbacks.canonicalName(name)
        if name not in self.originalNames:
            raise KeyError, name
        if ',' in name:
            raise ValueError, 'There can be no commas in the name.'
        self.unparsedValues[(channel, name)] = value
        if channel is not None:
            d = self.channels.setdefault(channel, {})
            d[name] = self.types[name](value)
        else:
            self.defaults[name] = self.types[name](value)

    def help(self, name):
        return self.helps[callbacks.canonicalName(name)]

    def names(self):
        L = self.originalNames.values()
        L.sort()
        return L

class Error(TypeError):
    pass

def BoolType(s):
    s = s.lower()
    if s in ('true', 'enable', 'on'):
        return True
    elif s in ('false', 'disable', 'off'):
        return False
    else:
        s = 'Value must be one of on/off/true/false/enable/disable.'
        raise Error, s

def StrType(s):
    if s and s[0] not in '\'"' and s[-1] not in '\'"':
        s = repr(s)
    try:
        v = utils.safeEval(s)
        if type(v) is not str:
            raise ValueError
    except ValueError: # This catches the utils.safeEval(s) errors too.
        raise Error, 'Value must be a string.'
    return v

def IntType(s):
    try:
        return int(s)
    except ValueError:
        raise Error, 'Value must be an int.'

class Mixin(object):
    """A mixin class to provide a "config" command that can be consistent
    across all plugins, in order to unify the configuration for each plugin.

    Plugins subclassing this should have a "configurables" attribute which is
    a ConfigurableDictionary initialized with a list of 4-tuples of
    (name, type, default, help).  Name is the string name of the config
    variable; type is a function taking a string and returning some value of
    the type the variable is supposed to be; default is the default value the
    variable should take on; help is a string that'll be returned to describe
    the purpose of the config variable.
    """
    def __init__(self):
        className = self.__class__.__name__
        self.filename = os.path.join(conf.confDir, '%s-configurable'%className)
        if os.path.exists(self.filename):
            fd = file(self.filename)
            for line in fd:
                line = line.rstrip()
                (channel, name, value) = line.split(',', 2)
                if channel == 'default':
                    channel = None
                try:
                    # The eval here is to turn from "'foo'" to 'foo'.
                    self.configurables.set(name, eval(value), channel)
                except Error, e:
                    s = 'Couldn\'t read configurable from file: %s'
                    self.log.warning(s, e)
                except KeyError, e:
                    s = 'Configurable variable %s doesn\'t exist anymore.'
                    self.log.warning(s, name)

    def die(self):
        fd = file(self.filename, 'w')
        L = self.configurables.unparsedValues.items()
        L.sort()
        for ((channel, name), value) in L:
            if channel is None:
                channel = 'default'
            name = self.configurables.originalNames[name]
            fd.write('%s,%s,%r\n' % (channel, name, value))
        fd.close()

    def config(self, irc, msg, args):
        """[<channel>] [<name>] [<value>]

        Sets the value of config variable <name> to <value> on <channel>.  If
        <name> is given but <value> is not, returns the help and current value
        for <name>.  If neither <name> nor <value> is given, returns the valid
        config variables for this plugin.  <channel> is only necessary if the
        message isn't sent in the channel itself.
        """
        try:
            channel = privmsgs.getChannel(msg, args)
            capability = ircdb.makeChannelCapability(channel, 'op')
        except callbacks.ArgumentError:
            raise
        except callbacks.Error:
            channel = None
            capability = 'admin'
        if not ircdb.checkCapability(msg.prefix, capability):
            irc.error(msg, conf.replyNoCapability % capability)
            return
        (name, value) = privmsgs.getArgs(args, required=0, optional=2)
        if not name:
            irc.reply(msg, utils.commaAndify(self.configurables.names()))
            return
        try:
            if not value:
                help = self.configurables.help(name)
                value = self.configurables.get(name, channel=channel)
                s = '%s: %s  (Current value: %r)' % (name, help, value)
                irc.reply(msg, s)
                return
            try:
                self.configurables.set(name, value, channel)
                irc.reply(msg, conf.replySuccess)
            except Error, e:
                irc.error(msg, str(e))
        except KeyError:
            irc.error(msg, 'There is no config variable %r' % name)
        



# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

