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
import sets
import time
import string
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
            #print '***', repr(line)
            (key, value) = re.split(r'(?<!\\):', line, 1)
            key = key.strip()
            value = value.strip()
        except ValueError:
            raise InvalidRegistryFile, 'Error unpacking line %r' % line
        _cache[key] = value
    _lastModified = time.time()
    _fd.close()

def close(registry, filename, annotated=True, helpOnceOnly=False):
    first = True
    helpCache = sets.Set()
    fd = utils.transactionalFile(filename)
    for (name, value) in registry.getValues(getChildren=True):
        if annotated and hasattr(value,'help') and value.help:
            if not helpOnceOnly or value.help not in helpCache:
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
            fd.write('%s: %s\n' % (name, value))
    fd.close()

def isValidRegistryName(name):
    # Now we can have . and : in names.  I'm still gonna call shenanigans on
    # anyone who tries to have spaces (though technically I can't see any
    # reason why it wouldn't work).  We also reserve all names starting with
    # underscores for internal use.
    return len(name.split()) == 1 and not name.startswith('_')

def escape(name):
    name = name.replace('\\', '\\\\')
    name = name.replace(':', '\\:')
    name = name.replace('.', '\\.')
    return name

def unescape(name):
    name = name.replace('\\.', '.')
    name = name.replace('\\:', ':')
    name = name.replace('\\\\', '\\')
    return name

_splitRe = re.compile(r'(?<!\\)\.')
def split(name):
    return map(unescape, _splitRe.split(name))

def join(names):
    return '.'.join(map(escape, names))

class Group(object):
    """A group; it doesn't hold a value unless handled by a subclass."""
    def __init__(self, supplyDefault=False, orderAlphabetically=False):
        self._name = 'unset'
        self._added = []
        self._children = utils.InsensitivePreservingDict()
        self._lastModified = 0
        self._supplyDefault = supplyDefault
        self._orderAlphabetically = orderAlphabetically
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
        v._supplyDefault = False
        v.help = '' # Clear this so it doesn't print a bazillion times.
        self.register(attr, v)
        return v

    def __getattr__(self, attr):
        if attr in self._children:
            return self._children[attr]
        elif self._supplyDefault:
            return self.__makeChild(attr, str(self))
        else:
            self.__nonExistentEntry(attr)

    def get(self, attr):
        # Not getattr(self, attr) because some nodes might have groups that
        # are named the same as their methods.
        return self.__getattr__(attr)

    def setName(self, name):
        #print '***', name
        self._name = name
        if name in _cache and self._lastModified < _lastModified:
            #print '***>', _cache[name]
            self.set(_cache[name])
        if self._supplyDefault:
            for (k, v) in _cache.iteritems():
                if k.startswith(self._name):
                    rest = k[len(self._name)+1:] # +1 is for .
                    parts = split(rest)
                    if len(parts) == 1 and parts[0] == name:
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
        # We tried in any number of horrible ways to make it so that
        # re-registering something would work.  It doesn't, plain and simple.
        # For the longest time, we had an "Is this right?" comment here, but
        # from experience, we now know that it most definitely *is* right.
        if name not in self._children:
            self._children[name] = node
            self._added.append(name)
            names = split(self._name)
            names.append(name)
            fullname = join(names)
            node.setName(fullname)
        else:
            # We do this so the return value from here is at least useful;
            # otherwise, we're just returning a useless, unattached node
            # that's simply a waste of space.
            node = self._children[name]
        return node

    def unregister(self, name):
        try:
            node = self._children[name]
            del self._children[name]
            self._added.remove(name)
            if node._name in _cache:
                del _cache[node._name]
            return node
        except KeyError:
            self.__nonExistentEntry(name)

    def rename(self, old, new):
        node = self.unregister(old)
        self.register(new, node)

    def getValues(self, getChildren=False, fullNames=True):
        L = []
        if self._orderAlphabetically:
            self._added.sort()
        for name in self._added:
            node = self._children[name]
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
    def __init__(self, default, help, setDefault=True,
                 private=False, showDefault=True, **kwargs):
        self.__parent = super(Value, self)
        self.__parent.__init__(**kwargs)
        self._default = default
        self._private = private
        self.showDefault = showDefault
        self.help = utils.normalizeWhitespace(help.strip())
        if setDefault:
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
        self.__parent.setName(*args)
        self._lastModified = time.time()

    def set(self, s):
        """Override this with a function to convert a string to whatever type
        you want, and call self.setValue to set the value."""
        self.setValue(s)

    def setValue(self, v):
        """Check conditions on the actual value type here.  I.e., if you're a
        IntegerLessThanOneHundred (all your values must be integers less than
        100) convert to an integer in set() and check that the integer is less
        than 100 in this method.  You *must* call this parent method in your
        own setValue."""
        self._lastModified = time.time()
        self.value = v
        if self._supplyDefault:
            for (name, v) in self._children.items():
                if v.__class__ is self.X:
                    self.unregister(name)

    def __str__(self):
        return repr(self())

    # We tried many, *many* different syntactic methods here, and this one was
    # simply the best -- not very intrusive, easily overridden by subclasses,
    # etc.
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
        super(Boolean, self).setValue(bool(v))

