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

"""
Allows 'aliases' for other commands.

Commands include:
  alias
  unalias
  freeze
  unfreeze
"""

from baseplugin import *

import new
import copy
import traceback

import conf
import debug
import privmsgs
import callbacks

def configure(onStart, afterConnect, advanced):
    # This will be called by setup.py to configure this module.  onStart and
    # afterConnect are both lists.  Append to onStart the commands you would
    # like to be run when the bot is started; append to afterConnect the
    # commands you would like to be run when the bot has finished connecting.
    from questions import expect, anything, something, yn
    onStart.append('load Alias')

class RecursiveAlias(Exception):
    pass

def findString(s, args):
    n = 0
    for elt in args:
        if type(elt) == list:
            n += findString(s, elt)
        elif elt == s:
            n += 1
    return n

def findDollars(args, soFar=None, L=None):
    if soFar is None:
        soFar = []
    if L is None:
        L = []
    for (i, elt) in enumerate(args):
        if type(elt) == list:
            nextSoFar = soFar[:]
            nextSoFar.append(i)
            findDollars(elt, soFar=nextSoFar, L=L)
        if len(elt) >= 2:
            if elt[0] == '$' and elt[1:].isdigit():
                mySoFar = soFar[:]
                mySoFar.append(i)
                L.append((mySoFar, elt))
    return L

def replaceDollars(dollars, aliasArgs, realArgs):
    for (indexes, dollar) in dollars:
        L = aliasArgs
        for i in indexes[:-1]:
            L = L[i]
        L[indexes[-1]] = realArgs[int(dollar[1:])-1]

def makeNewAlias(name, alias, aliasArgs):
    if findString(name, aliasArgs):
        raise RecursiveAlias
    dollars = findDollars(aliasArgs)
    numDollars = len(dollars)
    def f(self, irc, msg, args):
        #debug.printf('%s being called' % name)
        realArgs = privmsgs.getArgs(args, needed=numDollars)
        myArgs = copy.deepcopy(aliasArgs)
        if dollars:
            replaceDollars(dollars, myArgs, realArgs)
        else:
            myArgs.extend(args)
        self.Proxy(irc, msg, myArgs)
    f.__doc__ = '<an alias, arguments unknown>\n\nAlias for %r' % alias
    #f = new.function(f.func_code, f.func_globals, name)
    return f


class Alias(callbacks.Privmsg):
    def __init__(self):
        callbacks.Privmsg.__init__(self)
        self.frozen = set()
        
    def freeze(self, irc, msg, args):
        """<alias>

        'Freezes' an alias so that no one else can change it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.frozen.add(name)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There is no such alias.')
    freeze = privmsgs.checkCapability(freeze, 'admin')

    def unfreeze(self, irc, msg, args):
        """<alias>

        'Unfreezes' an alias so that people can define new aliases over it.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            self.frozen.discard(name)
            irc.reply(msg, conf.replySuccess)
        else:
            irc.error(msg, 'There is no such alias.')
    unfreeze = privmsgs.checkCapability(unfreeze, 'admin')
    
    def alias(self, irc, msg, args):
        """<name> <alias commands>

        Defines an alias <name> for the commands <commands>.  The <commands>
        should be in the standard [command argument [nestedcommand argument]]
        format.  Underscores can be used to represent arguments to the alias
        itself; for instance ...
        """
        try:
            (name, alias) = privmsgs.getArgs(args, needed=2)
            name = callbacks.canonicalName(name)
            cb = irc.findCallback(name)
            if cb is not None and cb != self:
                irc.error(msg, 'A command with that name already exists.')
                return
            if name in self.frozen:
                irc.error(msg, 'That alias is frozen.')
                return
            args = callbacks.tokenize(alias)
            try:
                f = makeNewAlias(name, alias, args)
            except RecursiveAlias:
                irc.error(msg, 'You can\'t define a recursive alias.')
            #debug.printf('setting attribute')
            setattr(self.__class__, name, f)
            irc.reply(msg, conf.replySuccess)
        except Exception, e:
            debug.recoverableException()
            print debug.exnToString(e)
        except:
            print 'exception raised'
            

    def unalias(self, irc, msg, args):
        """<name>

        Removes the given alias, if unfrozen.
        """
        name = privmsgs.getArgs(args)
        name = callbacks.canonicalName(name)
        if hasattr(self, name) and self.isCommand(name):
            if name not in self.frozen:
                delattr(self.__class__, name)
                irc.reply(msg, conf.replySuccess)
            else:
                irc.error(msg, 'That alias is frozen.')
        else:
            irc.error(msg, 'There is no such alias.')
        
        


Class = Alias

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
