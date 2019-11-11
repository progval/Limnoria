# -*- coding: utf-8 -*-
###
# Copyright (c) 2002-2005, Jeremiah Fincher
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

from . import dynamicScope

from . import i18n

builtins = (__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)
builtins['supybotInternationalization'] = i18n.PluginInternationalization()
from . import utils
del builtins['supybotInternationalization']

(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)['format'] = utils.str.format

class Author(object):
    """
    Describes a plugin author. All fields are optional, but the standard practice
    is to include an email and at least one of 'name' and 'nick'.
    """
    def __init__(self, name=None, nick=None, email=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.nick = nick
        self.email = email

    def format(self, short=False):
        # If only one of these are defined, take the nick as the name
        name = self.name or self.nick or 'Unknown author'

        s = name
        if self.nick and name != self.nick:
            # Format as "Name (nick)" if both are given and different
            s += ' (%s)' % self.nick
        if self.email and not short:
            # Add "Name (nick) <email>" or "Name <email>" if provided
            s += ' <%s>' % self.email
        return s

    def __str__(self):
        return self.format()

class authors(object): # This is basically a bag.
    jemfinch = Author('Jeremy Fincher', 'jemfinch', 'jemfinch@users.sf.net')
    jamessan = Author('James McCoy', 'jamessan', 'vega.james@gmail.com')
    strike = Author('Daniel DiPaolo', 'Strike', 'ddipaolo@users.sf.net')
    baggins = Author('William Robinson', 'baggins', 'airbaggins@users.sf.net')
    skorobeus = Author('Kevin Murphy', 'Skorobeus', 'skoro@skoroworld.com')
    inkedmn = Author('Brett Kelly', 'inkedmn', 'inkedmn@users.sf.net')
    bwp = Author('Brett Phipps', 'bwp', 'phippsb@gmail.com')
    bear = Author('Mike Taylor', 'bear', 'bear@code-bear.com')
    grantbow = Author('Grant Bowman', 'Grantbow', 'grantbow@grantbow.com')
    stepnem = Author('Štěpán Němec', 'stepnem', 'stepnem@gmail.com')
    progval = Author('Valentin Lorentz', 'ProgVal', 'progval@gmail.com')
    jlu = Author('James Lu', email='james@overdrivenetworks.com')
    unknown = Author('Unknown author', email='unknown@email.invalid')

    # Set as __maintainer__ field for all built-in plugins
    limnoria_core = Author('Limnoria contributors')

    # Let's be somewhat safe about this.
    def __getattr__(self, attr):
        try:
            return getattr(super(authors, self), attr.lower())
        except AttributeError:
            return self.unknown

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
