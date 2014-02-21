# Common

First things first: Supybot *requires* at least Python 2.6.  There
isn't any way to get around it.  You can get it from [Python homepage].

[Python homepage]:http://python.org/

# Recommended Software

[PySQLite] -- Version 3.x (most Python distributions include it by default)

[Twisted] -- Version 1.2.0 or greater (unless you actually want to use Twisted,
you don't actually need it)

[PySQLite]:https://code.google.com/p/pysqlite/
[Twisted]:http://twistedmatrix.com/trac/

For more information and help on how to use Supybot, checkout
the documents under [docs/], especially [GETTING_STARTED] and
[CONFIGURATION] .

[docs/]:docs/index.rst
[GETTING_STARTED]:docs/GETTING_STARTED
[CONFIGURATION]:docs/CONFIGURATION

So what do you do?  That depends on which operating system you're
running.  We've split this document up to address the different
methods, so find the section for your operating system and continue
from there.

# UNIX/Linux/BSD

If you're installing Python using your distributor's packages, you may
need a python-dev or python3-dev package installed, too.  If you don't have
a '/usr/lib/python2.x/distutils' directory or 
'/usr/lib/python2.x/config/Makefile' or with Python 3 
'/usr/lib/python3.x/distutils' or '/usr/lib/python3.x/config/Makefile' (assuming '/usr/lib/python2.x' or '/usr/lib/python3.x' is where your Python 
libs are installed), then you will need a python-dev or python3-dev package.

First start by git cloning Limnoria and moving to the cloned repository.

```
git clone git://github.com/ProgVal/Limnoria.git
cd Limnoria
```

The rest depends on do you have root access and do you want to perform global or local install.

## Global install

Run

```
python setup.py install
```

```python``` can be replaced with ```python2``` (if your distribution 
uses Python 3 by default) or ```python3``` if you want to use Python 3 
version.

Now you have several new programs installed where Python scripts are normally
installed on your system ('/usr/bin' or '/usr/local/bin' are common on
UNIX systems).  The two that might be of particular interest to you, the
new user, are 'supybot' and 'supybot-wizard'.  The former, 'supybot', is
the script to run an actual bot; the latter, 'supybot-wizard', is an
in-depth wizard that provides a nice user interface for creating a
registry file for your bot.

## Local install

Run

```
python setup.py install --user
```

```python``` can be replaced with ```python2``` (if your distribution 
uses Python 3 by default) or ```python3``` if you want to use 
Python 3 version.

and you will have new programs installed in ~/.local/bin. The two that might be of particular interest to you, the
new user, are 'supybot' and 'supybot-wizard'.  The former, 'supybot', is
the script to run an actual bot; the latter, 'supybot-wizard', is an
in-depth wizard that provides a nice user interface for creating a
registry file for your bot.

By default you must run the bot with full path to the binary unless you specify $PATH.

Run and add the following command to your shellrc, which is usually ~/.bashrc or ~/.zshrc , so you can run the programs without needing to write full paths to the binaries.

```
PATH=$HOME/.local/bin:$PATH
```

# Upgrading

To upgrade, return to the cloned Limnoria repository and run:

```
git pull
```

and then install Limnoria normally. "python setup.py install" doesn't affect config files of the bot any way.

If you don't have the cloned Limnoria repository, clone it again using the installation instructions.

## Upgrading to Python 3

Upgrading Python3 happens the same way, but if you want to move from 2 to 3 
or 3 to 2, you must remove the build/ directory and the executable 
supybot* files first. The build/ directory is on same directory as this 
file and supybot* are usually in /usr/local/bin or ~/.local/bin

```
rm -rf build/
rm /usr/local/bin/supybot*
rm ~/.local/bin/supybot*
```

# Windows

**Note**: If you are using an IPV6 connection, you will not be able
to run Supybot under Windows (unless Python has fixed things).  Current
versions of Python for Windows are *not* built with IPV6 support. This
isn't expected to be fixed until Python 2.4, at the earliest.

Now that you have Python installed, open up a command prompt.  The
easiest way to do this is to open the run dialog (Programs -> run) and
type "cmd" (for Windows 2000/XP/2003) or "command" (for Windows 9x).  In
order to reduce the amount of typing you need to do, I suggest adding
Python's directory to your path.  If you installed Python using the
default settings, you would then do the following in the command prompt
(otherwise change the path to match your settings)::

```
set PATH=C:\Python2x\;%PATH%
```

You should now be able to type 'python' to start the Python
interpreter.  Exit by pressing CTRL-Z and then Return.  Now that that's
setup, you'll want to cd into the directory that was created when you
unzipped Supybot; I'll assume you unzipped it to 'C:\Supybot' for these
instructions.  From 'C:\Supybot', run 

```
python setup.py install
```

This will install Supybot under 'C:\Python2x\'.  You will now have several new
programs installed in 'C:\Python2x\Scripts\'.  The two that might be of
particular interest to you, the new user, are 'supybot' and 'supybot-wizard'.
The former, 'supybot', is the script to run an actual bot; the latter,
'supybot-wizard', is an in-depth wizard that provides a nice user interface for
creating a registry file for your bot.
