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

"""Handles interactive questions; useful for wizards and whatnot."""

import textwrap
from getpass import getpass as getPass

def expect(prompt, possibilities, recursed=False, doindent=True):
    """Prompt the user with prompt, allow them to choose from possibilities.

    If possibilities is empty, allow anything.
    """
    originalPrompt = prompt
    if doindent:
        indent = ' ' * ((len(originalPrompt)%68) + 2)
    else:
        indent = ''
    if recursed:
        print 'Sorry, that response was not an option.'
    if possibilities:
        prompt = '%s [%s]' % (originalPrompt, '/'.join(possibilities))
        if len(prompt) > 70:
            prompt = '%s [%s]' % (originalPrompt, '/ '.join(possibilities))
            prompt = textwrap.fill(prompt, subsequent_indent=indent)
    else:
        prompt = textwrap.fill(prompt)
    prompt = prompt.replace('/ ', '/')
    prompt = prompt.strip() + ' '
    s = raw_input(prompt)
    s = s.strip()
    if possibilities:
        if s in possibilities:
            return s
        else:
            return expect(originalPrompt, possibilities, recursed=True,
                          doindent=doindent)
    else:
        return s.strip()

def expectWithDefault(prompt, possibilities, default):
    """Same as expect, except with a default."""
    indent = ' ' * ((len(prompt)%68) + 2)
    prompt = '%s [%s] (default: %s) ' % \
             (prompt.strip(), '/'.join(possibilities), default)
    if len(prompt) > 70:
        prompt = '%s [%s] (default: %s) ' % \
                 (prompt.strip(), ' / '.join(possibilities), default)
    prompt = textwrap.fill(prompt, subsequent_indent=indent)
    s = raw_input(prompt)
    s = s.strip()
    if s in possibilities:
        return s
    else:
        return default

def anything(prompt):
    """Allow anything from the user."""
    return expect(prompt, [])

def something(prompt):
    """Allow anything *except* nothing from the user."""
    s = expect(prompt, [])
    while not s:
        print 'Sorry, you must enter a value.'
        s = expect(prompt, [])
    return s

def yn(prompt):
    """Allow only 'y' or 'n' from the user."""
    return expect(prompt, ['y', 'n'], doindent=False)

def getpass(prompt='Enter password: '):
    password = ''
    password2 = ' '
    assert prompt
    if not prompt[-1].isspace():
        prompt += ' '
    while True:
        password = getPass(prompt)
        password2 = getPass('Re-enter password: ')
        if password != password2:
            print 'Passwords don\'t match.'
        else:
            break
    return password


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
