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

import textwrap

def expect(prompt, possibilities, recursed=False):
    originalPrompt = prompt
    if recursed:
        print 'Sorry, that response was not an option.'
    if possibilities:
        prompt = '%s [%s]' % (originalPrompt, '/'.join(possibilities))
    if len(prompt) > 70:
        prompt = '%s [%s]' % (originalPrompt, '/ '.join(possibilities))
    indent = ' ' * (len(originalPrompt) + 2)
    prompt = textwrap.fill(prompt, subsequent_indent=indent)
    prompt = prompt.replace('/ ', '/')
    prompt = prompt.strip() + ' '
    s = raw_input(prompt)
    s = s.strip()
    if possibilities:
        if s in possibilities:
            return s
        else:
            return expect(originalPrompt, possibilities, recursed=True)
    else:
        return s.strip()

def expectWithDefault(prompt, possibilities, default):
    indent = ' ' * (len(prompt) + 2)
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
    return expect(prompt, [])

def something(prompt):
    s = expect(prompt, [])
    while not s:
        print 'Sorry, you must enter a value.'
        s = expect(prompt, [])
    return s

def yn(prompt):
    return expect(prompt, ['y', 'n'])

def ny(prompt):
    return expect(prompt, ['n', 'y'])

def quit(prompt):
    return anything(prompt).lower() in ('q', 'quit')
