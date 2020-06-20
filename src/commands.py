###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2009-2010,2015, James McCoy
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
Includes wrappers for commands.
"""

import time
import getopt
import inspect
import threading
import multiprocessing #python2.6 or later!

try:
    import resource
except ImportError: # Windows!
    resource = None

from . import callbacks, conf, ircdb, ircmsgs, ircutils, log, \
        utils, world
from .utils import minisix
from .i18n import PluginInternationalization, internationalizeDocstring
_ = PluginInternationalization()

###
# Non-arg wrappers -- these just change the behavior of a command without
# changing the arguments given to it.
###

# Thread has to be a non-arg wrapper because by the time we're parsing and
# validating arguments, we're inside the function we'd want to thread.
def thread(f):
    """Makes sure a command spawns a thread when called."""
    def newf(self, irc, msg, args, *L, **kwargs):
        if world.isMainThread():
            targetArgs = (self.callingCommand, irc, msg, args) + tuple(L)
            t = callbacks.CommandThread(target=self._callCommand,
                                        args=targetArgs, kwargs=kwargs)
            t.start()
        else:
            f(self, irc, msg, args, *L, **kwargs)
    return utils.python.changeFunctionName(newf, f.__name__, f.__doc__)

class ProcessTimeoutError(Exception):
    """Gets raised when a process is killed due to timeout."""
    pass

def _rlimit_min(a, b):
    if a == resource.RLIM_INFINITY:
        return b
    elif b == resource.RLIM_INFINITY:
        return a
    else:
        return min(soft, heap_size)

def process(f, *args, **kwargs):
    """Runs a function <f> in a subprocess.
    
    Several extra keyword arguments can be supplied. 
    <pn>, the pluginname, and <cn>, the command name, are strings used to
    create the process name, for identification purposes.
    <timeout>, if supplied, limits the length of execution of target 
    function to <timeout> seconds.
    <heap_size>, if supplied, limits the memory used by the target
    function."""
    timeout = kwargs.pop('timeout', None)
    heap_size = kwargs.pop('heap_size', None)
    if resource and heap_size is None:
        heap_size = resource.RLIM_INFINITY

    if world.disableMultiprocessing:
        pn = kwargs.pop('pn', 'Unknown')
        cn = kwargs.pop('cn', 'unknown')
        try:
            return f(*args, **kwargs)
        except Exception as e:
            raise e
    
    try:
        q = multiprocessing.Queue()
    except OSError:
        log.error('Using multiprocessing.Queue raised an OSError.\n'
                'This is probably caused by your system denying semaphore\n'
                'usage. You should run these two commands:\n'
                '\tsudo rmdir /dev/shm\n'
                '\tsudo ln -Tsf /{run,dev}/shm\n'
                '(See https://github.com/travis-ci/travis-core/issues/187\n'
                'for more information about this bug.)\n')
        raise
    def newf(f, q, *args, **kwargs):
        if resource:
            rsrc = resource.RLIMIT_DATA
            (soft, hard) = resource.getrlimit(rsrc)
            soft = _rlimit_min(soft, heap_size)
            hard = _rlimit_min(hard, heap_size)
            resource.setrlimit(rsrc, (soft, hard))
        try:
            r = f(*args, **kwargs)
            q.put([False, r])
        except Exception as e:
            q.put([True, e])
    targetArgs = (f, q,) + args
    p = callbacks.CommandProcess(target=newf,
                                args=targetArgs, kwargs=kwargs)
    try:
        p.start()
    except OSError as e:
        log.error(
            'Failed to start a subprocess because of the following error: %s '
            'This might be caused by the way Limnoria is demonized / run in '
            'the background. Instead, try running it as a service '
            '<https://docs.limnoria.net/use/supybot-botchk.html>, '
            'use the --daemon option, or run it in screen/tmux.',
            e)
        raise
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        q.close()
        raise ProcessTimeoutError("%s aborted due to timeout." % (p.name,))
    try:
        raised, v = q.get(block=False)
    except minisix.queue.Empty:
        return None
    finally:
        q.close()

    if raised:
        raise v
    else:
        return v

def regexp_wrapper(s, reobj, timeout, plugin_name, fcn_name):
    '''A convenient wrapper to stuff regexp search queries through a subprocess.

    This is used because specially-crafted regexps can use exponential time
    and hang the bot.'''
    def re_bool(s, reobj):
        """Since we can't enqueue match objects into the multiprocessing queue,
        we'll just wrap the function to return bools."""
        if reobj.search(s) is not None:
            return True
        else:
            return False
    try:
        v = process(re_bool, s, reobj, timeout=timeout, pn=plugin_name, cn=fcn_name)
        return v
    except ProcessTimeoutError:
        return None

