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

import fix

import sys

import sets
import os.path

###
# Directions:
#
# Boolean values should be either True or False.
###

###
# Directories.
###
logDir = 'logs'
confDir = 'conf'
dataDir = 'data'
installDir = os.path.dirname(os.path.dirname(sys.modules[__name__].__file__))
pluginDirs = [os.path.join(installDir, s) for s in ('src', 'plugins')]

###
# Files.
###
userfile = 'users.conf'
channelfile = 'channels.conf'

###
# logTimestampFormat: A format string defining how timestamps should be.  Check
#                     the Python library reference for the "time" module to see
#                     what the various format specifiers mean.
###
logTimestampFormat = '[%d-%b-%Y %H:%M:%S]'

###
# humanTimestampFormat: A format string defining how timestamps should be
#                       formatted for human consumption.  Check the Python
#                       library reference for the "time" module to see what the
#                       various format specifiers mean.
###
humanTimestampFormat = '%I:%M %p, %B %d, %Y'

###
# throttleTime: A floating point number of seconds to throttle queued messages.
#               (i.e., messages will not be sent faster than once per
#                throttleTime units.)
###
throttleTime = 1.0

###
# snarfThrottle: A floating point number of seconds to throttle snarfed URLs,
#                in order to prevent loops between two bots.
###
snarfThrottle = 10.0

###
# allowEval: True if the owner (and only the owner) should be able to eval
#            arbitrary Python code.
###
allowEval = False

###
# replyWhenNotCommand: True if you want the bot reply when someone apparently
#                      addresses him but there is no command.  Otherwise he'll
#                      just remain silent.
###
replyWhenNotCommand = True

###
# replyWithPrivateNotice: True if replies to a user in a channel should be
#                         noticed to that user instead of sent to the channel
#                         itself.
replyWithPrivateNotice = False

###
# requireRegistration: Oftentimes a plugin will want to record who added or
#                      changed or messed with it last.  Supybot's user database
#                      is an excellent way to determine who exactly someone is.
#                      You may, however, want something a little less
#                      "intrustive," so you can set this variable to False to
#                      tell such plugins that they should use the hostmask when
#                      the user isn't registered with the user database.
###
requireRegistration = False

###
# enablePipeSyntax: Supybot allows nested commands; generally, commands are
#                   nested via [square brackets].  Supybot can also use a
#                   syntax more similar to Unix pipes.  What would be (and
#                   still can be; the pipe syntax doesn't disable the bracket
#                   syntax) "bot: bar [foo]" can now by "bot: foo | bar"
#                   This variable enables such syntax.
###
enablePipeSyntax = False

###
# showOnlySyntax : Supybot normally returns the full help whenever a user
#                  misuses a command.  If this option is set to True, the bot
#                  will only return the syntax of the command (the first line
#                  of the docstring) rather than the full help.
###
showOnlySyntax = False

###
# defaultCapabilities: Capabilities allowed to everyone by default.  You almost
#                      certainly want to have !owner and !admin in here.
###
defaultCapabilities = sets.Set(['-owner', '-admin'])

###
# reply%s: Stock replies for various reasons.
###
replyError = 'An error has occurred and has been logged.'
replyNoCapability = 'You don\'t have the "%s" capability.'
replySuccess = 'The operation succeeded.'
replyIncorrectAuth = 'Your hostmasks don\'t match or your password is wrong.'
replyNoUser = 'I can\'t find that user in my database.'
replyNotRegistered = 'You must be registered to use this command.'
replyInvalidArgument = 'I can\'t send \\r, \\n, or \\0 (\\x00).'
replyRequiresPrivacy = 'That can\'t be done in a channel.'
replyEvalNotAllowed = 'You must enable conf.allowEval for that to work.'
replyPossibleBug = 'This may be a bug. If you think it is, please file a bug '\
                   'report at <http://sourceforge.net/tracker/?' \
                   'func=add&group_id=58965&atid=489447>'

###
# errorReplyPrivate: True if errors should be reported privately so as not to
#                    bother the channel.
###
errorReplyPrivate = False

