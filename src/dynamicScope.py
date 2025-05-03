###
# Copyright (c) 2004-2005, Jeremiah Fincher
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

import logging
import sys

class DynamicScope(object):
    def _getLocals(self, name):
        f = sys._getframe().f_back.f_back # _getLocals <- __[gs]etattr__ <- ...
        while f:
            if name in f.f_locals:
                return f.f_locals
            f = f.f_back
        raise NameError(name)
    
    def __getattr__(self, name):
        try:
            return self._getLocals(name)[name]
        except (NameError, KeyError):
            return None
            
    def __setattr__(self, name, value):
        self._getLocals(name)[name] = value

class _DynamicScopeBuiltinsWrapper(DynamicScope):
    def __getattr__(self, name):
        _logger = logging.getLogger('supybot')
        _logger.warning('Using DynamicScope without an explicit import is '
                        'deprecated and will be removed in a future Limnoria '
                        'version. Use instead: '
                        'from supybot.dynamicScope import dynamic',
                        stacklevel=2, stack_info=True)
        return super().__getattr__(name)

dynamic = DynamicScope()
(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__)['dynamic'] = \
    _DynamicScopeBuiltinsWrapper()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