class UrlSnarfThread(world.SupyThread):
    def __init__(self, *args, **kwargs):
        assert 'url' in kwargs
        kwargs['name'] = 'Thread #%s (for snarfing %s)' % \
                         (world.threadsSpawned, kwargs.pop('url'))
        super(UrlSnarfThread, self).__init__(*args, **kwargs)
        self.setDaemon(True)

    def run(self):
        try:
            super(UrlSnarfThread, self).run()
        except utils.web.Error as e:
            log.debug('Exception in urlSnarfer: %s', utils.exnToString(e))

class SnarfQueue(ircutils.FloodQueue):
    timeout = conf.supybot.snarfThrottle
    def key(self, channel):
        return channel

_snarfed = SnarfQueue()

class SnarfIrc(object):
    def __init__(self, irc, channel, url):
        self.irc = irc
        self.url = url
        self.channel = channel

    def __getattr__(self, attr):
        return getattr(self.irc, attr)

    def reply(self, *args, **kwargs):
        _snarfed.enqueue(self.channel, self.url)
        return self.irc.reply(*args, **kwargs)

# This lock is used to serialize the calls to snarfers, so
# earlier snarfers are guaranteed to beat out later snarfers.
_snarfLock = threading.Lock()
def urlSnarfer(f):
    """Protects the snarfer from loops (with other bots) and whatnot."""
    def newf(self, irc, msg, match, *L, **kwargs):
        url = match.group(0)
        channel = msg.channel
        if not channel:
            # Don't snarf in private
            return
        if ircmsgs.isCtcp(msg) and not ircmsgs.isAction(msg):
            # Don't snarf CTCPs unless they are a /me
            return
        if ircdb.channels.getChannel(channel).lobotomized:
            self.log.debug('Not snarfing in %s: lobotomized.', channel)
            return
        if _snarfed.has(channel, url):
            self.log.info('Throttling snarf of %s in %s.', url, channel)
            return
        irc = SnarfIrc(irc, channel, url)
        def doSnarf():
            _snarfLock.acquire()
            try:
                # This has to be *after* we've acquired the lock so we can be
                # sure that all previous urlSnarfers have already run to
                # completion.
                if msg.repliedTo:
                    self.log.debug('Not snarfing, msg is already repliedTo.')
                    return
                f(self, irc, msg, match, *L, **kwargs)
            finally:
                _snarfLock.release()
        if threading.currentThread() is not world.mainThread:
            doSnarf()
        else:
            L = list(L)
            t = UrlSnarfThread(target=doSnarf, url=url)
            t.start()
    newf = utils.python.changeFunctionName(newf, f.__name__, f.__doc__)
    return newf


###
# Converters, which take irc, msg, args, and a state object, and build up the
# validated and converted args for the method in state.args.
###

# This is just so we can centralize this, since it may change.
def _int(s):
    base = 10
    if s.startswith('0x'):
        base = 16
        s = s[2:]
    elif s.startswith('0b'):
        base = 2
        s = s[2:]
    elif s.startswith('0') and len(s) > 1:
        base = 8
        s = s[1:]
    try:
        return int(s, base)
    except ValueError:
        if base == 10 and '.' not in s:
            try:
                return int(float(s))
            except OverflowError:
                raise ValueError('I don\'t understand numbers that large.')
        else:
            raise

def getInt(irc, msg, args, state, type=_('integer'), p=None):
    try:
        i = _int(args[0])
        if p is not None:
            if not p(i):
                state.errorInvalid(type, args[0])
        state.args.append(i)
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

def getNonInt(irc, msg, args, state, type=_('non-integer value')):
    try:
        _int(args[0])
        state.errorInvalid(type, args[0])
    except ValueError:
        state.args.append(args.pop(0))

def getLong(irc, msg, args, state, type='long'):
    getInt(irc, msg, args, state, type)
    state.args[-1] = minisix.long(state.args[-1])

def getFloat(irc, msg, args, state, type=_('floating point number')):
    try:
        state.args.append(float(args[0]))
        del args[0]
    except ValueError:
        state.errorInvalid(type, args[0])

def getPositiveInt(irc, msg, args, state, *L):
    getInt(irc, msg, args, state,
           p=lambda i: i>0, type=_('positive integer'), *L)

def getNonNegativeInt(irc, msg, args, state, *L):
    getInt(irc, msg, args, state,
            p=lambda i: i>=0, type=_('non-negative integer'), *L)

