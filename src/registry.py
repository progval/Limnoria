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

import utils


class RegistryException(Exception):
    pass

class InvalidRegistryValue(RegistryException):
    pass

class NonExistentRegistryEntry(RegistryException):
    pass

class Value(object):
    def __init__(self, default, help):
        self.help = utils.normalizeWhitespace(help)
        self.value = default

    def set(self, s):
        """Override this with a function to convert a string to whatever type
        you want, and set it to .value."""
        # self.value = value
        raise NotImplementedError
    
    def get(self):
        return self.value

    def __str__(self):
        return repr(self.value)

class Boolean(Value):
    def set(self, s):
        s = s.lower()
        if s in ('true', 'on', 'enabled'):
            self.value = True
        elif s in ('false', 'off', 'disabled'):
            self.value = False
        else:
            raise InvalidRegistryValue, 'Value must be True or False.'

class Integer(Value):
    def set(self, s):
        try:
            self.value = int(s)
        except ValueError:
            raise InvalidRegistryValue, 'Value must be an integer.'

class String(Value):
    def set(self, s):
        if s and s[0] not in '\'"' and s[-1] not in '\'"':
            s = repr(s)
        try:
            v = utils.safeEval(s)
            if type(v) is not str:
                raise ValueError
            self.value = v
        except ValueError: # This catches utils.safeEval(s) errors too.
            raise InvalidRegistryValue, 'Value must be a string.'

class StringSurroundedBySpaces(String):
    def set(self, s):
        String.set(self, s)
        if self.value.lstrip() == self.value:
            self.value = ' ' + self.value
        if self.value.rstrip() == self.value:
            self.value += ' '
            

class Group(object):
    def __init__(self):
        self.__dict__['name'] = 'unset'
        self.__dict__['values'] = {}
        self.__dict__['children'] = {}
        self.__dict__['originals'] = {}

    def __nonExistentEntry(self, attr):
        s = '%s is not a valid entry in %s' % (attr, self.name)
        raise NonExistentRegistryEntry, s

    def __getattr__(self, attr):
        original = attr
        attr = attr.lower()
        if attr in self.values:
            return self.values[attr].get()
        elif attr in self.children:
            return self.children[attr]
        else:
            self.__nonExistentEntry(original)
            
    def __setattr__(self, attr, s):
        original = attr
        attr = attr.lower()
        if attr in self.values:
            self.values[attr].set(s)
        elif attr in self.children and hasattr(self.children[attr], 'set'):
            self.children[attr].set(s)
        else:
            self.__nonExistentEntry(original)

    def get(self, attr):
        return self.__getattr__(attr)

    def help(self, attr):
        original = attr
        attr = attr.lower()
        if attr in self.values:
            return self.values[attr].help
        elif attr in self.children and hasattr(self.children[attr], 'help'):
            return self.children[attr].help
        else:
            self.__nonExistentEntry(original)
    
    def setName(self, name):
        self.__dict__['name'] = name

    def getName(self):
        return self.__dict__['name']

    def register(self, name, value):
        original = name
        name = name.lower()
        if name in self.values:
            value.set(str(self.values[name]))
        self.values[name] = value
        self.originals[name] = original

    def registerGroup(self, name, group=None):
        original = name
        name = name.lower()
        if group is None:
            group = Group()
        if name in self.children:
            group.__dict__['values'] = self.children[name].values
            group.__dict__['children'] = self.children[name].children
        self.children[name] = group
        self.originals[name] = original
        group.setName('%s.%s' % (self.name, name))

    def getValues(self):
        L = []
        items = self.values.items()
        items.sort()
        for (name, value) in items:
            L.append(('%s.%s' % (self.getName(), name), str(value)))
        items = self.children.items()
        items.sort()
        for (_, child) in items:
            L.extend(child.getValues())
        return L
        

class GroupWithDefault(Group):
    def __init__(self, value):
        Group.__init__(self)
        self.__dict__['value'] = value
        self.__dict__['help'] = value.help
        
    def __getattr__(self, attr):
        try:
            return Group.__getattr__(self, attr)
        except NonExistentRegistryEntry:
            return self.value.get()

    def __setattr__(self, attr, s):
        try:
            Group.__setattr__(self, attr, s)
        except NonExistentRegistryEntry:
            v = copy.copy(self.value)
            v.set(s)
            self.register(attr, v)

    def set(self, *args):
        if len(args) == 1:
            self.value.set(args[0])
        else:
            assert len(args) == 2
            (attr, s) = args
            self.__setattr__(attr, s)

    def getValues(self):
        L = Group.getValues(self)
        L.insert(0, (self.getName(), str(self.value)))
        return L



if __name__ == '__main__':
    supybot = Group()
    supybot.setName('supybot')
    supybot.register('throttleTime', Integer(1, """Determines the minimum
    number of seconds the bot will wait between sending messages to the server.
    """))
    supybot.registerGroup('plugins')
    supybot.plugins.registerGroup('topic')
    supybot.plugins.topic.registerGroup('separator',
      GroupWithDefault(StringSurroundedBySpaces(' || ',
      'Determines what separator the bot uses to separate topic entries.')))
    supybot.plugins.topic.separator.set('#supybot', ' |||| ')
    supybot.plugins.topic.separator.set(' <> ')

    for (k, v) in supybot.getValues():
        print '%s: %s' % (k, v)

    print supybot.help('throttleTime')
    print supybot.plugins.topic.help('separator')
    

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

