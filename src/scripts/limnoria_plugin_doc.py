#!/usr/bin/env python3

###
# Copyright (c) 2005, Ali Afshar
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

import os
import sys
import shutil
import string
import logging

import supybot

def error(s):
    sys.stderr.write('%s\n' % s)
    sys.exit(-1)

# We need to do this before we import conf.
if not os.path.exists('doc-conf'):
    os.mkdir('doc-conf')

registryFilename = os.path.join('doc-conf', 'doc.conf')
try:
    fd = open(registryFilename, 'w')
    fd.write("""
supybot.directories.data: doc-data
supybot.directories.conf: doc-conf
supybot.directories.log: doc-logs
supybot.log.stdout: False
supybot.log.level: DEBUG
supybot.log.format: %(levelname)s %(message)s
supybot.log.plugins.individualLogfiles: False
supybot.databases: sqlite3 anydbm cdb flat pickle
""")
    fd.close()
except EnvironmentError as e:
    error('Unable to open %s for writing.' % registryFilename)

import supybot.registry as registry
registry.open_registry(registryFilename)

import supybot.log as log
import supybot.conf as conf
conf.supybot.flush.setValue(False)

import textwrap

import supybot.utils as utils
import supybot.world as world
import supybot.plugin as plugin
import supybot.registry as registry

world.documenting = True

TITLE_TEMPLATE = 'Documentation for the $name plugin for Supybot'

class PluginDoc(object):
    def __init__(self, mod, titleTemplate):
        self.mod = mod
        self.inst = self.mod.Class(None)
        self.name = self.inst.name()
        self.appendExtraBlankLine = False
        self.titleTemplate = string.Template(titleTemplate)
        self.lines = []

    def appendLine(self, line, indent=0):
        line = line.strip()
        indent = '  ' * indent
        # this looked like a good idea, but it's actually breaking lines
        # in the middle of ReST elements:
        #lines = textwrap.wrap(line, 79,
        #                      initial_indent=indent,
        #                      subsequent_indent=indent)
        lines = [indent + line.replace('\n', '\n' + indent)]
        self.lines.extend(lines)
        if self.appendExtraBlankLine:
            self.lines.append('')

    def renderRST(self):
        self.appendExtraBlankLine = False
        self.appendLine('.. _plugin-%s:' % self.name)
        self.lines.append('')
        s = self.titleTemplate.substitute(name=self.name)
        self.appendLine(s)
        self.appendLine('=' * len(s))
        self.lines.append('')
        self.appendLine('Purpose')
        self.appendLine('-------')
        self.lines.append('')
        pdoc = getattr(self.mod, '__doc__',
                       'My author didn\'t give me a purpose.')
        self.appendLine(pdoc)
        self.lines.append('')
        cdoc = getattr(self.mod.Class, '__doc__', None)
        if cdoc is not None:
            self.appendLine('Usage')
            self.appendLine('-----')
            self.lines.append('')
            # We add spaces at the beginning in case the docstring does not
            # start with a newline (the default, unfortunately)
            self.appendLine(textwrap.dedent(" "* 1000 + cdoc).lstrip())
            self.lines.append('')
        commands = self.inst.listCommands()
        if len(commands):
            self.lines.append('.. _commands-%s:\n' % self.name)
            self.appendLine('Commands')
            self.appendLine('--------')
            self.lines.append('')
            for command in commands:
                log.debug('command: %s', command)
                self.lines.append('.. _command-%s-%s:\n' %
                    (self.name.lower(), command.replace(' ', '.')))
                line = '%s ' % command
                command = command.split()
                doc = self.inst.getCommandHelp(command)
                if doc:
                    doc = doc.replace('\x02', '')
                    (args, help) = doc.split(')', 1)
                    args = args.split('(', 1)[1]
                    args = args[len(' '.join(command)):].strip()
                    help = help.split('--', 1)[1].strip()
                    self.appendLine('``' + line + args + '``')
                    self.appendLine(help, 1)
                else:
                    self.appendLine('No help associated with this command')
                self.lines.append('')
        # now the config
        try:
            confs = conf.supybot.plugins.get(self.name)
            self.lines.append('.. _conf-%s:\n' % self.name)
            self.appendLine('Configuration')
            self.appendLine('-------------')
            self.lines.append('')
        except registry.NonExistentRegistryEntry:
            log.info('No configuration for plugin %s', plugin)
            self.appendLine('No configuration for this plugin')
        else:
            for confValues in self.genConfig(confs, 0):
                (name, kind, help, default, indent) = confValues
                self.appendLine('.. _conf-%s:' % name, indent - 1)
                self.lines.append('\n')
                self.appendLine('%s' % name, indent - 1)
                if default:
                    self.appendLine(
                        ('This config variable defaults to %s, %s')
                        % (default, kind), indent)
                else:
                    self.appendLine('This %s' % kind, indent)
                if help:
                    self.lines.append('')
                    self.appendLine(help, indent)
                self.lines.append('')
        return '\n'.join(self.lines) + '\n'

    def renderSTX(self):
        self.appendExtraBlankLine = True
        self.appendLine(self.titleTemplate.substitute(name=self.name))
        self.appendLine('Purpose', 1)
        pdoc = getattr(self.mod, '__doc__',
                       'My author didn\'t give me a purpose.')
        self.appendLine(pdoc, 2)
        cdoc = getattr(self.mod.Class, '__doc__', None)
        if cdoc is not None:
            self.appendLine('Usage', 1)
            self.appendLine(cdoc, 2)
        commands = self.inst.listCommands()
        if len(commands):
            self.appendLine('Commands', 1)
            for command in commands:
                log.debug('command: %s', command)
                line = '* %s ' % command
                command = command.split()
                doc = self.inst.getCommandHelp(command)
                if doc:
                    doc = doc.replace('\x02', '')
                    (args, help) = doc.split(')', 1)
                    args = args.split('(', 1)[1]
                    args = args[len(' '.join(command)):].strip()
                    help = help.split('--', 1)[1].strip()
                    self.appendLine(line + args, 2)
                    self.appendLine(help, 3)
                else:
                    self.appendLine('No help associated with this command', 3)
        # now the config
        try:
            confs = conf.supybot.plugins.get(self.name)
            self.appendLine('Configuration', 1)
        except registry.NonExistentRegistryEntry:
            log.info('No configuration for plugin %s', plugin)
            self.appendLine('No configuration for this plugin', 2)
        else:
            for confValues in self.genConfig(confs, 2):
                (name, kind, help, default, indent) = confValues
                self.appendLine('* %s' % name, indent - 1)
                if default:
                    self.appendLine(
                        ('This config variable defaults to %s, %s')
                        % (default, kind), indent)
                else:
                    self.appendLine('This %s' % kind, indent)
                self.appendLine(help, indent)
        return '\n'.join(self.lines) + '\n'

    def genConfig(self, item, origindent):
        confVars = item.getValues(getChildren=False, fullNames=False)
        if not confVars:
            return
        for (c, v) in confVars:
            name = v._name
            indent = origindent + 1
            if isinstance(v, registry.Value):
                try:
                    default = utils.str.dqrepr(str(v))
                    help = v.help()
                except registry.NonExistentRegistryEntry:
                    pass
                else:
                    cv = '' if v._channelValue else ' not'
                    nv = '' if v._networkValue else ' not'
                    kind = (
                        'is%s network-specific, and is%s channel-specific.'
                        % (nv, cv)
                    )
            else:
                help = ''
                default = ''
                kind = 'is a group of:'
            yield (name, kind, help, default, indent)
            for confValues in self.genConfig(v, indent):
                yield confValues

