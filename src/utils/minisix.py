###
# Copyright (c) 2014-2021, Valentin Lorentz
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

"""Restricted equivalent to six."""

from __future__ import division

import sys
import warnings

if sys.version_info[0] >= 3:
    PY2 = False
    PY3 = True
    intern = sys.intern
    integer_types = (int,)
    string_types = (str,)
    long = int

    import io
    import pickle
    import queue

    u = lambda x:x
    L = lambda x:x

    def make_datetime_utc(dt):
        import datetime
        return dt.replace(tzinfo=datetime.timezone.utc)
    def timedelta__totalseconds(td):
        return td.total_seconds()
    if sys.version_info >= (3, 3):
        def datetime__timestamp(dt):
            return dt.timestamp()
    else:
        def datetime__timestamp(dt):
            import datetime
            td = dt - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            return timedelta__totalseconds(td)
else:
    PY2 = True
    PY3 = False
    if isinstance(__builtins__, dict):
        intern = __builtins__['intern']
    else:
        intern = __builtins__.intern
    integer_types = (int, long)
    string_types = (basestring,)
    long = long

    class io:
        # cStringIO is buggy with Python 2.6 (
        # see http://paste.progval.net/show/227/ )
        # and it does not handle unicode objects in Python  2.x
        from StringIO import StringIO
        from cStringIO import StringIO as BytesIO
    import cPickle as pickle
    import Queue as queue

    u = lambda x:x.decode('utf8')
    L = lambda x:long(x)

    def make_datetime_utc(dt):
        warnings.warn('Timezones are not available on this version of '
                     'Python and may lead to incorrect results. You should '
                     'consider upgrading to Python 3.')
        return dt.replace(tzinfo=None)
    if sys.version_info >= (2, 7):
        def timedelta__totalseconds(td):
            return td.total_seconds()
    else:
        def timedelta__totalseconds(td):
            return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

    def datetime__timestamp(dt):
        import datetime
        warnings.warn('Timezones are not available on this version of '
                     'Python and may lead to incorrect results. You should '
                     'consider upgrading to Python 3.')
        return timedelta__totalseconds(dt - datetime.datetime(1970, 1, 1))
