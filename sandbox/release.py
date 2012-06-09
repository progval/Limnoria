#!/usr/bin/env python

import os
import re
import sys
import shutil

from optparse import OptionParser

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

def checkGitRepo():
    system('test "$(git rev-parse --is-inside-work-tree)" = "true"',
           'Must be run from a git checkout.')
    system('test "$(git rev-parse --show-cdup >/dev/null)" = ""',
           'Must be run from the top-level directory of the git checkout.')
    system('git rev-parse --verify HEAD >/dev/null '
           '&& git update-index --refresh'
           '&& git diff-files --quiet'
           '&& git diff-index --cached --quiet HEAD --',
           'Your tree is unclean. Can\'t run from here.')

if __name__ == '__main__':
    usage = 'usage: %prog [options] <username> <version>'
    parser = OptionParser(usage=usage)
    parser.set_defaults(sign=False, verbose=False)
    parser.add_option('-s', '--sign', action='store_true', dest='sign',
                      help='Pass on -s to relevant git commands')
    parser.add_option('-n', '--dry-run', action='store_true', dest='dry_run',
                      help='Build the release, but do not push to the git '
                           'remote or upload the release archives.')
    (options, args) = parser.parse_args()

    if len(args) != 2:
        parser.error('Both username and version must be specified')

    (u, v) = args
    if not re.match(r'^\d+\.\d+\.\d+(\.\d+)?\w*$', v):
        parser.error('Invalid version string: '
                     'must be of the form MAJOR.MINOR.PATCHLEVEL')

    checkGitRepo()

    sign = options.sign
    dryrun = options.dry_run

    if os.path.exists('supybot'):
        error('I need to make the directory "supybot" but it already exists.'
              '  Change to an appropriate directory or remove the supybot '
              'directory to continue.')
    print 'Checking out fresh tree from git.'
    system('git clone git+ssh://%s@supybot.git.sourceforge.net/gitroot/supybot'
           % u)
    os.chdir('supybot')

    print 'Checking RELNOTES version line.'
    if firstLine('RELNOTES') != 'Version %s' % v:
        error('Invalid first line in RELNOTES.')

    print 'Checking ChangeLog version line.'
    (first, _, third) = firstLines('ChangeLog', 3)
    if not re.match(r'^20\d\d-\d{2}-\d{2}\s+\w+.*<\S+@\S+>$', first):
        error('Invalid first line in ChangeLog.')
    if not re.match(r'^\t\* Version %s!$' % v, third):
        error('Invalid third line in ChangeLog.')

    print 'Updating version in version files.'
    versionFiles = ['src/version.py']
    for fn in versionFiles:
        sh = 'perl -pi -e "s/^version\s*=.*/version = \'%s\'/" %s' % (v, fn)
        system(sh, 'Error changing version in %s' % fn)
    system('git commit %s -m \'Updated to %s.\' %s'
           % (sign, v, ' '.join(versionFiles)))

    print 'Tagging release.'
    system('git tag %s -m "Release %s" %s' % (sign or '-a', v, v))

    print 'Committing %s+git to version files.' % v
    for fn in versionFiles:
        sh = 'perl -pi -e "s/^version\s*=.*/version = \'%s\'/" %s' % \
             (v + '+git', fn)
        system(sh, 'Error changing version in %s' % fn)
    system('git commit %s -m \'Updated to %s+git.\' %s'
           % (sign, v, ' '.join(versionFiles)))

    if not dryrun:
        print 'Pushing commits and tag.'
        system('git push origin master')
        system('git push --tags')

    print 'Creating tarball (gzip).'
    system('git archive --prefix=Supybot-%s/ --format=tar %s '
           '| gzip -c >../Supybot-%s.tar.gz' % (v, v, v))
    print 'Creating tarball (bzip2).'
    system('git archive --prefix=Supybot-%s/ --format=tar %s '
           '| bzip2 -c >../Supybot-%s.tar.bz2' % (v, v, v))
    print 'Creating zip.'
    system('git archive --prefix=Supybot-%s/ --format=zip %s '
           '>../Supybot-%s.zip' % (v, v, v))

    os.chdir('..')
    shutil.rmtree('supybot')

    if not dryrun:
        print 'Uploading package files to upload.sf.net.'
        system('scp Supybot-%s.tar.gz Supybot-%s.tar.bz2 Supybot-%s.zip '
               '%s@frs.sourceforge.net:uploads' % (v, v, v, u))
        os.unlink('Supybot-%s.tar.gz' % v)
        os.unlink('Supybot-%s.tar.bz2' % v)
        os.unlink('Supybot-%s.zip' % v)

        print 'Copying new version.txt over to project webserver.'
        system('echo %s > version.txt' % v)
        system('scp version.txt %s@web.sf.net:/home/groups/s/su/supybot/htdocs'
               %u)
        os.unlink('version.txt')

#    print 'Generating documentation.'
#    # docFiles is in the format {directory: files}
#    docFiles = {'.': ('README', 'INSTALL', 'ChangeLog'),
#                'docs': ('config.html', 'CAPABILITIES', 'commands.html',
#                         'CONFIGURATION', 'FAQ', 'GETTING_STARTED',
#                         'INTERFACES', 'OVERVIEW', 'PLUGIN-EXAMPLE',
#                         'plugins', 'plugins.html', 'STYLE'),
#               }
#    system('python scripts/supybot-plugin-doc')
#    pwd = os.getcwd()
#    os.chmod('docs/plugins', 0775)
#    sh = 'tar rf %s/docs.tar %%s' % pwd
#    for (dir, L) in docFiles.iteritems():
#        os.chdir(os.path.join(pwd, dir))
#        system(sh % ' '.join(L))
#    os.chdir(pwd)
#    system('bzip2 docs.tar')
#
#    print 'Uploading documentation to webspace.'
#    system('scp docs.tar.bz2 %s@supybot.sf.net:/home/groups/s/su/supybot'
#           '/htdocs/docs/.' % u)
#    system('ssh %s@supybot.sf.net "cd /home/groups/s/su/supybot/htdocs/docs; '
#           'tar jxf docs.tar.bz2"' % u)
#
#    print 'Cleaning up generated documentation.'
#    shutil.rmtree('docs/plugins')
#    configFiles = ('docs/config.html', 'docs/plugins.html',
#                   'docs/commands.html', 'docs.tar.bz2', 'test-conf',
#                   'test-data', 'test-logs', 'tmp')
#    for fn in configFiles:
#        os.remove(fn)

# This is the part where we do our release on Freshmeat using XMLRPC and
# <gasp> ESR's software to do it: http://freshmeat.net/p/freshmeat-submit/