def getIndex(irc, msg, args, state):
    getInt(irc, msg, args, state, type=_('index'))
    if state.args[-1] > 0:
        state.args[-1] -= 1

def getId(irc, msg, args, state, kind=None):
    type = 'id'
    if kind is not None and not kind.endswith('id'):
        type = kind + ' id'
    original = args[0]
    try:
        args[0] = args[0].lstrip('#')
        getInt(irc, msg, args, state, type=type)
    except Exception:
        args[0] = original
        raise

def getExpiry(irc, msg, args, state):
    now = int(time.time())
    try:
        expires = _int(args[0])
        if expires:
            expires += now
        state.args.append(expires)
        del args[0]
    except ValueError:
        state.errorInvalid(_('number of seconds'), args[0])

def getBoolean(irc, msg, args, state):
    try:
        state.args.append(utils.str.toBool(args[0]))
        del args[0]
    except ValueError:
        state.errorInvalid(_('boolean'), args[0])

def getNetworkIrc(irc, msg, args, state, errorIfNoMatch=False):
    if args:
        for otherIrc in world.ircs:
            if otherIrc.network.lower() == args[0].lower():
                state.args.append(otherIrc)
                del args[0]
                return
    if errorIfNoMatch:
        raise callbacks.ArgumentError
    else:
        state.args.append(irc)

def getHaveVoice(irc, msg, args, state, action=_('do that')):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not even in %s.') % state.channel, Raise=True)
    if not irc.state.channels[state.channel].isVoice(irc.nick):
        state.error(_('I need to be voiced to %s.') % action, Raise=True)

def getHaveVoicePlus(irc, msg, args, state, action=_('do that')):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not even in %s.') % state.channel, Raise=True)
    if not irc.state.channels[state.channel].isVoicePlus(irc.nick):
        # isOp includes owners and protected users
        state.error(_('I need to be at least voiced to %s.') % action,
                Raise=True)

def getHaveHalfop(irc, msg, args, state, action=_('do that')):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not even in %s.') % state.channel, Raise=True)
    if not irc.state.channels[state.channel].isHalfop(irc.nick):
        state.error(_('I need to be halfopped to %s.') % action, Raise=True)

def getHaveHalfopPlus(irc, msg, args, state, action=_('do that')):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not even in %s.') % state.channel, Raise=True)
    if not irc.state.channels[state.channel].isHalfopPlus(irc.nick):
        # isOp includes owners and protected users
        state.error(_('I need to be at least halfopped to %s.') % action,
                Raise=True)

def getHaveOp(irc, msg, args, state, action=_('do that')):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not even in %s.') % state.channel, Raise=True)
    if not irc.state.channels[state.channel].isOp(irc.nick):
        state.error(_('I need to be opped to %s.') % action, Raise=True)

def validChannel(irc, msg, args, state):
    if irc.isChannel(args[0]):
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('channel'), args[0])

def getHostmask(irc, msg, args, state):
    if ircutils.isUserHostmask(args[0]) or \
            (not conf.supybot.protocols.irc.strictRfc() and
                    args[0].startswith('$')):
        state.args.append(args.pop(0))
    else:
        try:
            hostmask = irc.state.nickToHostmask(args[0])
            state.args.append(hostmask)
            del args[0]
        except KeyError:
            state.errorInvalid(_('nick or hostmask'), args[0])

def getBanmask(irc, msg, args, state):
    getHostmask(irc, msg, args, state)
    getChannel(irc, msg, args, state)
    banmaskstyle = conf.supybot.protocols.irc.banmask
    state.args[-1] = banmaskstyle.makeBanmask(state.args[-1],
            channel=state.channel)

def getUser(irc, msg, args, state):
    try:
        state.args.append(ircdb.users.getUser(msg.prefix))
    except KeyError:
        state.errorNotRegistered(Raise=True)

def getOtherUser(irc, msg, args, state):
    # Although ircdb.users.getUser could accept a hostmask, we're explicitly
    # excluding that from our interface with this check
    if ircutils.isUserHostmask(args[0]):
        state.errorNoUser(args[0])
    try:
        state.args.append(ircdb.users.getUser(args[0]))
        del args[0]
    except KeyError:
        try:
            getHostmask(irc, msg, [args[0]], state)
            hostmask = state.args.pop()
            state.args.append(ircdb.users.getUser(hostmask))
            del args[0]
        except (KeyError, callbacks.Error):
            state.errorNoUser(name=args[0])

