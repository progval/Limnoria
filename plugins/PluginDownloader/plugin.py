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

import os
import io
import sys
import json
import shutil
import urllib
import urllib2
import tarfile
from cStringIO import StringIO

BytesIO = StringIO if sys.version_info[0] < 3 else io.BytesIO

import supybot.log as log
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('PluginDownloader')

class Repository:
    pass

class VersionnedRepository(Repository):
    pass

class GitRepository(VersionnedRepository):
    pass

class GithubRepository(GitRepository):
    def __init__(self, username, reponame, path='/'):
        self._username = username
        self._reponame = reponame
        if not path.startswith('/'):
            path = '/' + path
        if not path.endswith('/'):
            path += '/'
        self._path = path

        self._downloadUrl = 'https://github.com/%s/%s/tarball/master' % \
                            (
                            self._username,
                            self._reponame,
                            )


    _apiUrl = 'https://api.github.com'
    def _query(self, type_, uri_end, args={}):
        args = dict([(x,y) for x,y in args.items() if y is not None])
        url = '%s/%s/%s?%s' % (self._apiUrl, type_, uri_end,
                               urllib.urlencode(args))
        return json.loads(utils.web.getUrl(url).decode('utf8'))

    def getPluginList(self):
        plugins = self._query(
                                  'repos',
                                  '%s/%s/contents%s' % (
                                                          self._username,
                                                          self._reponame,
                                                          self._path,
                                                          )
                                  )
        if plugins is None:
            log.error((
                      'Cannot get plugins list from repository %s/%s '
                      'at Github'
                      ) % (self._username, self._reponame))
            return []
        plugins = [x['name'] for x in plugins if x['type'] == 'dir']
        return plugins

    def _download(self, plugin):
        try:
            response = utils.web.getUrlFd(self._downloadUrl)
            if sys.version_info[0] < 3:
                assert response.getcode() == 200, response.getcode()
            else:
                assert response.status == 200, response.status
            fileObject = BytesIO()
            fileObject.write(response.read())
        finally: # urllib does not handle 'with' statements :(
            response.close()
        fileObject.seek(0)
        return tarfile.open(fileobj=fileObject, mode='r:gz')
    def install(self, plugin):
        archive = self._download(plugin)
        prefix = archive.getnames()[0]
        dirname = ''.join((self._path, plugin))
        directories = conf.supybot.directories.plugins()
        directory = self._getWritableDirectoryFromList(directories)
        assert directory is not None, \
                'No valid directory in supybot.directories.plugins.'

        try:
            assert archive.getmember(prefix + dirname).isdir(), \
                'This is not a valid plugin (it is a file, not a directory).'

            run_2to3 = sys.version_info[0] >= 3
            for file in archive.getmembers():
                if file.name.startswith(prefix + dirname):
                    extractedFile = archive.extractfile(file)
                    newFileName = os.path.join(*file.name.split('/')[1:])
                    newFileName = newFileName[len(self._path)-1:]
                    newFileName = os.path.join(directory, newFileName)
                    if os.path.exists(newFileName):
                        assert os.path.isdir(newFileName), newFileName + \
                                'should not be a file.'
                        shutil.rmtree(newFileName)
                    if extractedFile is None:
                        os.mkdir(newFileName)
                    else:
                        with open(newFileName, 'ab') as fd:
                            reload_imported = False
                            for line in extractedFile.readlines():
                                if sys.version_info[0] >= 3:
                                    if 'import reload' in line.decode():
                                        reload_imported = True
                                    elif not reload_imported and \
                                            'reload(' in line.decode():
                                        fd.write('from imp import reload\n' \
                                                .encode())
                                        reload_imported = True
                                fd.write(line)
                    if newFileName.endswith('__init__.py'):
                        with open(newFileName) as fd:
                            lines = list(filter(lambda x:'import plugin' in x,
                                fd.readlines()))
                            if lines and lines[0].startswith('from . import'):
                                # This should be already Python 3-compatible
                                run_2to3 = False
        finally:
            archive.close()
            del archive
        if run_2to3:
            try:
                import lib2to3
            except ImportError:
                return _('Plugin is probably not compatible with your '
                        'Python version (3.x) and could not be converted '
                        'because 2to3 is not installed.')
            import subprocess
            fixers = []
            subprocess.Popen(['2to3', '-wn', os.path.join(directory, plugin)]) \
                    .wait()
            return _('Plugin was designed for Python 2, but an attempt to '
                    'convert it to Python 3 has been made. There is no '
                    'garantee it will work, though.')
        else:
            return _('Plugin successfully installed.')

    def getInfo(self, plugin):
        archive = self._download(plugin)
        prefix = archive.getnames()[0]
        dirname = ''.join((self._path, plugin))
        for file in archive.getmembers():
            if file.name.startswith(prefix + dirname + '/README'):
                extractedFile = archive.extractfile(file)
                content = extractedFile.read()
                if sys.version_info[0] >= 3:
                    content = content.decode()
                return content

    def _getWritableDirectoryFromList(self, directories):
        for directory in directories:
            if os.access(directory, os.W_OK):
                return directory
        return None


repositories = {
               'ProgVal':          GithubRepository(
                                                   'ProgVal',
                                                   'Supybot-plugins'
                                                   ),
               'quantumlemur':     GithubRepository(
                                                   'quantumlemur',
                                                   'Supybot-plugins',
                                                   ),
               'stepnem':          GithubRepository(
                                                   'stepnem',
                                                   'supybot-plugins',
                                                   ),
               'code4lib-snapshot':GithubRepository(
                                                   'code4lib',
                                                   'supybot-plugins',
                                                   'Supybot-plugins-20060723',
                                                   ),
               'code4lib-edsu':    GithubRepository(
                                                   'code4lib',
                                                   'supybot-plugins',
                                                   'edsu-plugins',
                                                   ),
               'code4lib':         GithubRepository(
                                                   'code4lib',
                                                   'supybot-plugins',
                                                   'plugins',
                                                   ),
               'nanotube-bitcoin': GithubRepository(
                                                   'nanotube',
                                                   'supybot-bitcoin-'
                                                             'marketmonitor',
                                                   ),
               'mtughan-weather':  GithubRepository(
                                                   'mtughan',
                                                   'Supybot-Weather',
                                                   ),
               'SpiderDave':       GithubRepository(
                                                   'SpiderDave',
                                                   'spidey-supybot-plugins',
                                                   'Plugins',
                                                   ),
               'Antibody':         GithubRepository(
                                                   'Antibody',
                                                   'supybot-plugins',
                                                   ),
               'doorbot':          GithubRepository(
                                                   'hacklab',
                                                   'doorbot',
                                                   ),
               'boombot':          GithubRepository(
                                                   'nod',
                                                   'boombot',
                                                   'plugins',
                                                   ),
               'mailed-notifier':  GithubRepository(
                                                   'tbielawa',
                                                   'supybot-mailed-notifier',
                                                   ),
               'pingdom':          GithubRepository(
                                                   'rynop',
                                                   'supyPingdom',
                                                   'plugins',
                                                   ),
               'scrum':            GithubRepository(
                                                   'amscanne',
                                                   'supybot-scrum',
                                                   ),
               'Hoaas':            GithubRepository(
                                                   'Hoaas',
                                                   'Supybot-plugins'
                                                   ),
               'nyuszika7h':       GithubRepository(
                                                   'nyuszika7h',
                                                   'limnoria-plugins'
                                                   ),
               'nyuszika7h-old':   GithubRepository(
                                                   'nyuszika7h',
                                                   'Supybot-plugins'
                                                   ),
               'resistivecorpse':  GithubRepository(
                                                   'resistivecorpse',
                                                   'supybot-plugins'
                                                   ),
               'frumious':         GithubRepository(
                                                   'frumiousbandersnatch',
                                                   'sobrieti-plugins',
                                                   'plugins',
                                                   ),
               'jonimoose':        GithubRepository(
                                                   'Jonimoose',
                                                   'Supybot-plugins',
                                                   ),
               'skgsergio':        GithubRepository(
                                                   'skgsergio',
                                                   'Limnoria-plugins',
                                                   ),
               'GLolol':           GithubRepository(
                                                   'GLolol',
                                                   'SupyPlugins',
                                                   ),
               'Iota':             GithubRepository(
                                                   'IotaSpencer',
                                                   'supyplugins',
                                                   ),
               }

class PluginDownloader(callbacks.Plugin):
    """This plugin allows you to install unofficial plugins from
    multiple repositories easily. Use the "repolist" command to see list of
    available repositories and "repolist <repository>" to list plugins, 
    which are available in that repository. When you want to install plugin,
    just run command "install <repository> <plugin>"."""

    threaded = True

    @internationalizeDocstring
    def repolist(self, irc, msg, args, repository):
        """[<repository>]

        Displays the list of plugins in the <repository>.
        If <repository> is not given, returns a list of available
        repositories."""

        global repositories
        if repository is None:
            irc.reply(_(', ').join([x for x in repositories]))
        elif repository not in repositories:
            irc.error(_(
                       'This repository does not exist or is not known by '
                       'this bot.'
                       ))
        else:
            plugins = repositories[repository].getPluginList()
            if plugins == []:
                irc.error(_('No plugin found in this repository.'))
            else:
                irc.reply(_(', ').join([x for x in plugins]))
    repolist = wrap(repolist, [optional('something')])

    @internationalizeDocstring
    def install(self, irc, msg, args, repository, plugin):
        """<repository> <plugin>

        Downloads and installs the <plugin> from the <repository>."""
        global repositories
        if repository not in repositories:
            irc.error(_(
                       'This repository does not exist or is not known by '
                       'this bot.'
                       ))
        elif plugin not in repositories[repository].getPluginList():
            irc.error(_('This plugin does not exist in this repository.'))
        else:
            try:
                irc.reply(repositories[repository].install(plugin))
            except Exception as e:
                import traceback
                traceback.print_exc()
                log.error(str(e))
                irc.error('The plugin could not be installed. Check the logs '
                        'for a more detailed error.')

    install = wrap(install, ['owner', 'something', 'something'])

    @internationalizeDocstring
    def info(self, irc, msg, args, repository, plugin):
        """<repository> <plugin>

        Displays informations on the <plugin> in the <repository>."""
        global repositories
        if repository not in repositories:
            irc.error(_(
                       'This repository does not exist or is not known by '
                       'this bot.'
                       ))
        elif plugin not in repositories[repository].getPluginList():
            irc.error(_('This plugin does not exist in this repository.'))
        else:
            info = repositories[repository].getInfo(plugin)
            if info is None:
                irc.error(_('No README found for this plugin'))
            else:
                if info.startswith('Insert a description of your plugin here'):
                    irc.error(_('This plugin has no description.'))
                else:
                    info = info.split('\n\n')[0]
                    irc.reply(info.replace('\n', ' '))
    info = wrap(info, ['something', optional('something')])


PluginDownloader = internationalizeDocstring(PluginDownloader)
Class = PluginDownloader


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
