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
Miscellaneous commands.
"""

import os
import pprint

import conf
import world
import debug
import privmsgs
import callbacks

class MiscCommands(callbacks.Privmsg):
    def list(self, irc, msg, args):
        """[<module name>]

        Lists the commands available in the given module.  If no module is
        given, lists the public modules available.
        """
        name = privmsgs.getArgs(args, needed=0, optional=1)
        name = name.lower()
        if not name:
            names = [cb.name() for cb in irc.callbacks
                     if hasattr(cb, 'public') and cb.public]
            names.sort()
            irc.reply(msg, ', '.join(names))
        else:
            for cb in irc.callbacks:
                cls = cb.__class__
                if cb.name().lower().startswith(name) and \
                       not issubclass(cls, callbacks.PrivmsgRegexp) and \
                       issubclass(cls, callbacks.Privmsg):
                    commands = [x for x in dir(cls)
                                if cb.isCommand(x) and \
                                hasattr(getattr(cb, x), '__doc__')]
                    commands.sort()
                    irc.reply(msg, ', '.join(commands))
                    return
            irc.error(msg, 'There is no module named %s, ' \
                                 'or that module has no commands.' % name)

    def help(self, irc, msg, args):
        """<command>

        Gives the help for a specific command.  To find commands,
        use the 'list' command to go see the commands offered by a module.
        The 'list' command by itself will show you what modules have commands.
        """
        command = privmsgs.getArgs(args, needed=0, optional=1)
        if not command:
            command = 'help'
        command = callbacks.canonicalName(command)
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__') and method.__doc__ is not None:
                doclines = method.__doc__.splitlines()
                help = doclines.pop(0)
                if doclines:
                    s = '%s %s (for more help use the morehelp command)'
                else:
                    s = '%s %s'
                irc.reply(msg, s % (command, help))
            else:
                irc.reply(msg, 'That command exists, but has no help.')
        else:
            for cb in irc.callbacks:
                if cb.name() == command:
                    if hasattr(cb, '__doc__'):
                        doclines = cb.__doc__.splitlines()
                        help = ' '.join(map(str.strip, doclines))
                        irc.reply(msg, help)
                    else:
                        irc.error(msg, 'That callback has no help.')
            else:
                irc.error(msg, 'There is no such command.')

    def morehelp(self, irc, msg, args):
        """<command>

        This command gives more help than is provided by the simple argument
        list given by the command 'help'.
        """
        command = callbacks.canonicalName(privmsgs.getArgs(args))
        cb = irc.findCallback(command)
        if cb:
            method = getattr(cb, command)
            if hasattr(method, '__doc__'):
                doclines = method.__doc__.splitlines()
                simplehelp = doclines.pop(0)
                if doclines:
                    doclines = filter(None, doclines)
                    doclines = map(str.strip, doclines)
                    help = ' '.join(doclines)
                    irc.reply(msg, help)
                else:
                    irc.reply(msg, 'That command has no more help.  '\
                                   'The original help is this: %s %s' % \
                                   (command, simplehelp))
            else:
                irc.error(msg, 'That command has no help at all.')
        
    def bug(self, irc, msg, args):
        """takes no arguments

        Log a recent bug.  A revent (long) history of the messages received
        will be logged, so don't abuse this command or you'll have an upset
        admin to deal with.
        """
        debug.msg(pprint.pformat(irc.state.history), 'normal')
        irc.reply(msg, conf.replySuccess)

    def version(self, irc, msg, args):
        """takes no arguments

        Returns the version of the current bot.
        """
        irc.reply(msg, world.version)

    def source(self, irc, msg, args):
        """takes no arguments

        Returns a URL saying where to get SupyBot.
        """
        irc.reply(msg, 'My source is at http://www.sf.net/projects/supybot/')

    def logfilesize(self, irc, msg, args):
        """[<logfile>]

        Returns the size of the various logfiles in use.  If given a specific
        logfile, returns only the size of that logfile.
        """
        filename = privmsgs.getArgs(args, needed=0, optional=1)
        if filename:
            if not filename.endswith('.log'):
                irc.error(msg, 'That filename doesn\'t appear to be a log.')
                return
            filenames = [filename]
        else:
            filenames = os.listdir(conf.logDir)
        result = []
        for file in filenames:
            if file.endswith('.log'):
                stats = os.stat(os.path.join(conf.logDir, file))
                result.append((file, str(stats.st_size)))
        irc.reply(msg, ', '.join(map(': '.join, result)))

    def getprefixchar(self, irc, msg, args):
        """takes no arguments

        Returns the prefix character(s) the bot is currently using.
        """
        irc.reply(msg, repr(conf.prefixChars))

    def moduleof(self, irc, msg, args):
        """<command>

        Returns the module <command> is in.
        """
        command = privmsgs.getArgs(args)
        Class = irc.findCallback(command)
        if Class is not None:
            irc.reply(msg, Class.name())
        else:
            irc.error(msg, 'There is no such command %s' % command)


Class = MiscCommands

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