def _getRe(f):
    def get(irc, msg, args, state, convert=True):
        original = args[:]
        s = args.pop(0)
        def isRe(s):
            try:
                f(s)
                return True
            except ValueError:
                return False
        try:
            while len(s) < 512 and not isRe(s):
                s += ' ' + args.pop(0)
            if len(s) < 512:
                if convert:
                    state.args.append(f(s))
                else:
                    state.args.append(s)
            else:
                raise ValueError
        except (ValueError, IndexError):
            args[:] = original
            state.errorInvalid(_('regular expression'), s)
    return get

getMatcher = _getRe(utils.str.perlReToPythonRe)
getMatcherMany = _getRe(utils.str.perlReToFindall)
getReplacer = _getRe(utils.str.perlReToReplacer)

def getNick(irc, msg, args, state):
    if ircutils.isNick(args[0], conf.supybot.protocols.irc.strictRfc()):
        if 'nicklen' in irc.state.supported:
            if len(args[0]) > irc.state.supported['nicklen']:
                state.errorInvalid(_('nick'), args[0],
                                 _('That nick is too long for this server.'))
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('nick'), args[0])

def getSeenNick(irc, msg, args, state, errmsg=None):
    try:
        irc.state.nickToHostmask(args[0])
        state.args.append(args.pop(0))
    except KeyError:
        if errmsg is None:
            errmsg = _('I haven\'t seen %s.') % args[0]
        state.error(errmsg, Raise=True)

def getChannel(irc, msg, args, state):
    if state.channel:
        return
    if args and irc.isChannel(args[0]):
        channel = args.pop(0)
    elif msg.channel:
        channel = msg.channel
    else:
        state.log.debug('Raising ArgumentError because there is no channel.')
        raise callbacks.ArgumentError
    state.channel = channel
    state.args.append(channel)

def getChannels(irc, msg, args, state):
    if args and all(map(irc.isChannel, args[0].split(','))):
        channels = args.pop(0).split(',')
    elif msg.channel:
        channels = [msg.channel]
    else:
        state.log.debug('Raising ArgumentError because there is no channel.')
        raise callbacks.ArgumentError
    state.args.append(channels)

def getChannelDb(irc, msg, args, state, **kwargs):
    channelSpecific = conf.supybot.databases.plugins.channelSpecific
    try:
        getChannel(irc, msg, args, state, **kwargs)
        channel = channelSpecific.getChannelLink(state.channel)
        state.args[-1] = channel
    except (callbacks.ArgumentError, IndexError):
        if channelSpecific():
            raise
        channel = channelSpecific.link()
        if not conf.get(channelSpecific.link.allow, channel):
            log.warning('channelSpecific.link is globally set to %s, but '
                        '%s disallowed linking to its db.', channel, channel)
            raise
        else:
            channel = channelSpecific.getChannelLink(channel)
            state.args.append(channel)

def inChannel(irc, msg, args, state):
    getChannel(irc, msg, args, state)
    if state.channel not in irc.state.channels:
        state.error(_('I\'m not in %s.') % state.channel, Raise=True)

def onlyInChannel(irc, msg, args, state):
    if not (msg.channel and msg.channel in irc.state.channels):
        state.error(_('This command may only be given in a channel that I am '
                    'in.'), Raise=True)
    else:
        state.channel = msg.channel
        state.args.append(state.channel)

def callerInGivenChannel(irc, msg, args, state):
    channel = args[0]
    if irc.isChannel(channel):
        if channel in irc.state.channels:
            if msg.nick in irc.state.channels[channel].users:
                state.args.append(args.pop(0))
            else:
                state.error(_('You must be in %s.') % channel, Raise=True)
        else:
            state.error(_('I\'m not in %s.') % channel, Raise=True)
    else:
        state.errorInvalid(_('channel'), args[0])

def nickInChannel(irc, msg, args, state):
    originalArgs = state.args[:]
    inChannel(irc, msg, args, state)
    state.args = originalArgs
    if args[0] not in irc.state.channels[state.channel].users:
        state.error(_('%s is not in %s.') % (args[0], state.channel), Raise=True)
    state.args.append(args.pop(0))

def getChannelOrNone(irc, msg, args, state):
    try:
        getChannel(irc, msg, args, state)
    except callbacks.ArgumentError:
        state.args.append(None)

