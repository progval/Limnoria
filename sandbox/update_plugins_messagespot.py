import os
import pbs

pbs.cd('Admin')
for plugin in os.listdir('..'):
    path = os.path.join('..', plugin)
    print(repr(path))
    assert os.path.exists(path)
    if not os.path.isdir(path):
        print 1
        continue
    print 2
    pbs.cd(path)
    pbs.pygettext('-D', 'config.py', 'plugin.py')
