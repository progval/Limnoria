###
# Copyright (c) 2004-2005, Jeremiah Fincher
# Copyright (c) 2009-2010, James McCoy
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

import re
import os
import time
import json
import codecs
import string
import textwrap

from . import utils, i18n, ircutils
from .utils import minisix
_ = i18n.PluginInternationalization()

def error(s):
   """Replace me with something better from another module!"""
   print('***', s)

def exception(s):
    """Ditto!"""
    print('***', s, 'A bad exception.')

class RegistryException(Exception):
    pass

class InvalidRegistryFile(RegistryException):
    pass

class InvalidRegistryName(RegistryException):
    pass

class InvalidRegistryValue(RegistryException):
    pass

class NonExistentRegistryEntry(RegistryException, AttributeError):
    # If we use hasattr() on a configuration group/value, Python 3 calls
    # __getattr__ and looks for an AttributeError, so __getattr__ has to
    # raise an AttributeError if a registry entry does not exist.
    pass

ENCODING = 'string_escape' if minisix.PY2 else 'unicode_escape'
decoder = codecs.getdecoder(ENCODING)
encoder = codecs.getencoder(ENCODING)

if hasattr(time, 'monotonic'):
    monotonic_time = time.monotonic
else:
    # fallback for python < 3.3
    monotonic_time = time.time

_cache = utils.InsensitivePreservingDict()
_lastModified = 0
def open_registry(filename, clear=False):
    """Initializes the module by loading the registry file into memory."""
    global _lastModified
    if clear:
        _cache.clear()
    _fd = open(filename)
    fd = utils.file.nonCommentNonEmptyLines(_fd)
    acc = ''
    slashEnd = re.compile(r'\\*$')
    for line in fd:
        line = line.rstrip('\r\n')
        # XXX There should be some way to determine whether or not we're
        #     starting a new variable or not.  As it is, if there's a backslash
        #     at the end of every line in a variable, it won't be read, and
        #     worse, the error will pass silently.
        #
        # If the line ends in an odd number of backslashes, then there is a
        # line-continuation.
        m = slashEnd.search(line)
        if m and len(m.group(0)) % 2:
            acc += line[:-1]
            continue
        else:
            acc += line
        try:
            (key, value) = re.split(r'(?<!\\): ', acc, 1)
            key = key.strip()
            value = value.strip('\r\n')
            value = decoder(value)[0]
            acc = ''
        except ValueError:
            raise InvalidRegistryFile('Error unpacking line %r' % acc)
        _cache[key] = value
    _lastModified = monotonic_time()
    _fd.close()

CONF_FILE_HEADER = """
######
# Although it is technically possible to do so, we do not recommend that
# you edit this file with a text editor.
# Whenever possible, do it on IRC using the Config plugin, which
# checks values you set are valid before writing them to the
# configuration.
# Moreover, if you edit this file while the bot is running, your
# changes may be lost.
######


"""

def close(registry, filename, private=True):
    first = True
    fd = utils.file.AtomicFile(filename)
    fd.write(CONF_FILE_HEADER)
    for (name, value) in registry.getValues(getChildren=True):
        help = value.help()
        if help:
            lines = textwrap.wrap(value._help)
            for (i, line) in enumerate(lines):
                lines[i] = '# %s\n' % line
            lines.insert(0, '###\n')
            if first:
                first = False
            else:
                lines.insert(0, '\n')
            if hasattr(value, 'value'):
                if value._showDefault:
                    lines.append('#\n')
                    try:
                        x = value.__class__(value._default, value._help)
                    except Exception as e:
                        exception('Exception instantiating default for %s:' %
                                  value._name)
                    try:
                        lines.append('# Default value: %s\n' % x)
                    except Exception:
                        exception('Exception printing default value of %s:' %
                                  value._name)
            lines.append('###\n')
            fd.writelines(lines)
        if hasattr(value, 'value'): # This lets us print help for non-values.
            try:
                if private or not value._private:
                    s = value.serialize()
                else:
                    s = 'CENSORED'
                fd.write('%s: %s\n' % (name, s))
            except Exception:
                exception('Exception printing value:')
    fd.close()

