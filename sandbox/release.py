#!/usr/bin/env python

import os
import re
import sys
import ftplib
import shutil

def firstLines(filename, n):
    fd = file(filename)
    lines = []
    while n:
        n -= 1
        lines.append(fd.readline().rstrip('\r\n'))
    return lines

def firstLine(filename):
    return firstLines(filename, 1)[0]

def error(s):
    sys.stderr.write(s+'\n')
    sys.exit(-1)

def system(sh, errmsg=None):
    if errmsg is None:
        errmsg = sh
    ret = os.system(sh)
    if not ret:
        error(errmsg + '  (error code: %s)')
    
if __name__ == '__main__':
    if len(sys.argv) < 2:
        error('Usage: %s <version>\n' % sys.argv[0])

    v = sys.argv[1]
    if not re.match(r'^\d+\.\d+\.\d+\w*$', v):
        error('Invalid version string: '
              'must be of the form MAJOR.MINOR.PATCHLEVEL.')
        
    if firstLine('RELNOTES') != 'Version %s':
        error('Invalid first line in RELNOTES.')

    (first, _, third) = firstLines('ChangeLog', 3)
    if not re.match(r'^200\d-\d{2}-\d{2}\s+\w+.*<\S+@\S+>$', first):
        error('Invalid first line in ChangeLog.')
    if not re.match(r'^\t\* Version %s!$' % v, third):
        error('Invalid third line in ChangeLog.')
    
    versionFiles = ('src/conf.py', 'scripts/supybot', 'setup.py')
    for fn in versionFiles:
        sh = 'perl -pi -e "s/^version\s*=.*/version = \'%s\'" %s' % (v, fn)
        system(sh, 'Error changing version in %s' % fn)
    system('cvs commit -m "Updated to %s." %s' % (v, ' '.join(versionFiles)))

    system('cvs tag -F release-%s' % v.replace('.', '_'))

    shutil.rmtree('test')
    shutil.rmtree('sandbox')
    system('find . -name CVS | xargs rm -rf')
    shutil.remove('.cvsignore')

    os.chdir('..')
    shutil.move('supybot', 'Supybot-%s' % v)

    system('tar czvf Supybot-%s.tar.gz Supybot-%s' % (v, v))
    system('tar cjvf Supybot-%s.tar.bz2 Supybot-%s' % (v, v))
    system('zip -r Supybot-%s.zip Supybot-%s' % (v, v))

##     ftp = ftplib.FTP('upload.sf.net')
##     ftp.login()
##     ftp.cwd('incoming')
##     ftp.storbinary('STOR Supybot-%s.tar.gz' % v)
##     ftp.storbinary('STOR Supybot-%s.tar.bz2' % v)
##     ftp.storbinary('STOR Supybot-%s.zip' % v)
##     ftp.close()

##     fd = file('version.txt', 'w')
##     fd.write(v+'\n')
##     fd.close()