###
# telnetEnable: A boolean saying whether or not to enable the telnet REPL.
#               This will allow a user with the 'owner' capability to telnet
#               into the bot and see how it's working internally.  A lifesaver
#               for development.
###
telnetEnable = False
telnetPort = 31337

###
# poll: the length of a polling term.
#       If asyncore drivers are all you're using, feel free to make
#       this arbitrarily large -- be warned, however, that all other
#       drivers are just sitting around while asyncore waits during
#       this poll period (including the schedule).  It'll take more
#       CPU, but you probably don't want to set this more than 0.01
#       when you've got non-asyncore drivers to worry about.
###
poll = 1

###
# maxHistory: Maximum number of messages kept in an Irc object's state.
###
maxHistory = 1000

###
# pingInterval: Number of seconds between PINGs to the server.
#               0 means not to ping the server.
###
pingInterval = 120

###
# nickmods: List of ways to 'spice up' a nick so the bot doesn't run out of
#           nicks if all his normal ones are taken.
###
nickmods = ['%s^', '^%s^', '__%s__', '%s_', '%s__', '__%s', '^^%s^^', '{%s}',
            '[%s]', '][%s][', '}{%s}{', '}{}%s', '^_^%s', '%s^_^', '^_^%s^_^']

###
# defaultAllow: Are commands allowed by default?
###
defaultAllow = True

###
# defaultIgnore: True if users should be ignored by default.
#                It's a really easy way to make sure that people who want to
#                talk to the bot register first.  (Of course, they can't
#                register if they're ignored.  We'll work on that.)
###
defaultIgnore = False

###
# ignores: Hostmasks to ignore.
###
ignores = []

###
# prefixChars: A string of chars that are valid prefixes to address the bot.
###
prefixChars = '@'

###
# detailedTracebacks: A boolean describing whether or not the bot will give
#                     *extremely* detailed tracebacks.  Be cautioned, this eats
#                     a lot of log file space.
###
detailedTracebacks = True

###
# driverModule: A string that is the module where the default driver for the
#               bot will be found.
###
driverModule = 'socketDrivers'
#driverModule = 'asyncoreDrivers'
#driverModule = 'twistedDrivers'

###############################
###############################
###############################
# DO NOT EDIT PAST THIS POINT #
###############################
###############################
###############################
version ='0.75.0'

commandsOnStart = []

# This is a dictionary mapping names to converter functions for use in the
# Owner.setconf command.
def mybool(s):
    """Converts a string read from the user into a bool, fuzzily."""
    if s.capitalize() == 'False' or s == '0':
        return False
    elif s.capitalize() == 'True' or s == '1':
        return True
    else:
        raise ValueError, 'invalid literal for mybool()'

def mystr(s):
    """Converts a string read from the user into a real string."""
    while s and s[0] in "'\"" and s[0] == s[-1]:
        s = s[1:-1]
    return s

types = {
    'logDir': mystr,
    'confDir': mystr,
    'dataDir': mystr,
    #'pluginDirs': (list, str),
    'userfile': mystr,
    'channelfile': mystr,
    'logTimestampFormat': mystr,
    'humanTimestampFormat': mystr,
    'throttleTime': float,
    'snarfThrottle': float,
    #'allowEval': mybool,
    'replyWhenNotCommand': mybool,
    'replyWithPrivateNotice': mybool,
    'requireRegistration': mybool,
    'enablePipeSyntax': mybool,
    'replyError': mystr,
    'replyNoCapability': mystr,
    'replySuccess': mystr,
    'replyIncorrectAuth': mystr,
    'replyNoUser': mystr,
    'replyNotRegistered': mystr,
    'replyInvalidArgument': mystr,
    'replyRequiresPrivacy': mystr,
    'replyEvalNotAllowed': mystr,
    'errorReplyPrivate': mybool,
    #'telnetEnable': mybool,
    #'telnetPort': int,
    'poll': float,
    #'maxHistory': int,
    'pingInterval': float,
    #'nickmods': (list, str),
    'defaultAllow': mybool,
    'defaultIgnore': mybool,
    #'ignores': (list, str),
    'prefixChars': mystr,
    'detailedTracebacks': mybool,
    'driverModule': mystr,
    'showOnlySyntax': mybool,
}


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
