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
        errmsg = repr(sh)
    ret = os.system(sh)
    if ret:
        error(errmsg + '  (error code: %s)' % ret)
    
if __name__ == '__main__':
    if len(sys.argv) < 3:
        error('Usage: %s <sf username> <version>\n' % sys.argv[0])

    print 'Check version string for validity.' 
    (u, v) = sys.argv[1:]
    if not re.match(r'^\d+\.\d+\.\d+\w*$', v):
        error('Invalid version string: '
              'must be of the form MAJOR.MINOR.PATCHLEVEL.')

    if os.path.exists('supybot'):
        error('I need to make the directory "supybot" but it already exists.'
              '  Change to an appropriate directory or rmeove the supybot '
              'directory to continue.')
    print 'Checking out fresh tree from CVS.'
    system('cvs -d:ext:%s@cvs.sf.net:/cvsroot/supybot co supybot' % u)
    os.chdir('supybot')
        
    print 'Checking RELNOTES version line.'
    if firstLine('RELNOTES') != 'Version %s' % v:
        error('Invalid first line in RELNOTES.')

    print 'Checking ChangeLog version line.'
    (first, _, third) = firstLines('ChangeLog', 3)
    if not re.match(r'^200\d-\d{2}-\d{2}\s+\w+.*<\S+@\S+>$', first):
        error('Invalid first line in ChangeLog.')
    if not re.match(r'^\t\* Version %s!$' % v, third):
        error('Invalid third line in ChangeLog.')
    
    print 'Updating version in version files.'
    versionFiles = ('src/conf.py', 'scripts/supybot', 'setup.py')
    for fn in versionFiles:
        sh = 'perl -pi -e "s/^version\s*=.*/version = \'%s\'/" %s' % (v, fn)
        system(sh, 'Error changing version in %s' % fn)
    system('cvs commit -m "Updated to %s." %s' % (v, ' '.join(versionFiles)))

    print 'Tagging release.'
    system('cvs tag -F release-%s' % v.replace('.', '_'))

    print 'Removing test, sandbox, CVS, and .cvsignore.'
    shutil.rmtree('test')
    shutil.rmtree('sandbox')
    system('find . -name CVS | xargs rm -rf')
    os.remove('.cvsignore')

    os.chdir('..')
    dirname = 'Supybot-%s' % v
    print 'Renaming directory to %s.' % dirname
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    shutil.move('supybot', dirname)

    print 'Creating tarball (gzip).'
    system('tar czvf Supybot-%s.tar.gz %s' % (v, dirname))
    print 'Creating tarball (bzip2).'
    system('tar cjvf Supybot-%s.tar.bz2 %s' % (v, dirname))
    print 'Creating zip.'
    system('zip -r Supybot-%s.zip %s' % (v, dirname))

    print 'Uploading package files to upload.sf.net.'
    ftp = ftplib.FTP('upload.sf.net')
    ftp.login()
    ftp.cwd('incoming')
    for filename in ['Supybot-%s.tar.gz',
                     'Supybot-%s.tar.bz2',
                     'Supybot-%s.zip']:
        filename = filename % v
        print 'Uploading %s to SF.net.' % filename
        ftp.storbinary('STOR %s' % filename, file(filename))
    ftp.close()

    print 'Copying new version.txt over to project webserver.'
    system('echo %s > version.txt' % v)
    system('scp version.txt %s@shell.sf.net:/home/groups/s/su/supybot/htdocs'%u)

    print 'Committing %s+cvs to version files.' % v
    for fn in versionFiles:
        sh = 'perl -pi -e "s/^version\s*=.*/version = \'%s\'/" %s' % \
             (v + '+cvs', fn)
        system(sh, 'Error changing version in %s' % fn)
    system('cvs commit -m "Updated to %s." %s' % (v, ' '.join(versionFiles)))

# This is the part where we do our release on Freshmeat using XMLRPC and
# <gasp> ESR's software to do it: http://freshmeat.net/p/freshmeat-submit/
