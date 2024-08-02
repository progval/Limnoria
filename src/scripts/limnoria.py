###
# Copyright (c) 2003-2004, Jeremiah Fincher
# Copyright (c) 2009, James McCoy
# Copyright (c) 2010-2021, Valentin Lorentz
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
This is the main program to run Supybot.
"""

import re
import os
import sys
import atexit
import shutil
import signal

from io import StringIO  # Import this after version check since this will fail on Python 2

def _termHandler(signalNumber, stackFrame):
    raise SystemExit('Signal #%s.' % signalNumber)

signal.signal(signal.SIGTERM, _termHandler)

import time
import optparse
import textwrap

started = time.time()

import supybot
import supybot.utils as utils
import supybot.registry as registry
import supybot.questions as questions
import supybot.ircutils as ircutils
try:
    import supybot.i18n as i18n
except ImportError:
    sys.stderr.write("""Error:
    You are running a mix of Limnoria and stock Supybot code. Although you run
    one of Limnoria\'s executables, Python tries to load stock
    Supybot\'s library. To fix this issue, uninstall Supybot
    ("%s -m pip uninstall supybot" should do the job)
    and install Limnoria again.
    For your information, Supybot's libraries are installed here:
    %s\n""" %
    (sys.executable, '\n    '.join(supybot.__path__)))
    exit(-1)

from supybot.version import version

def run():
    import supybot.log as log
    import supybot.conf as conf
    import supybot.world as world
    import supybot.drivers as drivers
    import supybot.ircmsgs as ircmsgs
    import supybot.schedule as schedule
    import supybot.httpserver as httpserver
    # We schedule this event rather than have it actually run because if there
    # is a failure between now and the time it takes the Owner plugin to load
    # all the various plugins, our registry file might be wiped.  That's bad.
    interrupted = False
    when = conf.supybot.upkeepInterval()
    schedule.addPeriodicEvent(world.upkeep, when, name='upkeep', now=False)
    world.startedAt = started
    while world.ircs:
        try:
            drivers.run()
        except KeyboardInterrupt:
            if interrupted:
                # Interrupted while waiting for queues to clear.  Let's clear
                # them ourselves.
                for irc in world.ircs:
                    irc._reallyDie()
                    continue
            else:
                interrupted = True
                log.info('Exiting due to Ctrl-C.  '
                         'If the bot doesn\'t exit within a few seconds, '
                         'feel free to press Ctrl-C again to make it exit '
                         'without flushing its message queues.')
                world.upkeep()
                for irc in world.ircs:
                    quitmsg = conf.supybot.plugins.Owner.quitMsg() or \
                              'Ctrl-C at console.'
                    # Because we're quitting from the console, none of the
                    # standard msg substitutions exist, and these will show as
                    # raw strings by default. Substitute them here with
                    # something meaningful instead.
                    env = dict((key, '<console>')
                               for key in ('who', 'nick', 'user', 'host'))
                    quitmsg = ircutils.standardSubstitute(irc, None, quitmsg,
                                                          env=env)
                    irc.queueMsg(ircmsgs.quit(quitmsg))
                    irc.die()
        except SystemExit as e:
            s = str(e)
            if s:
                log.info('Exiting due to %s', s)
            break
        except:
            try: # Ok, now we're *REALLY* paranoid!
                log.exception('Exception raised out of drivers.run:')
            except Exception as e:
                print('Exception raised in log.exception.  This is *really*')
                print('bad.  Hopefully it won\'t happen again, but tell us')
                print('about it anyway, this is a significant problem.')
                print('Anyway, here\'s the exception: %s' % \
                      utils.gen.exnToString(e))
            except:
                print('Oh, this really sucks.  Not only did log.exception')
                print('raise an exception, but freaking-a, it was a string')
                print('exception.  People who raise string exceptions should')
                print('die a slow, painful death.')
    httpserver.stopServer()
    now = time.time()
    seconds = now - world.startedAt
    log.info('Total uptime: %s.', utils.gen.timeElapsed(seconds))
    (user, system, _, _, _) = os.times()
    log.info('Total CPU time taken: %.2f seconds.', user+system)
    log.info('No more Irc objects, exiting.')

def main():
    parser = optparse.OptionParser(usage='Usage: %prog [options] configFile',
                                   version='Limnoria %s running on Python %s' %
                                   (version, sys.version))
    parser.add_option('-P', '--profile', action='store_true', dest='profile',
                      help='enables profiling')
    parser.add_option('-n', '--nick', action='store',
                      dest='nick', default='',
                      help='nick the bot should use')
    parser.add_option('-u', '--user', action='store',
                      dest='user', default='',
                      help='full username the bot should use')
    parser.add_option('-i', '--ident', action='store',
                      dest='ident', default='',
                      help='ident the bot should use')
    parser.add_option('-d', '--daemon', action='store_true',
                      dest='daemon',
                      help='Determines whether the bot will daemonize.  '
                           'This is a no-op on non-POSIX systems.')
    parser.add_option('', '--allow-default-owner', action='store_true',
                      dest='allowDefaultOwner',
                      help='Determines whether the bot will allow its '
                           'defaultCapabilities not to include "-owner", thus '
                           'giving all users the owner capability by default. '
                           'This is a security risk since it allows anyone to run '
                           'any command on your bot, so we advise not to use this.')
    parser.add_option('', '--allow-root', action='store_true',
                      dest='allowRoot',
                      help='Determines whether the bot will be allowed to run '
                           'as root. This should not be used except in special '
                           'circumstances, such as running inside a containerized '
                           'environment.')
    parser.add_option('', '--debug', action='store_true', dest='debug',
                      help='Determines whether some extra debugging stuff '
                      'will be logged in this script.')
    parser.add_option('', '--disable-multiprocessing', action='store_true',
                      dest='disableMultiprocessing',
                      help='Disables multiprocessing stuff. May lead to '
                      'vulnerabilities.')

    (options, args) = parser.parse_args()

    if os.name == 'posix':
        if (os.getuid() == 0 or os.geteuid() == 0) and not options.allowRoot:
            sys.stderr.write('Running as root is not supported by default (see --allow-root).')
            sys.stderr.write(os.linesep)
            sys.exit(-1)

    if len(args) > 1:
        parser.error("""Only one configuration file should be specified.""")
    elif not args:
        parser.error(utils.str.normalizeWhitespace("""It seems you've given me
        no configuration file.  If you do have a configuration file, be sure to
        specify the filename.  If you don't have a configuration file, read
        docs/GETTING_STARTED and follow the instructions."""))
    else:
        registryFilename = args.pop()
        try:
            # The registry *MUST* be opened before importing log or conf.
            registry.open_registry(registryFilename)
            shutil.copyfile(registryFilename, registryFilename + '.bak')
        except registry.InvalidRegistryFile as e:
            s = '%s in %s.  Please fix this error and start supybot again.' % \
                (e, registryFilename)
            s = textwrap.fill(s)
            sys.stderr.write(s)
            sys.stderr.write(os.linesep)
            raise
            sys.exit(-1)
        except EnvironmentError as e:
            sys.stderr.write(str(e))
            sys.stderr.write(os.linesep)
            sys.exit(-1)

    i18n.getLocaleFromRegistryCache()

    try:
        import supybot.log as log
    except supybot.registry.InvalidRegistryValue as e:
        # This is raised here because supybot.log imports supybot.conf.
        name = e.value._name
        errmsg = textwrap.fill('%s: %s' % (name, e),
                               width=78, subsequent_indent=' '*len(name))
        sys.stderr.write(errmsg)
        sys.stderr.write(os.linesep)
        sys.stderr.write('Please fix this error in your configuration file '
                         'and restart your bot.')
        sys.stderr.write(os.linesep)
        sys.exit(-1)
    import supybot.conf as conf
    import supybot.world as world
    i18n.import_conf()
    world.starting = True

    def closeRegistry():
        # We only print if world.dying so we don't see these messages during
        # upkeep.
        logger = log.debug
        if world.dying:
            logger = log.info
        logger('Writing registry file to %s', registryFilename)
        registry.close(conf.supybot, registryFilename)
        logger('Finished writing registry file.')
    world.flushers.append(closeRegistry)
    world.registryFilename = registryFilename

    nick = options.nick or conf.supybot.nick()
    user = options.user or conf.supybot.user()
    ident = options.ident or conf.supybot.ident()

    networks = conf.supybot.networks()
    if not networks:
        questions.output("""No networks defined.  Perhaps you should re-run the
        wizard?""", fd=sys.stderr)
        # XXX We should turn off logging here for a prettier presentation.
        sys.exit(-1)

    if os.name == 'posix' and options.daemon:
        def fork():
            child = os.fork()
            if child != 0:
                if options.debug:
                    print('Parent exiting, child PID: %s' % child)
                # We must us os._exit instead of sys.exit so atexit handlers
                # don't run.  They shouldn't be dangerous, but they're ugly.
                os._exit(0)
        fork()
        os.setsid()
        # What the heck does this do?  I wonder if it breaks anything...
        # ...It did.  I don't know why, but it seems largely useless.  It seems
        # to me reasonable that we should respect the user's umask.
        #os.umask(0)
        # Let's not do this for now (at least until I can make sure it works):
        # Actually, let's never do this -- we'll always have files open in the
        # bot directories, so they won't be able to be unmounted anyway.
        # os.chdir('/')
        fork()
        # Since this is the indicator that no writing should be done to stdout,
        # we'll set it to True before closing stdout et alii.
        conf.daemonized = True
        # Closing stdin shouldn't cause problems.  We'll let it raise an
        # exception if it does.
        sys.stdin.close()
        # Closing these two might cause problems; we log writes to them as
        # level WARNING on upkeep.
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = StringIO()
        sys.stderr = StringIO()
        # We have to be really methodical here.
        os.close(0)
        os.close(1)
        os.close(2)
        fd = os.open('/dev/null', os.O_RDWR)
        os.dup2(fd, 0)
        os.dup2(fd, 1)
        os.dup2(fd, 2)
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        log.info('Completed daemonization.  Current PID: %s', os.getpid())

    # Stop setting our own umask.  See comment above.
    #os.umask(077)

    # Let's write the PID file.  This has to go after daemonization, obviously.
    pidFile = conf.supybot.pidFile()
    if pidFile:
        try:
            fd = open(pidFile, 'w')
            pid = os.getpid()
            fd.write('%s%s' % (pid, os.linesep))
            fd.close()
            def removePidFile():
                try:
                    os.remove(pidFile)
                except EnvironmentError as e:
                    log.error('Could not remove pid file: %s', e)
            atexit.register(removePidFile)
        except EnvironmentError as e:
            log.critical('Error opening/writing pid file %s: %s', pidFile, e)
            sys.exit(-1)

    conf.allowDefaultOwner = options.allowDefaultOwner
    world.disableMultiprocessing = options.disableMultiprocessing

    if not os.path.exists(conf.supybot.directories.log()):
        os.mkdir(conf.supybot.directories.log())
    if not os.path.exists(conf.supybot.directories.conf()):
        os.mkdir(conf.supybot.directories.conf())
    if not os.path.exists(conf.supybot.directories.data()):
        os.mkdir(conf.supybot.directories.data())
    if not os.path.exists(conf.supybot.directories.data.tmp()):
        os.mkdir(conf.supybot.directories.tmp())

    userdataFilename = os.path.join(conf.supybot.directories.conf(),
                                    'userdata.conf')
    # Let's open this now since we've got our directories setup.
    if not os.path.exists(userdataFilename):
        fd = open(userdataFilename, 'w')
        fd.write('\n')
        fd.close()
    registry.open_registry(userdataFilename)

    import supybot.irclib as irclib
    import supybot.ircmsgs as ircmsgs
    import supybot.drivers as drivers
    import supybot.callbacks as callbacks
    import supybot.plugins.Owner as Owner

    # This may take some resources, and it does not need to run while booting, so
    # we import it as late as possible (but before plugins are loaded).
    import supybot.httpserver as httpserver

    owner = Owner.Class()

    if options.profile:
        import cProfile
        world.profiling = True
        cProfile.runctx('run()',
                        globals=globals(), locals={**locals(), "run": run},
                        filename='%s-%i.prof' % (nick, time.time()))
    else:
        run()


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
