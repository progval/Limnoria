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

import copy
import sets
import types

import utils

class RegistryException(Exception):
    pass

class InvalidRegistryFile(RegistryException):
    pass

class InvalidRegistryValue(RegistryException):
    pass

class NonExistentRegistryEntry(RegistryException):
    pass

cache = {}
def open(filename):
    """Initializes the module by loading the registry file into memory."""
    cache.clear()
    fd = utils.nonCommentNonEmptyLines(file(filename))
    for (i, line) in enumerate(fd):
        line = line.rstrip('\r\n')
        try:
            (key, value) = line.split(': ', 1)
        except ValueError:
            raise InvalidRegistryFile, 'Error unpacking line #%s' % (i+1)
        cache[key.lower()] = value

def close(registry, filename):
    fd = file(filename, 'w')
    for (name, value) in registry.getValues(getChildren=True):
        fd.write('%s: %s\n' % (name, value))
    fd.close()


class Value(object):
    def __init__(self, default, help):
        self.default = default
        self.help = utils.normalizeWhitespace(help.strip())
        self.setValue(default)
        self.set(str(self)) # This is needed.

    def set(self, s):
        """Override this with a function to convert a string to whatever type
        you want, and set it to .value."""
        raise NotImplementedError

    def setValue(self, v):
        self.value = v
    
    def reset(self):
        self.setValue(self.default)

    def __str__(self):
        return repr(self.value)

    # This is simply prettier than naming this function get(self)
    def __call__(self):
        return self.value


class Boolean(Value):
    def set(self, s):
        s = s.lower()
        if s in ('true', 'on', 'enabled'):
            self.value = True
        elif s in ('false', 'off', 'disabled'):
            self.value = False
        elif s == 'toggle':
            self.value = not self.value
        else:
            raise InvalidRegistryValue, 'Value must be True or False.'

class Integer(Value):
    def set(self, s):
        try:
            self.value = int(s)
        except ValueError:
            raise InvalidRegistryValue, 'Value must be an integer.'

class PositiveInteger(Value):
    def set(self, s):
        try:
            original = self.value
            self.value = int(s)
            if self.value < 0:
                raise ValueError
        except ValueError:
            self.value = original
            raise InvalidRegistryValue, 'Value must be a positive integer.'

class Float(Value):
    def set(self, s):
        try:
            self.value = float(s)
        except ValueError:
            raise InvalidRegistryValue, 'Value must be a float.'

class String(Value):
    def set(self, s):
        if not s or (s[0] not in '\'"' and s[-1] not in '\'"'):
            s = repr(s)
        try:
            v = utils.safeEval(s)
            if not isinstance(v, basestring):
                raise ValueError
            self.value = v
        except ValueError: # This catches utils.safeEval(s) errors too.
            raise InvalidRegistryValue, 'Value must be a string.'

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
        if self.value.lstrip() == self.value:
            self.value = ' ' + self.value
        if self.value.rstrip() == self.value:
            self.value += ' '
            
class CommaSeparatedListOfStrings(String):
    def set(self, s):
        String.set(self, s)
        self.value = map(str.strip, self.value.split(','))

    def __str__(self):
        return ','.join(self.value)

class CommaSeparatedSetOfStrings(CommaSeparatedListOfStrings):
    def set(self, s):
        CommaSeparatedListOfStrings.set(self, s)
        self.value = sets.Set(self.value)

class Group(object):
    def __init__(self):
        self.name = 'unset'
        self.values = {}
        self.children = {}
        self.originals = {}

    def __nonExistentEntry(self, attr):
        s = '%s is not a valid entry in %s' % (attr, self.name)
        raise NonExistentRegistryEntry, s

    def __getattr__(self, attr):
        original = attr
        attr = attr.lower()
        if attr in self.values:
            return self.values[attr]
        elif attr in self.children:
            return self.children[attr]
        else:
            self.__nonExistentEntry(original)
            
    def get(self, attr):
        return self.__getattr__(attr)
    
    def getChild(self, attr):
        return self.children[attr.lower()]

    def setName(self, name):
        self.name = name

    def getName(self):
        return self.name

    def register(self, name, value):
        original = name
        name = name.lower()
        self.values[name] = value
        self.originals[name] = original
        if cache:
            fullname = '%s.%s' % (self.name, name)
            if fullname in cache:
                value.set(cache[fullname])

    def registerGroup(self, name, group=None):
        original = name
        name = name.lower()
        if name in self.children:
            return # Ignore redundant group inserts.
        if group is None:
            group = Group()
        self.children[name] = group
        self.originals[name] = original
        fullname = '%s.%s' % (self.name, name)
        group.setName(fullname)
        if cache and fullname in cache:
            group.set(cache[fullname])

    def getValues(self, getChildren=False):
        L = []
        items = self.values.items()
        for (name, child) in self.children.items():
            if hasattr(child, 'value'):
                items.append((name, child))
        utils.sortBy(lambda (k, _): (k.lower(), len(k), k), items)
        for (name, value) in items:
            L.append(('%s.%s' % (self.getName(), self.originals[name]), value))
        if getChildren:
            items = self.children.items()
            utils.sortBy(lambda (k, _): (k.lower(), len(k), k), items)
            for (_, child) in items:
                L.extend(child.getValues(getChildren))
        return L
        

class GroupWithValue(Group):
    def __init__(self, value):
        Group.__init__(self)
        self.value = value
        self.help = value.help

    def set(self, s):
        self.value.set(s)

    def setValue(self, v):
        self.value.setValue(v)

    def reset(self):
        self.value.reset()

    def __call__(self):
        return self.value()

    def __str__(self):
        return str(self.value)


class GroupWithDefault(GroupWithValue):
    def __init__(self, value):
        GroupWithValue.__init__(self, value)
        
    def __makeChild(self, attr, s):
        v = copy.copy(self.value)
        v.set(s)
        self.register(attr, v)

    def __getattr__(self, attr):
        try:
            return GroupWithValue.__getattr__(self, attr)
        except NonExistentRegistryEntry:
            self.__makeChild(attr, str(self))
            return self.__getattr__(attr)

    def setName(self, name):
        GroupWithValue.setName(self, name)
        for (k, v) in cache.iteritems():
            if k.startswith(self.name):
                (_, group) = rsplit(k, '.', 1)
                self.__makeChild(group, v)

    def getValues(self, getChildren=False):
        L = GroupWithValue.getValues(self, getChildren)
        me = str(self)
        L = [v for v in L if str(v[1]) != me]
        return L


if __name__ == '__main__':
    import sys
    sys.setrecursionlimit(40)
    supybot = Group()
    supybot.setName('supybot')
    supybot.register('throttleTime', Float(1, """Determines the minimum
    number of seconds the bot will wait between sending messages to the server.
    """))
    supybot.registerGroup('plugins')
    supybot.plugins.registerGroup('topic')
    supybot.plugins.topic.registerGroup('separator',
      GroupWithDefault(StringSurroundedBySpaces(' || ',
      'Determines what separator the bot uses to separate topic entries.')))
    supybot.plugins.topic.separator.setChild('#supybot', ' |||| ')
    supybot.plugins.topic.separator.set(' <> ')

    supybot.throttleTime.set(10)

    supybot.registerGroup('log')
    supybot.log.registerGroup('stdout',
                              GroupWithValue(Boolean(False,
                                                     """Help for stdout.""")))
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