def genDoc(m, options):
    Plugin = PluginDoc(m, options.titleTemplate)
    outputFilename = string.Template(options.outputFilename).substitute(
        name=Plugin.name, format=options.format)
    path = os.path.join(options.outputDir, outputFilename)
    print('Generating documentation for %s to %s...' % (Plugin.name, path))
    try:
        fd = open(path, 'w')
    except EnvironmentError as e:
        error('Unable to open %s for writing.' % path)
    f = getattr(Plugin, 'render%s' % options.format.upper(), None)
    if f is None:
        fd.close()
        error('Unknown render format: `%s\'' % options.format)
    try:
        fd.write(f())
    finally:
        fd.close()

def main():
    import glob
    import os.path
    import optparse
    import supybot.plugin as plugin

    parser = optparse.OptionParser(usage='Usage: %prog [options] [plugins]',
                                   version='Supybot %s' % conf.version)
    parser.add_option('-c', '--clean', action='store_true', default=False,
                      dest='clean', help='Cleans the various data/conf/logs '
                      'directories after generating the docs.')
    parser.add_option('-o', '--output-dir', dest='outputDir', default='.',
                      help='Specifies the directory in which to write the '
                      'documentation for the plugin.')
    parser.add_option('--output-filename', dest='outputFilename',
                      default='$name.$format',
                      help='Specifies the path of individual output files. '
                      'If present in the value, "$name" will be substituted '
                      'with the plugin\'s name and "$format" with the value '
                      'if --format.')
    parser.add_option('-f', '--format', dest='format', choices=['rst', 'stx'],
                      default='rst', help='Specifies which output format to '
                      'use.')
    parser.add_option('--plugins-dir',
                      action='append', dest='pluginsDirs', default=[],
                      help='Looks in in the given directory for plugins and '
                      'generates documentation for all of them.')
    parser.add_option('--title-template',
                      default=TITLE_TEMPLATE, dest='titleTemplate',
                      help='Template string for the title of generated files')
    (options, args) = parser.parse_args()

    # This must go before checking for args, of course.
    for pluginDir in options.pluginsDirs:
        for name in glob.glob(os.path.join(pluginDir, '*')):
            if os.path.isdir(name):
                args.append(name)

    if not args:
        parser.print_help()
        sys.exit(-1)

    args = [s.rstrip('\\/') for s in args]
    pluginDirs = set([os.path.dirname(s) or '.' for s in args])
    conf.supybot.directories.plugins.setValue(list(pluginDirs))
    pluginNames = set([os.path.basename(s) for s in args])
    plugins = set([])
    for pluginName in pluginNames:
        if pluginName == '__pycache__':
            continue
        if pluginName.endswith('.py'):
            pluginName = pluginName[:-3]
        try:
            pluginModule = plugin.loadPluginModule(pluginName)
        except ImportError as e:
            s = 'Failed to load plugin %s: %s\n' \
                '(pluginDirs: %s)' % (pluginName, e,
                                      conf.supybot.directories.plugins())
            error(s)
        plugins.add(pluginModule)

    for Plugin in plugins:
        genDoc(Plugin, options)

    if options.clean:
        # We are about to remove the log dir; so trying to write anything
        # (such as "Shutdown initiated." and friends, from atexit callbacks)
        # would result in errors.
        log._handler.setLevel(logging.CRITICAL)
        shutil.rmtree(conf.supybot.directories.log())
        shutil.rmtree(conf.supybot.directories.conf())
        shutil.rmtree(conf.supybot.directories.data())


if __name__ == '__main__':
    main()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=78:
