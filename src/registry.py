#!/usr/bin/env python

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

__revision__ = "$Id$"

import re
import copy
import sets
import time
import types
import textwrap

import fix
import utils

class RegistryException(Exception):
    pass

class InvalidRegistryFile(RegistryException):
    pass

class InvalidRegistryValue(RegistryException):
    pass

class NonExistentRegistryEntry(RegistryException):
    pass

_cache = utils.InsensitivePreservingDict()
_lastModified = 0
def open(filename):
    """Initializes the module by loading the registry file into memory."""
    global _lastModified
    _cache.clear()
    fd = utils.nonCommentNonEmptyLines(file(filename))
    for (i, line) in enumerate(fd):
        line = line.rstrip('\r\n')
        try:
            (key, value) = re.split(r':\s*', line, 1)
        except ValueError:
            raise InvalidRegistryFile, 'Error unpacking line #%s' % (i+1)
        _cache[key] = value
    _lastModified = time.time()

def close(registry, filename, annotated=True, helpOnceOnly=False):
    first = True
    helpCache = sets.Set()
    fd = file(filename, 'w')
    for (name, value) in registry.getValues(getChildren=True):
        if annotated and hasattr(value,'help') and value.help:
            if not helpOnceOnly or value.help not in self.helpCache:
                helpCache.add(value.help)
                lines = textwrap.wrap(value.help)
                for (i, line) in enumerate(lines):
                    lines[i] = '# %s\n' % line
                lines.insert(0, '###\n')
                if first:
                    first = False
                else:
                    lines.insert(0, '\n')
                lines.append('#\n')
                try:
                    original = value.value
                    value.value = value.default
                    lines.append('# Default value: %s\n' % value)
                finally:
                    value.value = original
                lines.append('###\n')
                fd.writelines(lines)
        fd.write('%s: %s\n' % (name, value))
    fd.close()


class Group(object):
    def __init__(self, supplyDefault=False):
        self.name = 'unset'
        self.added = []
        self.children = utils.InsensitivePreservingDict()
        self._lastModified = 0
        self.supplyDefault = supplyDefault
        OriginalClass = self.__class__
        class X(OriginalClass):
            """This class exists to differentiate those values that have
            been changed from their default from those that haven't."""
            def set(self, *args):
                self.__class__ = OriginalClass
                self.set(*args)
            def setValue(self, *args):
                self.__class__ = OriginalClass
                self.setValue(*args)
        self.X = X

    def __nonExistentEntry(self, attr):
        s = '%s is not a valid entry in %s' % (attr, self.name)
        raise NonExistentRegistryEntry, s

    def __makeChild(self, attr, s):
        v = self.__class__(self.default, self.help)
        v.set(s)
        v.__class__ = self.X
        v.supplyDefault = False
        v.help = '' # Clear this so it doesn't print a bazillion times.
        self.register(attr, v)
        return v

    def __getattr__(self, attr):
        if attr in self.children:
            return self.children[attr]
        elif self.supplyDefault:
            return self.__makeChild(attr, str(self))
        else:
            self.__nonExistentEntry(attr)
            
    def get(self, attr):
        # Not getattr(self, attr) because some nodes might have groups that
        # are named the same as their methods.
        return self.__getattr__(attr)

    def setName(self, name):
        self.name = name
        if name in _cache and self._lastModified < _lastModified:
            self.set(_cache[name])
        if self.supplyDefault:
            for (k, v) in _cache.iteritems():
                if k.startswith(self.name):
                    (_, group) = rsplit(k, '.', 1)
                    try:
                        self.__makeChild(group, v)
                    except InvalidRegistryValue:
                        # It's probably supposed to be registered later.
                        pass
    
    def register(self, name, node=None):
        if node is None:
            node = Group()
        if name not in self.children: # XXX Is this right?
            self.children[name] = node
            self.added.append(name)
            fullname = '%s.%s' % (self.name, name)
            node.setName(fullname)

    def unregister(self, name):
        try:
            del self.children[name]
            self.added.remove(name)
        except KeyError:
            self.__nonExistentEntry(name)

    def getValues(self, getChildren=False, fullNames=True):
        L = []
        for name in self.added:
            node = self.children[name]
            if hasattr(node, 'value'):
                if node.__class__ is not self.X:
                    L.append((node.name, node))
            if getChildren:
                L.extend(node.getValues(getChildren, fullNames))
        if not fullNames:
            L = [(rsplit(s, '.', 1)[1], node) for (s, node) in L]
        return L


class Value(Group):
    def __init__(self, default, help, **kwargs):
        Group.__init__(self, **kwargs)
        self.default = default
        self.help = utils.normalizeWhitespace(help.strip())
        self.setValue(default)

    def setName(self, *args):
        if self.name == 'unset':
            self._lastModified = 0
        Group.setName(self, *args)
        self._lastModified = time.time()

    def set(self, s):
        """Override this with a function to convert a string to whatever type
        you want, and call self.setValue to set the value."""
        raise NotImplementedError

    def setValue(self, v):
        """Check conditions on the actual value type here.  I.e., if you're a
        IntegerLessThanOneHundred (all your values must be integers less than
        100) convert to an integer in set() and check that the integer is less
        than 100 in this method.  You *must* call this parent method in your
        own setValue."""
        self._lastModified = time.time()
        self.value = v
    
    def __str__(self):
        return repr(self())

    # This is simply prettier than naming this function get(self)
    def __call__(self):
        if _lastModified > self._lastModified:
            if self.name in _cache:
                self.set(_cache[self.name])
        return self.value

