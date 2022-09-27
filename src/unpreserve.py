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

class Reader(object):
    """Opens a file and reads it in blocks, using the `Creator` class to
    instantiate an object for each of the blocks.

    The format is of the form:

    ```
    entry_type entry_id1
      command1 arg1 arg1b
      command2 arg2

    entry_type entry_id2
      command3 arg3 arg13
    ```

    When reading this file, the `Creator` will be instantiated with the
    provided args and kwargs to a `creator` object, whose methods will then
    be called in this pattern:

    ```
    creator.entry_type("entry_id1", 1)
    creator.command1("arg1 arg1b", 2)
    creator.command2("arg2", 3)
    creator.finish()

    creator.entry_type'entry_id2", 5)
    creator.command3("arg3 arg3b", 6)
    creator.finish()
    ```
    """
    def __init__(self, Creator, *args, **kwargs):
        self.Creator = Creator
        self.args = args
        self.kwargs = kwargs
        self.creator = None
        self.modifiedCreator = False
        self.indent = None

    def normalizeCommand(self, s):
        return s.lower()

    def readFile(self, filename):
        self.read(open(filename, encoding='utf8'))

    def read(self, fd):
        lineno = 0
        for line in fd:
            lineno += 1
            if not line.strip():
                continue
            line = line.rstrip('\r\n')
            line = line.expandtabs()
            s = line.lstrip(' ')
            indent = len(line) - len(s)
            if indent != self.indent:
                # New indentation level.
                if self.creator is not None:
                    self.creator.finish()
                self.creator = self.Creator(*self.args, **self.kwargs)
                self.modifiedCreator = False
                self.indent = indent
            (command, rest) = s.split(None, 1)
            command = self.normalizeCommand(command)
            self.modifiedCreator = True
            if hasattr(self.creator, command):
                command = getattr(self.creator, command)
                command(rest, lineno)
            else:
                self.creator.badCommand(command, rest, lineno)
        if self.modifiedCreator:
            self.creator.finish()


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