def getChannelOrGlobal(irc, msg, args, state):
    if args and args[0] == 'global':
        channel = args.pop(0)
        channel = 'global'
    elif args and irc.isChannel(args[0]):
        channel = args.pop(0)
        state.channel = channel
    elif msg.channel:
        channel = msg.channel
        state.channel = channel
    else:
        state.log.debug('Raising ArgumentError because there is no channel.')
        raise callbacks.ArgumentError
    state.args.append(channel)

def checkChannelCapability(irc, msg, args, state, cap):
    getChannel(irc, msg, args, state)
    cap = ircdb.canonicalCapability(cap)
    cap = ircdb.makeChannelCapability(state.channel, cap)
    if not ircdb.checkCapability(msg.prefix, cap):
        state.errorNoCapability(cap, Raise=True)

def getOp(irc, msg, args, state):
    checkChannelCapability(irc, msg, args, state, 'op')

def getHalfop(irc, msg, args, state):
    checkChannelCapability(irc, msg, args, state, 'halfop')

def getVoice(irc, msg, args, state):
    checkChannelCapability(irc, msg, args, state, 'voice')

def getLowered(irc, msg, args, state):
    state.args.append(ircutils.toLower(args.pop(0)))

def getSomething(irc, msg, args, state, errorMsg=None, p=None):
    if p is None:
        p = lambda _: True
    if not args[0] or not p(args[0]):
        if errorMsg is None:
            errorMsg = _('You must not give the empty string as an argument.')
        state.error(errorMsg, Raise=True)
    else:
        state.args.append(args.pop(0))

def getSomethingNoSpaces(irc, msg, args, state, *L):
    def p(s):
        return len(s.split(None, 1)) == 1
    L = L or [_('You must not give a string containing spaces as an argument.')]
    getSomething(irc, msg, args, state, p=p, *L)

def private(irc, msg, args, state):
    if msg.channel:
        state.errorRequiresPrivacy(Raise=True)

def public(irc, msg, args, state, errmsg=None):
    if not msg.channel:
        if errmsg is None:
            errmsg = _('This message must be sent in a channel.')
        state.error(errmsg, Raise=True)

def checkCapability(irc, msg, args, state, cap):
    cap = ircdb.canonicalCapability(cap)
    if not ircdb.checkCapability(msg.prefix, cap):
        state.errorNoCapability(cap, Raise=True)

def checkCapabilityButIgnoreOwner(irc, msg, args, state, cap):
    cap = ircdb.canonicalCapability(cap)
    if not ircdb.checkCapability(msg.prefix, cap, ignoreOwner=True):
        state.errorNoCapability(cap, Raise=True)

def owner(irc, msg, args, state):
    checkCapability(irc, msg, args, state, 'owner')

def admin(irc, msg, args, state):
    checkCapability(irc, msg, args, state, 'admin')

def anything(irc, msg, args, state):
    state.args.append(args.pop(0))

def getGlob(irc, msg, args, state):
    glob = args.pop(0)
    if '*' not in glob and '?' not in glob:
        glob = '*%s*' % glob
    state.args.append(glob)

def getUrl(irc, msg, args, state):
    if utils.web.urlRe.match(args[0]):
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('url'), args[0])

def getEmail(irc, msg, args, state):
    if utils.net.emailRe.match(args[0]):
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('email'), args[0])

def getHttpUrl(irc, msg, args, state):
    if utils.web.httpUrlRe.match(args[0]):
        state.args.append(args.pop(0))
    elif utils.web.httpUrlRe.match('http://' + args[0]):
        state.args.append('http://' + args.pop(0))
    else:
        state.errorInvalid(_('http url'), args[0])

def getNow(irc, msg, args, state):
    state.args.append(int(time.time()))

def getCommandName(irc, msg, args, state):
    if ' ' in args[0]:
        state.errorInvalid(_('command name'), args[0])
    else:
        state.args.append(callbacks.canonicalName(args.pop(0)))

def getIp(irc, msg, args, state):
    if utils.net.isIP(args[0]):
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('ip'), args[0])

def getLetter(irc, msg, args, state):
    if len(args[0]) == 1:
        state.args.append(args.pop(0))
    else:
        state.errorInvalid(_('letter'), args[0])

def getMatch(irc, msg, args, state, regexp, errmsg):
    m = regexp.search(args[0])
    if m is not None:
        state.args.append(m)
        del args[0]
    else:
        state.error(errmsg, Raise=True)

def getLiteral(irc, msg, args, state, literals, errmsg=None):
    # ??? Should we allow abbreviations?
    if isinstance(literals, minisix.string_types):
        literals = (literals,)
    abbrevs = utils.abbrev(literals)
    if args[0] in abbrevs:
        state.args.append(abbrevs[args.pop(0)])
    elif errmsg is not None:
        state.error(errmsg, Raise=True)
    else:
        raise callbacks.ArgumentError