def isValidRegistryName(name):
    # Now we can have . and : in names.  I'm still gonna call shenanigans on
    # anyone who tries to have spaces (though technically I can't see any
    # reason why it wouldn't work).  We also reserve all names starting with
    # underscores for internal use.
    return len(name.split()) == 1 and not name.startswith('_')

def escape(name):
    name = encoder(name)[0].decode()
    name = name.replace(':', '\\:')
    name = name.replace('.', '\\.')
    return name

def unescape(name):
    name = name.replace('\\.', '.')
    name = name.replace('\\:', ':')
    name = decoder(name.encode())[0]
    return name

_splitRe = re.compile(r'(?<!\\)\.')
def split(name):
    return list(map(unescape, _splitRe.split(name)))

def join(names):
    return '.'.join(map(escape, names))

class Group(object):
    """A group; it doesn't hold a value unless handled by a subclass."""
    __slots__ = ('_help', '_name', '_added', '_children', '_lastModified',
            '_private', '_supplyDefault', '_orderAlphabetically', '_wasSet')
    def __init__(self, help='',
                 orderAlphabetically=True, private=False):
        self._help = utils.str.normalizeWhitespace(help)
        self._name = 'unset'
        self._added = []
        self._children = utils.InsensitivePreservingDict()
        self._lastModified = 0
        self._private = private
        self._supplyDefault = False  # It should only be true for Value
        self._orderAlphabetically = orderAlphabetically
        self._wasSet = True

    def __call__(self):
        raise ValueError('Groups have no value.')

    def __nonExistentEntry(self, attr):
        s = _('%r is not a valid entry in %r') % (attr, self._name)
        raise NonExistentRegistryEntry(s)

    def _makeChild(self, attr, s):
        raise NotImplementedError(
            'Group does not implement _makeChild; only Value does.')

    def __hasattr__(self, attr):
        return attr in self._children

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError('%s has no attribute %s' %
                (self.__class__.__name__, attr))
        elif attr in self._children:
            return self._children[attr]
        elif self._supplyDefault:
            return self._makeChild(attr, str(self))
        else:
            self.__nonExistentEntry(attr)

    def help(self):
        return i18n.PluginInternationalization().__call__(self._help)

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
            for (k, v) in _cache.items():
                if k.startswith(self._name):
                    rest = k[len(self._name)+1:] # +1 is for .
                    parts = split(rest)
                    if len(parts) == 1 and parts[0] == name:
                        try:
                            self._makeChild(name, v)
                        except InvalidRegistryValue:
                            # It's probably supposed to be registered later.
                            pass

    def register(self, name, node=None):
        if not isValidRegistryName(name):
            raise InvalidRegistryName(name)
        if node is None:
            node = Group(private=self._private)
        else:
            node._private = node._private or self._private
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
            # We do this in order to reload the help, if it changed.
            if node._help != '' and node._help != self._children[name]._help:
                self._children[name]._help = node._help
            # We do this so the return value from here is at least useful;
            # otherwise, we're just returning a useless, unattached node
            # that's simply a waste of space.
            node = self._children[name]
        return node

    def unregister(self, name):
        try:
            node = self._children[name]
            del self._children[name]
            # We do this because we need to remove case-insensitively.
            name = name.lower()
            for elt in reversed(self._added):
                if elt.lower() == name:
                    self._added.remove(elt)
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
                if node._wasSet:
                    L.append((node._name, node))
            if getChildren:
                L.extend(node.getValues(getChildren, fullNames))
        if not fullNames:
            L = [(split(s)[-1], node) for (s, node) in L]
        return L

class _NoValueGiven:
    # Special value for Value.error()
    pass

