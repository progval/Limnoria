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

import os
import time
import codecs
import random
import shutil
import os.path

from . import crypt

def sanitizeName(filename):
    """Removes / from filenames and escapes them if they are '.' or '..'."""
    filename = filename.replace('/', '')
    if filename == '.':
        return '_'
    elif filename == '..':
        return '__'
    else:
        return filename

def contents(filename):
    with open(filename) as fd:
        return fd.read()

def open_mkdir(filename, mode='wb', *args, **kwargs):
    """filename -> file object.

    Returns a file object for filename, creating as many directories as may be
    necessary.  I.e., if the filename is ./foo/bar/baz, and . exists, and ./foo
    exists, but ./foo/bar does not exist, bar will be created before opening
    baz in it.
    """
    if mode not in ('w', 'wb'):
        raise ValueError('utils.file.open expects to write.')
    (dirname, basename) = os.path.split(filename)
    os.makedirs(dirname)
    return open(filename, mode, *args, **kwargs)

def copy(src, dst):
    """src, dst -> None

    Copies src to dst, using this module's 'open' function to open dst.
    """
    srcfd = open(src)
    dstfd = open_mkdir(dst, 'wb')
    shutil.copyfileobj(srcfd, dstfd)
    srcfd.close()
    dstfd.close()

def writeLine(fd, line):
    fd.write(line)
    if not line.endswith('\n'):
        fd.write('\n')

def readLines(filename):
    fd = open(filename)
    try:
        return [line.rstrip('\r\n') for line in fd.readlines()]
    finally:
        fd.close()

def touch(filename):
    fd = open(filename, 'w')
    fd.close()

def mktemp(suffix=''):
    """Gives a decent random string, suitable for a filename."""
    r = random.Random()
    m = crypt.md5(suffix.encode('utf8'))
    r.seed(time.time())
    s = str(r.getstate())
    period = random.random()
    now = start = time.time()
    while start + period < now:
        time.sleep() # Induce a context switch, if possible.
        now = time.time()
        m.update(str(random.random()))
        m.update(s)
        m.update(str(now))
        s = m.hexdigest()
    return crypt.sha((s + str(time.time())).encode('utf8')).hexdigest()+suffix

def nonCommentLines(fd):
    for line in fd:
        if not line.startswith('#'):
            yield line

def nonEmptyLines(fd):
    return filter(str.strip, fd)

def nonCommentNonEmptyLines(fd):
    return nonEmptyLines(nonCommentLines(fd))

def chunks(fd, size):
    return iter(lambda : fd.read(size), '')
##     chunk = fd.read(size)
##     while chunk:
##         yield chunk
##         chunk = fd.read(size)

class AtomicFile(object):
    """Used for files that need to be atomically written -- i.e., if there's a
    failure, the original file remains, unmodified.  mode must be 'w' or 'wb'"""
    class default(object): # Holder for values.
        # Callables?
        tmpDir = None
        backupDir = None
        makeBackupIfSmaller = True
        allowEmptyOverwrite = True
    def __init__(self, filename, mode='w', allowEmptyOverwrite=None,
                 makeBackupIfSmaller=None, tmpDir=None, backupDir=None,
                 encoding=None):
        if tmpDir is None:
            tmpDir = force(self.default.tmpDir)
        if backupDir is None:
            backupDir = force(self.default.backupDir)
        if makeBackupIfSmaller is None:
            makeBackupIfSmaller = force(self.default.makeBackupIfSmaller)
        if allowEmptyOverwrite is None:
            allowEmptyOverwrite = force(self.default.allowEmptyOverwrite)
        if encoding is None and 'b' not in mode:
            encoding = 'utf8'
        if mode not in ('w', 'wb'):
            raise ValueError(format('Invalid mode: %q', mode))
        self.rolledback = False
        self.allowEmptyOverwrite = allowEmptyOverwrite
        self.makeBackupIfSmaller = makeBackupIfSmaller
        self.filename = filename
        self.backupDir = backupDir
        if tmpDir is None:
            # If not given a tmpDir, we'll just put a random token on the end
            # of our filename and put it in the same directory.
            self.tempFilename = '%s.%s' % (self.filename, mktemp())
        else:
            # If given a tmpDir, we'll get the basename (just the filename, no
            # directory), put our random token on the end, and put it in tmpDir
            tempFilename = '%s.%s' % (os.path.basename(self.filename), mktemp())
            self.tempFilename = os.path.join(tmpDir, tempFilename)
        # This doesn't work because of the uncollectable garbage effect.
        # self.__parent = super(AtomicFile, self)
        self._fd = codecs.open(self.tempFilename, mode, encoding=encoding)

    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            self.rollback()
        else:
            self.close()


    @property
    def closed(self):
        return self._fd.closed

    def write(self, data):
        return self._fd.write(data)

    def writelines(self, lines):
        return self._fd.writelines(lines)

    def rollback(self):
        if not self.closed:
            self._fd.close()
            if os.path.exists(self.tempFilename):
                os.remove(self.tempFilename)
            self.rolledback = True

    def seek(self, offset):
        return self._fd.seek(offset)

    def tell(self):
        return self._fd.tell()

    def flush(self):
        return self._fd.flush()

    def close(self):
        if not self.rolledback:
            self._fd.close()
            # We don't mind writing an empty file if the file we're overwriting
            # doesn't exist.
            newSize = os.path.getsize(self.tempFilename)
            originalExists = os.path.exists(self.filename)
            if newSize or self.allowEmptyOverwrite or not originalExists:
                if originalExists:
                    oldSize = os.path.getsize(self.filename)
                    if self.makeBackupIfSmaller and newSize < oldSize and \
                            self.backupDir != '/dev/null':
                        now = int(time.time())
                        backupFilename = '%s.backup.%s' % (self.filename, now)
                        if self.backupDir is not None:
                            backupFilename = os.path.basename(backupFilename)
                            backupFilename = os.path.join(self.backupDir,
                                                          backupFilename)
                        shutil.copy(self.filename, backupFilename)
                # We use shutil.move here instead of os.rename because
                # the latter doesn't work on Windows when self.filename
                # (the target) already exists.  shutil.move handles those
                # intricacies for us.

                # This raises IOError if we can't write to the file.  Since
                # in *nix, it only takes write perms to the *directory* to
                # rename a file (and shutil.move will use os.rename if
                # possible), we first check if we have the write permission
                # and only then do we write.
                fd = open(self.filename, 'a')
                fd.close()
                shutil.move(self.tempFilename, self.filename)

        else:
            raise ValueError('AtomicFile.close called after rollback.')

    def __del__(self):
        # We rollback because if we're deleted without being explicitly closed,
        # that's bad.  We really should log this here, but as of yet we've got
        # no logging facility in utils.  I've got some ideas for this, though.
        self.rollback()

# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
