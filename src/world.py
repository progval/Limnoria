#!/usr/bin/env python

###
# Copyright (c) 2002, Jeremiah Fincher
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

from fix import *

import os
import gc
import time
import copy
import types
import string
import atexit
import linecache
try:
    import msvcrt
except ImportError:
    pass

import conf
import debug

# version: The version of the bot.
version = '0.70.0'

startedAt = 0.0

threadsSpawned = 0
###
# End Global Values.
###

try:
    ignore(ircs)
except NameError:
    ircs = []

try:
    ignore(flushers)
except NameError:
    flushers = [] # A periodic function will flush all these.

def flush():
    for f in flushers:
        f()

atexit.register(flush)

try:
    ignore(tempvars)
except NameError:
    tempvars = {} # A storage place for temporary variables that need to be
                  # globally accessible.


def upkeep(): # Function to be run on occasion to do upkeep stuff.
    gc.collect()
    if os.name == 'nt':
        msvcrt.heapmin()
    if gc.garbage:
        debug.msg('Uncollectable garbage: %s' % gc.garbage, 'normal')
    if 'noflush' not in tempvars:
        flush()
    msg = '%s upkeep ran.' % time.strftime(conf.timestampFormat)
    debug.msg(msg, 'verbose')

'''
def superReload(oldmodule):
    ###
    # So here's how this baby works:
    #   Reload the module.
    #   Iterate through the old module, finding classes and functions that are
    #     also in the new module.
    #   Add an __getattribute__ or __getattr__ method to those classes that are
    #     present in the new module.  This method will, when called, change
    #     the instance's __class__ to point to the new class.
    #   Change the func_code, func_defaults, and func_doc of any functions or
    #     methods or generators we run across, just in case someone's holding
    #     a reference to them instead of calling them by name.
    ###
    """Reload a module and make objects auto-update."""
    # reload(module) modifies module in-place, so we need a copy of its
    # __dict__ to iterate through.
    olddict = copy.copy(oldmodule.__dict__)
    newmodule = reload(oldmodule)
    newdict = newmodule.__dict__
    for (name, oldvalue) in olddict.iteritems():
        if name in newdict:
            newvalue = newdict[name]
            oldtype = type(oldvalue)
            # We have to pass in newvalue because of Python's scoping.
            def updater(self, s, newvalue=newvalue):
                # This function is to be an __getattr__ or __getattribute__.
                try:
                    self.__class__ = newvalue
                except:
                    debug.recoverableException()
                    try:
                        del self.__class__.__getattribute__
                    except AttributeError:
                        del self.__class__.__getattr__
                return getattr(self, s)
            if oldtype == types.TypeType and \
               oldvalue.__module__ == newmodule.__name__:
                # New-style classes support __getattribute__, which is
                # called on *any* attribute access, so they get updated
                # the first time they're used after a reload.
                if not (issubclass(oldvalue, str) or \
                        issubclass(oldvalue, long) or \
                        issubclass(oldvalue, tuple)):
                    oldvalue.__getattribute__ = updater
            elif oldtype == types.ClassType and\
                 oldvalue.__module__ == newmodule.__name__:
                # Old-style classes can only use getattr, so they might not
                # update right away.  Hopefully they will, but to solve
                # this problem I just use new-style classes.
                oldvalue.__getattr__ = updater
            elif oldtype == type(newvalue):
                if oldtype == types.FunctionType or\
                   oldtype == types.GeneratorType:
                    oldvalue.func_code = newvalue.func_code
                    oldvalue.func_defaults = newvalue.func_defaults
                    oldvalue.func_doc = newvalue.func_doc
                elif oldtype == types.MethodType:
                    oldfunc = oldvalue.im_func
                    newfunc = newvalue.im_func
                    oldfunc.func_code = newfunc.func_code
                    oldfunc.func_defaults = newfunc.func_defaults
                    oldfunc.func_doc = newfunc.func_doc
    # Update the linecache, so tracebacks show the proper lines.
    linecache.checkcache()
    return newmodule
'''

try:
    # This makes the module reload properly; we don't want to lose oldobjects
    # on reload.
    oldobjects
except NameError:
    oldobjects = {}
def superReload(module):
    def updateFunction(old, new, attrs):
        """Update all attrs in old to the same attrs in new."""
        for name in attrs:
            setattr(old, name, getattr(new, name))

    for (name, object) in module.__dict__.iteritems():
        # For every attribute of the old module, keep the object.
        key = (module.__name__, name)
        oldobjects.setdefault(key, []).append(object)
    module = reload(module)
    for name, newobj in module.__dict__.iteritems():
        # For every attribute in the new module...
        key = (module.__name__, name)
        if key in oldobjects: # If the same attribute was in the old module...
            for oldobj in oldobjects[key]:
                # Give it the new attributes :)
                if type(newobj) == types.ClassType:
                    toRemove = []
                    for k in oldobj.__dict__:
                        if k not in newobj.__dict__:
                            toRemove.append(k)
                    for k in toRemove:
                        del oldobj.__dict__[k]
                    oldobj.__dict__.update(newobj.__dict__)
#                elif type(newobj) == types.TypeType:
#                    if hasattr(oldobj, '__dict__'):
#                        oldobj.__dict__.update(newobj.__dict__)
                elif type(newobj) == types.FunctionType:
                    updateFunction(oldobj, newobj, ('func_code',
                                                    'func_defaults',
                                                    'func_doc'))
                elif type(newobj) == types.MethodType:
                    updateFunction(oldobj.im_func, newobj.im_func,
                                  ('func_code', 'func_defaults', 'func_doc'))
    return module

#################################################
#################################################
#################################################
## Don't even *think* about messing with this. ##
#################################################
#################################################
#################################################
startup = False
testing = False

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
