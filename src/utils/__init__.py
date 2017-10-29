###
# Copyright (c) 2002-2005, Jeremiah Fincher
# Copyright (c) 2008, James McCoy
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

from . import minisix

###
# csv.{join,split} -- useful functions that should exist.
###
import csv
def join(L):
    fd = minisix.io.StringIO()
    writer = csv.writer(fd)
    writer.writerow(L)
    return fd.getvalue().rstrip('\r\n')

def split(s):
    fd = minisix.io.StringIO(s)
    reader = csv.reader(fd)
    return next(reader)
csv.join = join
csv.split = split

builtins = (__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)

# We use this often enough that we're going to stick it in builtins.
def force(x):
    if callable(x):
        return x()
    else:
        return x
builtins['force'] = force

internationalization = builtins.get('supybotInternationalization', None)

# These imports need to happen below the block above, so things get put into
# __builtins__ appropriately.
from .gen import *
from . import crypt, error, file, iter, net, python, seq, str, transaction, web

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