class Value(Group):
    """Invalid registry value.  If you're getting this message, report it,
    because we forgot to put a proper help string here."""
    __slots__ = ('__parent', '_default', '_showDefault', '_help', '_callbacks',
            'value', '_networkValue', '_channelValue', '_opSettable')
    def __init__(self, default, help, setDefault=True,
                 showDefault=True, **kwargs):
        self.__parent = super(Value, self)
        self.__parent.__init__(help, **kwargs)
        self._default = default
        self._showDefault = showDefault
        self._help = utils.str.normalizeWhitespace(help.strip())
        self._callbacks = []
        self._networkValue = False
        self._channelValue = False
        if setDefault:
            self.setValue(default)

    def _makeChild(self, attr, s):
        v = self.__class__(self._default, self._help)
        v.set(s)
        v._wasSet = False
        if self._networkValue and self._channelValue:
            # If this is both a network-specific and channel-specific value,
            # then the child is (only) channel-specific.
            v._networkValue = False
            v._channelValue = True
            v._supplyDefault = True
        else:
            # Otherwise, the child is neither network-specific or
            # channel-specific.
            v._supplyDefault = False
        v._help = '' # Clear this so it doesn't print a bazillion times.
        self.register(attr, v)
        return v

    def error(self, value=_NoValueGiven):
        if hasattr(self, 'errormsg') and value is not _NoValueGiven:
            try:
                s = self.errormsg % value
            except TypeError:
                s = self.errormsg
        elif self.__doc__:
            s = self.__doc__
        else:
            s = """%s has no docstring.  If you're getting this message,
            report it, because we forgot to put a proper help string here."""%\
            self._name
        e = InvalidRegistryValue(utils.str.normalizeWhitespace(s))
        e.value = self
        raise e

    def getSpecific(self, network=None, channel=None, check=True):
        """Gets the network-specific and/or channel-specific value of this
        Value.
        If `check=True` (the default), this will raise an error if `network`
        (resp. `channel`) is provided but this Value is not network-specific
        (resp. channel-specific). If `check=False`, then `network` and/or
        `channel` may be silently ignored.
        """
        if network and not self._networkValue:
            if check:
                raise NonExistentRegistryEntry('%s is not network-specific' %
                    self._name)
            else:
                network = None
        if channel and not self._channelValue:
            if check:
                raise NonExistentRegistryEntry('%s is not channel-specific' %
                    self._name)
            else:
                channel = None

        # It may seem weird to check channel/network validity here,
        # but we need to prevent plugins from passing garbage values.
        #
        # For example, LinkRelay has an inFilter() function that called
        # self.registryValue('...', msg.args[0]) no matter the command. This
        # means that, every time the bot sends a 'PING :<timestamp>' from to
        # network, LinkRelayed called
        # self.registryValue('...', '<timestamp>'), which calls this
        # function.
        #
        # We then get the proper group, and do .get('<timestamp>'), which
        # causes a new variable to be registered.
        # And if the values have a high cardinality (eg. with timestamps),
        # this creates *a lot* of values, thereby leaking megabytes of memory
        # a week.
        #
        # Ideally, we would want to not register these variables, but it's
        # complicated for multiple reasons, including:
        #
        # 1. if two plugins .get() them, store them for a little while, then
        #    both set them, we have to take care of it.
        # 2. if <group>.network.channel is modified, then we need to register
        #    both .channel and .network. (and what if two plugins are doing
        #    this concurrently with different channels?)
        # 3. we could also have a task run in the upkeep function, but we have
        #    issues again with plugins that keep a reference.
        #
        # All in all, this is not ideal, but afaict, this is the least bad
        # solution. And let's hope no one bruteforces valid channel names.
        # If you have a better solution, please let us know!
        #
        # Also, we're setting them to None instead of raising an error in
        # order not to break existing plugins.
        if channel and not ircutils.isChannel(channel):
            channel = None
        if network:
            from . import world  # put here to work around circular dependencies
            if world.getIrc(network) is None:
                network = None

        if network and channel:
            # The complicated case. We want a net+chan specific value,
            # which may come in three different ways:
            #
            # 1. it was set explicitly net+chan
            # 2. it's inherited from a net specific value (which may itself be
            #    inherited from the base value)
            # 3. it's inherited from the chan specific value (which is not a
            #    actually a parent in the registry tree, but we need this to
            #    load configuration from old bots).
            #
            # The choice between 2 and 3 is done by checking which of the
            # net-specific and chan-specific values was set explicitly by
            # a user/admin. In case both were, the net-specific value is used
            # (there is no particular reason for this, I just think it makes
            # more sense).
            network_value = self.get(':' + network)
            network_channel_value = network_value.get(channel)
            channel_value = self.get(channel)
            if network_value._wasSet or network_channel_value._wasSet:
                # cases 1 and 2
                return network_channel_value
            else:
                # case 3
                return channel_value
        elif network:
            return self.get(':' + network)
        elif channel:
            return self.get(channel)
        else:
            return self

    def setName(self, *args):
        if self._name == 'unset':
            self._lastModified = 0
        self.__parent.setName(*args)
        self._lastModified = monotonic_time()

    def set(self, s):
        """Override this with a function to convert a string to whatever type
        you want, and call self.setValue to set the value."""
        self.setValue(s)

        # redundant as setValue() already sets it, but it avoids really hard
        # bugs if subclasses mess with _setValue.
        self._wasSet = True

    def setValue(self, v):
        """Check conditions on the actual value type here.  I.e., if you're a
        IntegerLessThanOneHundred (all your values must be integers less than
        100) convert to an integer in set() and check that the integer is less
        than 100 in this method.  You *must* call this parent method in your
        own setValue."""
        self._setValue(v, inherited=False)

    def _setValue(self, v, inherited):
        """Like setValue, but accepted an extra 'inherited' argument.
        inherited=True means the value is inherited from the parent, so if
        the parent gets a new value, this group will get the new value as
        well."""
        self._lastModified = monotonic_time()
        self.value = v
        if self._supplyDefault:
            for (name, child) in list(self._children.items()):
                if not child._wasSet:
                    child._setValue(v, inherited=True)
        # We call the callback once everything is clean
        for callback, args, kwargs in self._callbacks:
            callback(*args, **kwargs)
        self._wasSet = not inherited

    def context(self, value):
        """Return a context manager object, which sets this variable to a
        temporary value, and set the previous value back when exiting the
        context."""
        class Context:
            def __enter__(self2):
                self2._old_value = self.value
                self.setValue(value)
            def __exit__(self2, exc_type, exc_value, traceback):
                self.setValue(self2._old_value)
        return Context()

    def addCallback(self, callback, *args, **kwargs):
        """Add a callback to the list. A callback is a function that will be
        called when the value is changed. You can give this function as many
        extra arguments as you wish, they will be passed to the callback."""
        self._callbacks.append((callback, args, kwargs))

    def removeCallback(self, callback):
        """Remove all occurences of this callbacks from the callback list."""
        self._callbacks = [x for x in self._callbacks if x[0] is not callback]

    def __str__(self):
        return repr(self())

    def serialize(self):
        return encoder(str(self))[0].decode()

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
    __slots__ = ()
    errormsg = _('Value must be either True or False (or On or Off), not %r.')
    def set(self, s):
        try:
            v = utils.str.toBool(s)
        except ValueError:
            if s.strip().lower() == 'toggle':
                v = not self.value
            else:
                self.error(s)
        self.setValue(v)

    def setValue(self, v):
        super(Boolean, self).setValue(bool(v))

class Integer(Value):
    """Value must be an integer."""
    __slots__ = ()
    errormsg = _('Value must be an integer, not %r.')
    def set(self, s):
        try:
            self.setValue(int(s))
        except ValueError:
            self.error(s)

class NonNegativeInteger(Integer):
    """Value must be a non-negative integer."""
    __slots__ = ()
    errormsg = _('Value must be a non-negative integer, not %r.')
    def setValue(self, v):
        if v < 0:
            self.error(v)
        super(NonNegativeInteger, self).setValue(v)

class PositiveInteger(NonNegativeInteger):
    """Value must be positive (non-zero) integer."""
    __slots__ = ()
    errormsg = _('Value must be positive (non-zero) integer, not %r.')
    def setValue(self, v):
        if not v:
            self.error(v)
        super(PositiveInteger, self).setValue(v)

class Float(Value):
    """Value must be a floating-point number."""
    __slots__ = ()
    errormsg = _('Value must be a floating-point number, not %r.')
    def set(self, s):
        try:
            self.setValue(float(s))
        except ValueError:
            self.error(s)

    def setValue(self, v):
        try:
            super(Float, self).setValue(float(v))
        except ValueError:
            self.error(v)

class PositiveFloat(Float):
    """Value must be a floating-point number greater than zero."""
    __slots__ = ()
    errormsg = _('Value must be a floating-point number greater than zero, '
            'not %r.')
    def setValue(self, v):
        if v <= 0:
            self.error(v)
        else:
            super(PositiveFloat, self).setValue(v)

class Probability(Float):
    """Value must be a floating point number in the range [0, 1]."""
    __slots__ = ('__parent',)
    errormsg = _('Value must be a floating point number in the range [0, 1], '
            'not %r.')
    def __init__(self, *args, **kwargs):
        self.__parent = super(Probability, self)
        self.__parent.__init__(*args, **kwargs)

    def setValue(self, v):
        if 0 <= v <= 1:
            self.__parent.setValue(v)
        else:
            self.error(v)

class String(Value):
    """Value is not a valid Python string."""
    __slots__ = ()
    errormsg = _('Value should be a valid Python string, not %r.')
    def set(self, s):
        v = s
        if not v:
            v = '""'
        elif v[0] != v[-1] or v[0] not in '\'"':
            v = repr(v)
        try:
            v = utils.safeEval(v)
            if not isinstance(v, minisix.string_types):
                raise ValueError
            self.setValue(v)
        except ValueError: # This catches utils.safeEval(s) errors too.
            self.error(s)

    _printable = string.printable[:-4]
    def _needsQuoting(self, s):
        return any([x not in self._printable for x in s]) and s.strip() != s

    def __str__(self):
        s = self.value
        if self._needsQuoting(s):
            s = repr(s)
        return s

class OnlySomeStrings(String):
    __slots__ = ('__parent', '__dict__') # unfortunately, __dict__ is needed
                                         # to set __doc__.
    validStrings = ()
    def __init__(self, *args, **kwargs):
        assert self.validStrings, 'There must be some valid strings.  ' \
                                  'This is a bug.'
        self.__parent = super(OnlySomeStrings, self)
        self.__parent.__init__(*args, **kwargs)
        self.__doc__ = format(_('Valid values include %L.'),
                              list(map(repr, self.validStrings)))
        self.errormsg = format(_('Valid values include %L, not %%r.'),
                              list(map(repr, self.validStrings)))

    def help(self):
        strings = [s for s in self.validStrings if s]
        return format('%s  Valid strings: %L.', self._help, strings)

    def normalize(self, s):
        lowered = s.lower()
        L = list(map(str.lower, self.validStrings))
        try:
            i = L.index(lowered)
        except ValueError:
            return s # This is handled in setValue.
        return self.validStrings[i]

    def setValue(self, s):
        v = self.normalize(s)
        if s in self.validStrings:
            self.__parent.setValue(v)
        else:
            self.error(v)

class NormalizedString(String):
    __slots__ = ('__parent')
    def __init__(self, default, *args, **kwargs):
        default = self.normalize(default)
        self.__parent = super(NormalizedString, self)
        self.__parent.__init__(default, *args, **kwargs)
        self._showDefault = False

    def normalize(self, s):
        return utils.str.normalizeWhitespace(s.strip())

    def set(self, s):
        s = self.normalize(s)
        self.__parent.set(s)

    def setValue(self, s):
        s = self.normalize(s)
        self.__parent.setValue(s)

    def serialize(self):
        s = self.__parent.serialize()
        prefixLen = len(self._name) + 2
        lines = textwrap.wrap(s, width=76-prefixLen)
        last = len(lines)-1
        for (i, line) in enumerate(lines):
            if i != 0:
                line = ' '*prefixLen + line
            if i != last:
                line += '\\'
            lines[i] = line
        ret = os.linesep.join(lines)
        return ret

class StringSurroundedBySpaces(String):
    __slots__ = ()
    def setValue(self, v):
        if v and v.lstrip() == v:
            v= ' ' + v
        if v.rstrip() == v:
            v += ' '
        super(StringSurroundedBySpaces, self).setValue(v)

class StringWithSpaceOnRight(String):
    __slots__ = ()
    def setValue(self, v):
        if v and v.rstrip() == v:
            v += ' '
        super(StringWithSpaceOnRight, self).setValue(v)

class Regexp(Value):
    """Value must be a valid regular expression."""
    errormsg = _('Value must be a valid regular expression, not %r.')

    def __init__(self, default, *args, **kwargs):
        # We're not supposed to do convertions here, BUT this is needed
        # when the value is set programmatically because the value
        # plugins set (a string) is not the same as the one they get
        # (a compiled pattern object)
        default = self._convertFromString(default)
        super().__init__(default, *args, **kwargs)

    def error(self, e):
        s = 'Value must be a regexp of the form m/.../ or /.../. %s' % e
        e = InvalidRegistryValue(s)
        e.value = self
        raise e

    def _convertFromString(self, s):
        if s:
            # We need to preserve the original string, as it's shown in
            # the user interface and the config file.
            # It might be tempting to set the original string as an
            # attribute, but doing so would result in inconsistent states
            # for childs of this variable, should they be reset, or the
            # value of there parent change.
            return (s, utils.str.perlReToPythonRe(s))
        else:
            return None

    def set(self, s):
        try:
            v = self._convertFromString(s)
        except ValueError as e:
            self.error(e)
        else:
            super().set(v)

    def setValue(self, v):
        """Don't call this function directly from plugins, it is subject
        to change without notice."""
        if v is not None and (not isinstance(v, tuple) or len(v) != 2):
            raise InvalidRegistryValue(
                'Can\'t setValue a regexp, there would be an inconsistency '
                'between the regexp and the recorded string value. '
                'Use .set() instead.')

        super().setValue(v)

    def __call__(self):
        if self.value is None:
            return None
        else:
            return self.value[1]

    def __str__(self):
        if self.value is None:
            return ''
        else:
            return self.value[0]

class SeparatedListOf(Value):
    __slots__ = ()
    List = list
    Value = Value
    sorted = False
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
        if self.sorted:
            values = sorted(values)
        if values:
            return self.joiner(values)
        else:
            # We must return *something* here, otherwise down along the road we
            # can run into issues showing users the value if they've disabled
            # nick prefixes in any of the numerous ways possible.  Since the
            # config parser doesn't care about this space, we'll use it :)
            return ' '

class SpaceSeparatedListOf(SeparatedListOf):
    __slots__ = ()
    def splitter(self, s):
        return s.split()
    joiner = ' '.join

class SpaceSeparatedListOfStrings(SpaceSeparatedListOf):
    __slots__ = ()
    Value = String

class SpaceSeparatedSetOfStrings(SpaceSeparatedListOfStrings):
    __slots__ = ()
    List = set

class CommaSeparatedListOfStrings(SeparatedListOf):
    __slots__ = ()
    Value = String
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

class CommaSeparatedSetOfStrings(SeparatedListOf):
    __slots__ = ()
    List = set
    Value = String
    def splitter(self, s):
        return re.split(r'\s*,\s*', s)
    joiner = ', '.join

class TemplatedString(String):
    __slots__ = ()
    requiredTemplates = []
    def __init__(self, *args, **kwargs):
        assert self.requiredTemplates, \
               'There must be some templates.  This is a bug.'
        self.__parent = super(String, self)
        self.__parent.__init__(*args, **kwargs)

    def setValue(self, v):
        def hasTemplate(s):
            return re.search(r'\$%s\b|\${%s}' % (s, s), v) is not None
        if utils.iter.all(hasTemplate, self.requiredTemplates):
            self.__parent.setValue(v)
        else:
            self.error(v)

class Json(String):
    __slots__ = ()
    # Json-serializable data
    def set(self, v):
        self.setValue(json.loads(v))
    def setValue(self, v):
        super(Json, self).setValue(json.dumps(v))
    def __call__(self):
        return json.loads(super(Json, self).__call__())

    class _Context:
        def __init__(self, var):
            self._var = var
        def __enter__(self):
            self._dict = self._var()
            return self._dict
        def __exit__(self, *args):
            self._var.setValue(self._dict)

    def editable(self):
        """Return an editable dict usable within a 'with' statement and
        committed to the configuration variable at the end."""
        return self._Context(self)

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