class Integer(Value):
    """Value must be an integer."""
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            self.error()

class NonNegativeInteger(Integer):
    """Value must be a non-negative integer."""
    def setValue(self, v):
        if v < 0:
            self.error()
        super(NonNegativeInteger, self).setValue(v)

class PositiveInteger(NonNegativeInteger):
    """Value must be positive (non-zero) integer."""
    def setValue(self, v):
        if not v:
            self.error()
        super(PositiveInteger, self).setValue(v)

class Float(Value):
    """Value must be a floating-point number."""
    def set(self, s):
        try:
            self.setValue(float(s))
        except ValueError:
            self.error()

    def setValue(self, v):
        try:
            super(Float, self).setValue(float(v))
        except ValueError:
            self.error()

class PositiveFloat(Float):
    """Value must be a float-point number greater than zero."""
    def setValue(self, v):
        if v <= 0:
            self.error()
        else:
            super(PositiveFloat, self).setValue(v)

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

    _printable = string.printable[:-4]
    def _needsQuoting(self, s):
        return s.translate(string.ascii, self._printable) and s.strip() != s
               
    def __str__(self):
        s = self.value
        if self._needsQuoting(s):
            s = repr(s)
        return s

class OnlySomeStrings(String):
    validStrings = ()
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        self.__parent = super(OnlySomeStrings, self)
        self.__parent.__init__(*args, **kwargs)

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
            self.__parent.setValue(s)
        else:
            self.error()

class NormalizedString(String):
    def __init__(self, default, *args, **kwargs):
        default = self.normalize(default)
        self.__parent = super(NormalizedString, self)
        self.__parent.__init__(default, *args, **kwargs)
        
    def normalize(self, s):
        return utils.normalizeWhitespace(s.strip())
    
    def set(self, s):
        s = self.normalize(s)
        self.__parent.set(s)

    def setValue(self, s):
        s = self.normalize(s)
        self.__parent.setValue(s)

class StringSurroundedBySpaces(String):
    def setValue(self, v):
        if v.lstrip() == v:
            v= ' ' + v
        if v.rstrip() == v:
            v += ' '
        super(StringSurroundedBySpaces, self).setValue(v)

class StringWithSpaceOnRight(String):
    def setValue(self, v):
        if v.rstrip() == v:
            v += ' '
        super(StringWithSpaceOnRight, self).setValue(v)

class Regexp(Value):
    """Value must be a valid regular expression."""
    def __init__(self, *args, **kwargs):
        kwargs['setDefault'] = False
        super(Regexp, self).__init__(*args, **kwargs)
        
    def error(self, e):
        raise InvalidRegistryValue, 'Value must be a regexp of the form %s' % e

    def set(self, s):
        try:
            if s:
                self.setValue(utils.perlReToPythonRe(s), sr=s)
            else:
                self.setValue(None)
        except ValueError, e:
            self.error(e)

    def setValue(self, v, sr=None):
        parent = super(Regexp, self)
        if v is None:
            self.sr = ''
            parent.setValue(None)
        elif sr is not None:
            self.sr = sr
            parent.setValue(v)
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
            v = self.Value(s, '')
            L[i] = v()
        self.setValue(L)

    def setValue(self, v):
        super(SeparatedListOf, self).setValue(self.List(v))

    def __str__(self):
        values = self()
        if values:
            return self.joiner(values)
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

class SpaceSeparatedSetOfStrings(SpaceSeparatedListOfStrings):
    List = sets.Set

class CommaSeparatedListOfStrings(SeparatedListOf):
    Value = String
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:

