###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

"""Handles interactive questions; useful for wizards and whatnot."""

from __future__ import print_function

import sys
import textwrap
from getpass import getpass as getPass

from . import ansi, utils
from .utils import minisix
from supybot.i18n import PluginInternationalization
_ = PluginInternationalization()

useBold = False

def output(s, unformatted=True, fd=sys.stdout):
    if unformatted:
        s = textwrap.fill(utils.str.normalizeWhitespace(s), width=65)
    print(s, file=fd)
    print('', file=fd)

def expect(prompt, possibilities, recursed=False, default=None,
           acceptEmpty=False, fd=sys.stdout):
    """Prompt the user with prompt, allow them to choose from possibilities.

    If possibilities is empty, allow anything.
    """
    prompt = utils.str.normalizeWhitespace(prompt)
    originalPrompt = prompt
    if recursed:
        output(_('Sorry, that response was not an option.'))
    if useBold:
        choices = '[%s%%s%s]' % (ansi.RESET, ansi.BOLD)
    else:
        choices = '[%s]'
    if possibilities:
        prompt = '%s %s' % (originalPrompt, choices % '/'.join(possibilities))
        if len(prompt) > 70:
            prompt = '%s %s' % (originalPrompt, choices % '/ '.join(possibilities))
    if default is not None:
        if useBold:
            prompt = '%s %s(default: %s)' % (prompt, ansi.RESET, default)
        else:
            prompt = '%s (default: %s)' % (prompt, default)
    prompt = textwrap.fill(prompt)
    prompt = prompt.replace('/ ', '/')
    prompt = prompt.strip() + ' '
    if useBold:
        prompt += ansi.RESET
        print(ansi.BOLD, end=' ', file=fd)
    if minisix.PY3:
        s = input(prompt)
    else:
        s = raw_input(prompt)
    s = s.strip()
    print(file=fd)
    if possibilities:
        if s in possibilities:
            return s
        elif not s and default is not None:
            return default
        elif not s and acceptEmpty:
            return s
        else:
            return expect(originalPrompt, possibilities, recursed=True,
                          default=default)
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
        output(_('Sorry, you must enter a value.'))
        s = expect(prompt, [], default=default)
    return s

def yn(prompt, default=None):
    """Allow only 'y' or 'n' from the user."""
    if default is not None:
        if default:
            default = 'y'
        else:
            default = 'n'
    s = expect(prompt, ['y', 'n'], default=default)
    if s == 'y':
        return True
    else:
        return False

def getpass(prompt=None, secondPrompt=None):
    """Prompt the user for a password."""
    if prompt is None:
        prompt = _('Enter password: ')
    if secondPrompt is None:
        secondPrompt = _('Re-enter password: ')
    password = ''
    secondPassword = ' ' # Note that this should be different than password.
    assert prompt
    if not prompt[-1].isspace():
        prompt += ' '
    while True:
        if useBold:
            prompt = ansi.BOLD + prompt + ansi.RESET
            secondPrompt = ansi.BOLD + secondPrompt + ansi.RESET
        password = getPass(prompt)
        secondPassword = getPass(secondPrompt)
        if password != secondPassword:
            output(_('Passwords don\'t match.'))
        else:
            break
    print('')
    return password


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
