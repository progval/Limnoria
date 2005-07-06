###
# Copyright (c) 2005, Jeremiah Fincher
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

"""
Defines a Transaction class for multi-file transactions.
"""

import os
import shutil
import os.path

import error
import python
import file as File

# 'txn' is used as an abbreviation for 'transaction' in the following source.

class FailedAcquisition(error.Error):
    def __init__(self, txnDir, e=None):
        self.txnDir = txnDir
        msg = 'Could not acquire transaction directory: %s.' % self.txnDir
        error.Error.__init__(self, msg, e)
        
class InProgress(error.Error):
    def __init__(self, inProgress, e=None):
        self.inProgress = inProgress
        msg = 'Transaction appears to be in progress already: %s exists.' % \
              self.inProgress
        error.Error.__init__(self, msg, e)
        

class TransactionMixin(python.Object):
    JOURNAL = 'journal'
    ORIGINALS = 'originals'
    INPROGRESS = '.inProgress'
    REPLACEMENTS = 'replacements'
    # expects a self.dir.  used by Transaction and Rollback.
    def __init__(self, txnDir):
        self.txnDir = txnDir
        self.dir = self.txnDir + self.INPROGRESS
        self._journalName = self.dirize(self.JOURNAL)

    def escape(self, filename):
        return os.path.abspath(filename)[1:]
    
    def dirize(self, *args):
        return os.path.join(self.dir, *args)

    def _original(self, filename):
        return self.dirize(self.ORIGINALS, self.escape(filename))
    
    def _replacement(self, filename):
        return self.dirize(self.REPLACEMENTS, self.escape(filename))
    
    def _checkCwd(self):
        expected = File.contents(self.dirize('cwd'))
        if os.getcwd() != expected:
            raise InvalidCwd(expected)
        
    def _journalCommands(self):
        journal = file(self._journalName)
        for line in journal:
            line = line.rstrip('\n')
            (command, rest) = line.split(None, 1)
            args = rest.split()
            yield (command, args)
        

class Transaction(TransactionMixin):
    def __init__(self, *args, **kwargs):
        """Transaction(root, txnDir) -> None

        txnDir is the directory that will hold the transaction's working files
        and such.  If it can't be renamed, there is probably an active
        transaction.
        """
        TransactionMixin.__init__(self, *args, **kwargs)
        if os.path.exists(self.dir):
            raise InProgress(self.dir)
        if not os.path.exists(self.txnDir):
            raise FailedAcquisition(self.txnDir)
        try:
            os.rename(self.txnDir, self.dir)
        except EnvironmentError, e:
            raise TransactionAcquisitionFailure(self.txnDir, e)
        os.mkdir(self.dirize(self.ORIGINALS))
        os.mkdir(self.dirize(self.REPLACEMENTS))
        self._journal = file(self._journalName, 'a')
        cwd = file(self.dirize('cwd'), 'w')
        cwd.write(os.getcwd())
        cwd.close()

    def _journalCommand(self, command, *args):
        File.writeLine(self._journal,
                       '%s %s' % (command, ' '.join(map(str, args))))
        self._journal.flush()

    def _makeOriginal(self, filename):
        File.copy(filename, self._original(filename))

    def replace(self, filename):
        self._checkCwd()
        self._makeOriginal(filename)
        self._journalCommand('replace', filename)
        return File.open(self._replacement(filename))

    def append(self, filename):
        self._checkCwd()
        length = os.stat(filename).st_size
        self._journalCommand('append', filename, length)
        replacement = self._replacement(filename)
        File.copy(filename, replacement)
        return file(replacement, 'a')

    def commit(self, removeWhenComplete=True):
        self._journal.close()
        self._checkCwd()
        File.touch(self.dirize('commit'))
        for (command, args) in self._journalCommands():
            methodName = 'commit%s' % command.capitalize()
            getattr(self, methodName)(*args)
        File.touch(self.dirize('committed'))
        if removeWhenComplete:
            shutil.rmtree(self.dir)

    def commitReplace(self, filename):
        shutil.copy(self._replacement(filename), filename)

    def commitAppend(self, filename, length):
        shutil.copy(self._replacement(filename), filename)


class Rollback(TransactionMixin):
    def rollback(self, removeWhenComplete=True):
        self._checkCwd()
        if not os.path.exists(self.dirize('commit')):
            return # No action taken; commit hadn't begun.
        for (command, args) in self._journalCommands():
            methodName = 'rollback%s' % command.capitalize()
            getattr(self, methodName)(*args)
        if removeWhenComplete:
            shutil.rmtree(self.dir)

    def rollbackReplace(self, filename):
        shutil.copy(self._original(filename), filename)

    def rollbackAppend(self, filename, length):
        fd = file(filename, 'a')
        fd.truncate(int(length))
        fd.close()
        

# vim:set shiftwidth=4 tabstop=8 expandtab textwidth=78:
