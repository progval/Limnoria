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

__revision__ = "$Id$"

import sys
import textwrap
from getpass import getpass as getPass

import ansi
import utils

useColor = False

def output(s, unformatted=True, useBold=False):
    if unformatted:
        s = textwrap.fill(utils.normalizeWhitespace(s))
    if useColor and useBold:
        sys.stdout.write(ansi.BOLD)
    print s
    if useColor and useBold:
        print ansi.RESET
    print

def expect(prompt, possibilities, recursed=False, doindent=True, default=None):
    """Prompt the user with prompt, allow them to choose from possibilities.

    If possibilities is empty, allow anything.
    """
    originalPrompt = prompt
    if doindent:
        indent = ' ' * ((len(originalPrompt)%68) + 2)
    else:
        indent = ''
    if recursed:
        output('Sorry, that response was not an option.', unformatted=False)
    if possibilities:
        prompt = '%s [%s]' % (originalPrompt, '/'.join(possibilities))
        if len(prompt) > 70:
            prompt = '%s [%s]' % (originalPrompt, '/ '.join(possibilities))
    if default is not None:
        prompt = '%s (default: %s)' % (prompt, default)
    prompt = textwrap.fill(prompt, subsequent_indent=indent)
    prompt = prompt.replace('/ ', '/')
    prompt = prompt.strip() + ' '
    if useColor:
        sys.stdout.write(ansi.BOLD)
    s = raw_input(prompt)
    if useColor:
        print ansi.RESET
    s = s.strip()
    if possibilities:
        if s in possibilities:
            return s
        elif not s and default is not None:
            return default
        else:
            return expect(originalPrompt, possibilities, recursed=True,
                          doindent=doindent, default=default)
    else:
        if not s and default is not None:
            return default
        return s.strip()

def anything(prompt):
    """Allow anything from the user."""
    return expect(prompt, [])

def something(prompt, default=None):
    """Allow anything *except* nothing from the user."""
    s = expect(prompt, [], default=default)
    while not s:
        output('Sorry, you must enter a value.', unformatted=False)
        s = expect(prompt, [], default=default)
    return s

def yn(prompt, default=None):
    """Allow only 'y' or 'n' from the user."""
    if default is not None:
        if default:
            default = 'y'
        else:
            default = 'n'
    s = expect(prompt, ['y', 'n'], doindent=False, default=default)
    if s is 'y':
        return True
    return False

def getpass(prompt='Enter password: '):
    """Prompt the user for a password."""
    password = ''
    password2 = ' '
    assert prompt
    if not prompt[-1].isspace():
        prompt += ' '
    while True:
        if useColor:
            sys.stdout.write(ansi.BOLD)
        password = getPass(prompt)
        password2 = getPass('Re-enter password: ')
        if useColor:
            print ansi.RESET
        if password != password2:
            output('Passwords don\'t match.', unformatted=False)
        else:
            break
    return password


# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
