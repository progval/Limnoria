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

import supybot.fix as fix
import supybot.utils as utils

class RegistryException(Exception):
    pass

class InvalidRegistryFile(RegistryException):
    pass

class InvalidRegistryName(RegistryException):
    pass

class InvalidRegistryValue(RegistryException):
    pass

class NonExistentRegistryEntry(RegistryException):
    pass

_cache = utils.InsensitivePreservingDict()
_lastModified = 0
def open(filename, clear=False):
    """Initializes the module by loading the registry file into memory."""
    global _lastModified
    if clear:
        _cache.clear()
    _fd = file(filename)
    fd = utils.nonCommentNonEmptyLines(_fd)
    for (i, line) in enumerate(fd):
        line = line.rstrip('\r\n')
        try:
            (key, value) = re.split(r':\s*', line, 1)
        except ValueError:
            raise InvalidRegistryFile, 'Error unpacking line #%s' % (i+1)
        _cache[key] = value
    _lastModified = time.time()
    _fd.close()

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
                if hasattr(value, 'value'):
                    if value.showDefault:
                        lines.append('#\n')
                        try:
                            original = value.value
                            value.value = value._default
                            lines.append('# Default value: %s\n' % value)
                        finally:
                            value.value = original
                lines.append('###\n')
                fd.writelines(lines)
        if hasattr(value, 'value'): # This lets us print help for non-valued.
            fd.write('%s: %s\n' % (escape(name), value))
    fd.close()

def isValidRegistryName(name):
    return '.' not in name and ':' not in name and len(name.split()) == 1

def escape(name):
    return name

def split(name):
    # XXX: This should eventually handle escapes.
    return name.split('.')

def join(names):
    return '.'.join(names)

class Group(object):
    def __init__(self, supplyDefault=False):
        self._name = 'unset'
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

    def __call__(self):
        raise ValueError, 'Groups have no value.'

    def __nonExistentEntry(self, attr):
        s = '%s is not a valid entry in %s' % (attr, self._name)
        raise NonExistentRegistryEntry, s

    def __makeChild(self, attr, s):
        v = self.__class__(self._default, self.help)
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
        self._name = name
        if name in _cache and self._lastModified < _lastModified:
            self.set(_cache[name])
        if self.supplyDefault:
            for (k, v) in _cache.iteritems():
                if k.startswith(self._name):
                    group = split(k)[-1]
                    try:
                        self.__makeChild(group, v)
                    except InvalidRegistryValue:
                        # It's probably supposed to be registered later.
                        pass

    def register(self, name, node=None):
        if not isValidRegistryName(name):
            raise InvalidRegistryName, name
        if node is None:
            node = Group()
        if name not in self.children: # XXX Is this right?
            self.children[name] = node
            self.added.append(name)
            fullname = join([self._name, name])
            node.setName(fullname)
        return node

    def unregister(self, name):
        try:
            node = self.children[name]
            del self.children[name]
            self.added.remove(name)
            return node
        except KeyError:
            self.__nonExistentEntry(name)

    def rename(self, old, new):
        node = self.unregister(old)
        self.register(new, node)

    def getValues(self, getChildren=False, fullNames=True):
        L = []
        for name in self.added:
            node = self.children[name]
            if hasattr(node, 'value') or hasattr(node, 'help'):
                if node.__class__ is not self.X:
                    L.append((node._name, node))
            if getChildren:
                L.extend(node.getValues(getChildren, fullNames))
        if not fullNames:
            L = [(split(s)[-1], node) for (s, node) in L]
        return L


class Value(Group):
    """Invalid registry value.  If you're getting this message, report it,
    because we forgot to put a proper help string here."""
    def __init__(self, default, help,
                 private=False, showDefault=True, **kwargs):
        Group.__init__(self, **kwargs)
        self._default = default
        self._private = private
        self.showDefault = showDefault
        self.help = utils.normalizeWhitespace(help.strip())
        self.setValue(default)

    def error(self):
        if self.__doc__:
            s = self.__doc__
        else:
            s = """Invalid registry value.  If you're getting this message,
            report it, because we forgot to put a proper help string here."""
        raise InvalidRegistryValue, utils.normalizeWhitespace(s)

    def setName(self, *args):
        if self._name == 'unset':
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
        if self.supplyDefault:
            for (name, v) in self.children.items():
                if v.__class__ is self.X:
                    self.unregister(name)

    def __str__(self):
        return repr(self())

    # This is simply prettier than naming this function get(self)
    def __call__(self):
        if _lastModified > self._lastModified:
            if self._name in _cache:
                self.set(_cache[self._name])
        return self.value

class Boolean(Value):
    """Value must be either True or False (or On or Off)."""
    def set(self, s):
        s = s.strip().lower()
        if s in ('true', 'on', 'enable', 'enabled'):
            value = True
        elif s in ('false', 'off', 'disable', 'disabled'):
            value = False
        elif s == 'toggle':
            value = not self.value
        else:
            self.error()
        self.setValue(value)

    def setValue(self, v):
        Value.setValue(self, bool(v))

class Integer(Value):
    """Value must be an integer."""
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            self.error()

class PositiveInteger(Value):
    """Value must be positive (non-zero) integer."""
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            self.error()

    def setValue(self, v):
        if v <= 0:
            self.error()
        Value.setValue(self, v)

class Float(Value):
    """Value must be a floating-point number."""
    def set(self, s):
        try:
            self.setValue(float(s))
        except ValueError:
            self.error()

    def setValue(self, v):
        try:
            Value.setValue(self, float(v))
        except ValueError:
            self.error()

class String(Value):
    """Value is not a valid Python string."""
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
            self.error()

class OnlySomeStrings(String):
    validStrings = ()
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        String.__init__(self, *args, **kwargs)

    def error(self):
        raise InvalidRegistryValue, \
              'That is not a valid value.  Valid values include %s.' % \
              utils.commaAndify(map(repr, self.validStrings))

    def normalize(self, s):
        lowered = s.lower()
        L = list(map(str.lower, self.validStrings))
        try:
            i = L.index(lowered)
        except ValueError:
            return s # This is handled in setValue.
        return self.validStrings[i]

    def setValue(self, s):
        s = self.normalize(s)
        if s in self.validStrings:
            String.setValue(self, s)
        else:
            self.error()

class NormalizedString(String):
    def normalize(self, s):
        return utils.normalizeWhitespace(s.strip())
    
    def set(self, s):
        s = self.normalize(s)
        String.set(self, s)

    def setValue(self, s):
        s = self.normalize(s)
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
    def error(self, e):
        raise InvalidRegistryValue, 'Invalid regexp: %s' % e

    def set(self, s):
        try:
            if s:
                self.value = utils.perlReToPythonRe(s)
                self._lastModified = time.time()
            else:
                self.setValue(None)
            self.sr = s
        except ValueError, e:
            self.error(e)

    def setValue(self, v):
        if v is None:
            self.sr = ''
            Value.setValue(self, None)
        else:
            raise InvalidRegistryValue, \
                  'Can\'t setValue a regexp, there would be an inconsistency '\
                  'between the regexp and the recorded string value.'

    def __str__(self):
        self() # Gotta update if we've been reloaded.
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
        value = self()
        if value:
            return self.joiner(value)
        else:
            # We must return *something* here, otherwise down along the road we
            # can run into issues showing users the value if they've disabled
            # nick prefixes in any of the numerous ways possible.  Since the
            # config parser doesn't care about this space, we'll use it :)
            return ' '

class SpaceSeparatedListOf(SeparatedListOf):
    def splitter(self, s):
        return s.split()
    joiner = ' '.join

class SpaceSeparatedListOfStrings(SpaceSeparatedListOf):
    Value = String

class CommaSeparatedListOfStrings(SeparatedListOf):
    Value = String
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join


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