def getTo(irc, msg, args, state):
    if args[0].lower() == 'to':
        args.pop(0)

def getPlugin(irc, msg, args, state, require=True):
    cb = irc.getCallback(args[0])
    if cb is not None:
        state.args.append(cb)
        del args[0]
    elif require:
        state.errorInvalid(_('plugin'), args[0])
    else:
        state.args.append(None)

def getIrcColor(irc, msg, args, state):
    if args[0] in ircutils.mircColors:
        state.args.append(ircutils.mircColors[args.pop(0)])
    else:
        state.errorInvalid(_('irc color'))

def getText(irc, msg, args, state):
    if args:
        state.args.append(' '.join(args))
        args[:] = []
    else:
        raise IndexError

wrappers = ircutils.IrcDict({
    'admin': admin,
    'anything': anything,
    'banmask': getBanmask,
    'boolean': getBoolean,
    'callerInGivenChannel': callerInGivenChannel,
    'isGranted': getHaveHalfopPlus, # Backward compatibility
    'capability': getSomethingNoSpaces,
    'channel': getChannel,
    'channels': getChannels,
    'channelOrGlobal': getChannelOrGlobal,
    'channelDb': getChannelDb,
    'checkCapability': checkCapability,
    'checkCapabilityButIgnoreOwner': checkCapabilityButIgnoreOwner,
    'checkChannelCapability': checkChannelCapability,
    'color': getIrcColor,
    'commandName': getCommandName,
    'email': getEmail,
    'expiry': getExpiry,
    'filename': getSomething, # XXX Check for validity.
    'float': getFloat,
    'glob': getGlob,
    'halfop': getHalfop,
    'haveHalfop': getHaveHalfop,
    'haveHalfop+': getHaveHalfopPlus,
    'haveOp': getHaveOp,
    'haveOp+': getHaveOp, # We don't handle modes greater than op.
    'haveVoice': getHaveVoice,
    'haveVoice+': getHaveVoicePlus,
    'hostmask': getHostmask,
    'httpUrl': getHttpUrl,
    'id': getId,
    'inChannel': inChannel,
    'index': getIndex,
    'int': getInt,
    'ip': getIp,
    'letter': getLetter,
    'literal': getLiteral,
    'long': getLong,
    'lowered': getLowered,
    'matches': getMatch,
    'networkIrc': getNetworkIrc,
    'nick': getNick,
    'nickInChannel': nickInChannel,
    'nonInt': getNonInt,
    'nonNegativeInt': getNonNegativeInt,
    'now': getNow,
    'onlyInChannel': onlyInChannel,
    'op': getOp,
    'otherUser': getOtherUser,
    'owner': owner,
    'plugin': getPlugin,
    'positiveInt': getPositiveInt,
    'private': private,
    'public': public,
    'regexpMatcher': getMatcher,
    'regexpMatcherMany': getMatcherMany,
    'regexpReplacer': getReplacer,
    'seenNick': getSeenNick,
    'something': getSomething,
    'somethingWithoutSpaces': getSomethingNoSpaces,
    'text': getText,
    'to': getTo,
    'url': getUrl,
    'user': getUser,
    'validChannel': validChannel,
    'voice': getVoice,
})

def addConverter(name, wrapper):
    wrappers[name] = wrapper

class UnknownConverter(KeyError):
    pass

def getConverter(name):
    try:
        return wrappers[name]
    except KeyError as e:
        raise UnknownConverter(str(e))

def callConverter(name, irc, msg, args, state, *L):
    getConverter(name)(irc, msg, args, state, *L)

###
# Contexts.  These determine what the nature of conversions is; whether they're
# defaulted, or many of them are allowed, etc.  Contexts should be reusable;
# i.e., they should not maintain state between calls.
###
def contextify(spec):
    if not isinstance(spec, context):
        spec = context(spec)
    return spec

def setDefault(state, default):
    if callable(default):
        state.args.append(default())
    else:
        state.args.append(default)

class context(object):
    def __init__(self, spec):
        self.args = ()
        self.spec = spec # for repr
        if isinstance(spec, tuple):
            assert spec, 'tuple spec must not be empty.'
            self.args = spec[1:]
            self.converter = getConverter(spec[0])
        elif spec is None:
            self.converter = getConverter('anything')
        elif isinstance(spec, minisix.string_types):
            self.args = ()
            self.converter = getConverter(spec)
        else:
            assert isinstance(spec, context)
            self.converter = spec

    def __call__(self, irc, msg, args, state):
        log.debug('args before %r: %r', self, args)
        self.converter(irc, msg, args, state, *self.args)
        log.debug('args after %r: %r', self, args)

    def __repr__(self):
        return '<%s for %s>' % (self.__class__.__name__, self.spec)