class Boolean(Value):
    def set(self, s):
        s = s.lower()
        if s in ('true', 'on', 'enable', 'enabled'):
            value = True
        elif s in ('false', 'off', 'disable', 'disabled'):
            value = False
        elif s == 'toggle':
            value = not self.value
        else:
            raise InvalidRegistryValue, '%r is not True or False.' % s
        self.setValue(value)

    def setValue(self, v):
        Value.setValue(self, bool(v))

class Integer(Value):
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            raise InvalidRegistryValue, '%r is not an integer.' % s

class PositiveInteger(Value):
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            raise InvalidRegistryValue, '%r is not a positive integer.' % s

    def setValue(self, v):
        if v <= 0:
            raise InvalidRegistryValue, '%r is not a positive integer.' % v
        Value.setValue(self, v)

class Float(Value):
    def set(self, s):
        try:
            self.setValue(float(s))
        except ValueError:
            raise InvalidRegistryValue, '%r is not a float.' % s

    def setValue(self, v):
        try:
            Value.setValue(self, float(v))
        except ValueError:
            raise InvalidRegistryValue, '%r is not a float.' % v

class String(Value):
    def set(self, s):
        if not s:
            s = '""'
        elif s[0] != s[-1] or s[0] not in '\'"':
            s = repr(s)
        try:
            v = utils.safeEval(s)
            if not isinstance(v, basestring):
                raise ValueError
            self.setValue(v)
        except ValueError: # This catches utils.safeEval(s) errors too.
            raise InvalidRegistryValue, '%r is not a string.' % s

class NormalizedString(String):
    def set(self, s):
        s = utils.normalizeWhitespace(s.strip())
        String.set(self, s)

    def setValue(self, s):
        s = utils.normalizeWhitespace(s.strip())
        String.setValue(self, s)

class StringSurroundedBySpaces(String):
    def set(self, s):
        String.set(self, s)
        self.setValue(self.value)

    def setValue(self, v):
        if v.lstrip() == v:
            v= ' ' + v
        if v.rstrip() == v:
            v += ' '
        String.setValue(self, v)
            
class StringWithSpaceOnRight(String):
    def setValue(self, v):
        if v.rstrip() == v:
            v += ' '
        String.setValue(self, v)

class Regexp(Value):
    def set(self, s):
        try:
            if s:
                self.value = utils.perlReToPythonRe(s)
                self._lastModified = time.time()
            else:
                self.setValue(None)
            self.sr = s
        except ValueError, e:
            raise InvalidRegistryValue, '%r is not a valid regexp: %s' % (s, e)

    def setValue(self, v):
        if v is None:
            self.sr = ''
            Value.setValue(self, None)
        else:
            raise InvalidRegistryValue, \
                  'Can\'t set to a regexp, there would be an inconsistency ' \
                  'between the regexp and the recorded string value.'

    def __str__(self):
        return self.sr
        
class SeparatedListOf(Value):
    List = list
    Value = Value
    def splitter(self, s):
        """Override this with a function that takes a string and returns a list
        of strings."""
        raise NotImplementedError

    def joiner(self, L):
        """Override this to join the internal list for output."""
        raise NotImplementedError
    
    def set(self, s):
        L = self.splitter(s)
        for (i, s) in enumerate(L):
            v = self.Value(s, 'help does not matter here')
            L[i] = v()
        self.setValue(L)

    def setValue(self, v):
        Value.setValue(self, self.List(v))

    def __str__(self):
        return self.joiner(self.value)
        
class SpaceSeparatedListOfStrings(SeparatedListOf):
    Value = String
    def splitter(self, s):
        return s.split()
    joiner = ' '.join
    
class CommaSeparatedListOfStrings(SeparatedListOf):
    Value = String
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join
    
class CommaSeparatedSetOfStrings(CommaSeparatedListOfStrings):
    List = sets.Set


if __name__ == '__main__':
#if 1:
    import sys
    sys.setrecursionlimit(40)
    supybot = Group()
    supybot.setName('supybot')
    supybot.register('throttleTime', Float(1, """Determines the minimum
    number of seconds the bot will wait between sending messages to the server.
    """))
    supybot.register('plugins')
    supybot.plugins.register('Topic')
    supybot.plugins.topic.register('separator',
      StringSurroundedBySpaces(' || ', """Determines what separator the bot
      uses to separate topic entries.""", supplyDefault=True))
    supybot.plugins.topic.separator.get('#supybot').set(' |||| ')
    supybot.plugins.topic.separator.set(' <> ')

    supybot.throttleTime.set(10)

    supybot.register('log')
    supybot.log.register('stdout', Boolean(False, """Help for stdout."""))
    supybot.log.stdout.register('colorized', Boolean(False,
                                                     'Help colorized'))
    supybot.log.stdout.setValue(True)

    for (k, v) in supybot.getValues():
        print '%s: %s' % (k, v)

    print
    print 'Asking children'
    print

    for (k, v) in supybot.getValues(getChildren=True):
        print '%s: %s' % (k, v)

    print supybot.throttleTime.help
    print supybot.plugins.topic.separator.help
    

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