class rest(context):
    def __call__(self, irc, msg, args, state):
        if args:
            original = args[:]
            args[:] = [' '.join(args)]
            try:
                super(rest, self).__call__(irc, msg, args, state)
            except Exception:
                args[:] = original
        else:
            raise IndexError

# additional means:  Look for this (and make sure it's of this type).  If
# there are no arguments for us to check, then use our default.
class additional(context):
    def __init__(self, spec, default=None):
        self.__parent = super(additional, self)
        self.__parent.__init__(spec)
        self.default = default

    def __call__(self, irc, msg, args, state):
        try:
            self.__parent.__call__(irc, msg, args, state)
        except IndexError:
            log.debug('Got IndexError, returning default.')
            setDefault(state, self.default)

# optional means: Look for this, but if it's not the type I'm expecting or
# there are no arguments for us to check, then use the default value.
class optional(additional):
    def __call__(self, irc, msg, args, state):
        try:
            super(optional, self).__call__(irc, msg, args, state)
        except (callbacks.ArgumentError, callbacks.Error) as e:
            log.debug('Got %s, returning default.', utils.exnToString(e))
            state.errored = False
            setDefault(state, self.default)

class any(context):
    def __init__(self, spec, continueOnError=False):
        self.__parent = super(any, self)
        self.__parent.__init__(spec)
        self.continueOnError = continueOnError

    def __call__(self, irc, msg, args, state):
        st = state.essence()
        try:
            while args:
                self.__parent.__call__(irc, msg, args, st)
        except IndexError:
            pass
        except (callbacks.ArgumentError, callbacks.Error) as e:
            if not self.continueOnError:
                raise
            else:
                log.debug('Got %s, returning default.', utils.exnToString(e))
                pass
        state.args.append(st.args)

class many(any):
    def __call__(self, irc, msg, args, state):
        super(many, self).__call__(irc, msg, args, state)
        if not state.args[-1]:
            state.args.pop()
            raise callbacks.ArgumentError

class first(context):
    def __init__(self, *specs, **kw):
        if 'default' in kw:
            self.default = kw.pop('default')
            assert not kw, 'Bad kwargs for first.__init__'
        self.spec = specs # for __repr__
        self.specs = list(map(contextify, specs))

    def __call__(self, irc, msg, args, state):
        errored = False
        for spec in self.specs:
            try:
                spec(irc, msg, args, state)
                return
            except Exception as e:
                e2 = e # 'e' is local.
                errored = state.errored
                state.errored = False
                continue
        if hasattr(self, 'default'):
            state.args.append(self.default)
        else:
            state.errored = errored
            raise e2

class reverse(context):
    def __call__(self, irc, msg, args, state):
        args[:] = args[::-1]
        super(reverse, self).__call__(irc, msg, args, state)
        args[:] = args[::-1]

class commalist(context):
    def __call__(self, irc, msg, args, state):
        original = args[:]
        st = state.essence()
        trailingComma = True
        try:
            while trailingComma:
                arg = args.pop(0)
                if not arg.endswith(','):
                    trailingComma = False
                for part in arg.split(','):
                    if part: # trailing commas
                        super(commalist, self).__call__(irc, msg, [part], st)
            state.args.append(st.args)
        except Exception:
            args[:] = original
            raise

class getopts(context):
    """The empty string indicates that no argument is taken; None indicates
    that there is no converter for the argument."""
    def __init__(self, getopts):
        self.spec = getopts # for repr
        self.getopts = {}
        self.getoptL = []
        self.getoptLs = ''
        for (name, spec) in getopts.items():
            if spec == '':
                if len(name) == 1:
                    self.getoptLs += name
                    self.getopts[name] = None
                self.getoptL.append(name)
                self.getopts[name] = None
            else:
                if len(name) == 1:
                    self.getoptLs += name + ':'
                    self.getopts[name] = contextify(spec)
                self.getoptL.append(name + '=')
                self.getopts[name] = contextify(spec)
        log.debug('getopts: %r', self.getopts)
        log.debug('getoptL: %r', self.getoptL)

    def __call__(self, irc, msg, args, state):
        log.debug('args before %r: %r', self, args)
        (optlist, rest) = getopt.getopt(args, self.getoptLs, self.getoptL)
        getopts = []
        for (opt, arg) in optlist:
            if opt.startswith('--'):
                opt = opt[2:] # Strip --
            else:
                opt = opt[1:]
            log.debug('opt: %r, arg: %r', opt, arg)
            context = self.getopts[opt]
            if context is not None:
                st = state.essence()
                context(irc, msg, [arg], st)
                assert len(st.args) == 1
                getopts.append((opt, st.args[0]))
            else:
                getopts.append((opt, True))
        state.args.append(getopts)
        args[:] = rest
        log.debug('args after %r: %r', self, args)

###
# This is our state object, passed to converters along with irc, msg, and args.
###

class State(object):
    log = log
    def __init__(self, types):
        self.args = []
        self.kwargs = {}
        self.types = types
        self.channel = None
        self.errored = False

    def __getattr__(self, attr):
        if attr.startswith('error'):
            self.errored = True
            return getattr(dynamic.irc, attr)
        else:
            raise AttributeError(attr)

    def essence(self):
        st = State(self.types)
        for (attr, value) in self.__dict__.items():
            if attr not in ('args', 'kwargs'):
                setattr(st, attr, value)
        return st

    def __repr__(self):
        return '%s(args=%r, kwargs=%r, channel=%r)' % (self.__class__.__name__,
                                                       self.args, self.kwargs,
                                                       self.channel)


###
# This is a compiled Spec object.
###
class Spec(object):
    def _state(self, types, attrs={}):
        st = State(types)
        st.__dict__.update(attrs)
        st.allowExtra = self.allowExtra
        return st

    def __init__(self, types, allowExtra=False):
        self.types = types
        self.allowExtra = allowExtra
        utils.seq.mapinto(contextify, self.types)

    def __call__(self, irc, msg, args, stateAttrs={}):
        state = self._state(self.types[:], stateAttrs)
        while state.types:
            context = state.types.pop(0)
            try:
                context(irc, msg, args, state)
            except IndexError:
                raise callbacks.ArgumentError
        if args and not state.allowExtra:
            log.debug('args and not self.allowExtra: %r', args)
            raise callbacks.ArgumentError
        return state

def _wrap(f, specList=[], name=None, checkDoc=True, **kw):
    name = name or f.__name__
    assert (not checkDoc) or (hasattr(f, '__doc__') and f.__doc__), \
                'Command %r has no docstring.' % name
    spec = Spec(specList, **kw)
    def newf(self, irc, msg, args, **kwargs):
        state = spec(irc, msg, args, stateAttrs={'cb': self, 'log': self.log})
        self.log.debug('State before call: %s', state)
        if state.errored:
            self.log.debug('Refusing to call %s due to state.errored.', f)
        else:
            try:
                f(self, irc, msg, args, *state.args, **state.kwargs)
            except TypeError:
                self.log.error('Spec: %s', specList)
                self.log.error('Received args: %s', args)
                code = f.__code__
                funcArgs = inspect.getargs(code)[0][len(self.commandArgs):]
                self.log.error('Extra args: %s', funcArgs)
                self.log.debug('Make sure you did not wrap a wrapped '
                               'function ;)')
                raise
    newf2 = utils.python.changeFunctionName(newf, name, f.__doc__)
    newf2.__module__ = f.__module__
    return internationalizeDocstring(newf2)

def wrap(f, *args, **kwargs):
    if callable(f):
        # Old-style call OR decorator syntax with no converter.
        # f is the command.
        return _wrap(f, *args, **kwargs)
    else:
        # Call with the Python decorator syntax
        assert isinstance(f, list) or isinstance(f, tuple)
        specList = f
        def decorator(f):
            return _wrap(f, specList, *args, **kwargs)
        return decorator
wrap.__doc__ = """Useful wrapper for plugin commands.

Valid converters are: %s.

:param f: A command, taking (self, irc, msg, args, ...) as arguments
:param specList: A list of converters and contexts""" % \
        ', '.join(sorted(wrappers.keys()))

__all__ = [
    # Contexts.
    'any', 'many',
    'optional', 'additional',
    'rest', 'getopts',
    'first', 'reverse',
    'commalist',
    # Converter helpers.
    'getConverter', 'addConverter', 'callConverter',
    # Decorators.
    'urlSnarfer', 'thread',
    # Functions.
    'wrap', 'process', 'regexp_wrapper',
    # Stuff for testing.
    'Spec',
]

# This doesn't work.  Suck.
## if world.testing:
##     __all__.append('Spec')

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
