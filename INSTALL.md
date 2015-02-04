# Common

**Note: there is an even easier [installation guide in the documentation!](http://doc.supybot.aperio.fr/en/latest/use/install.html)**

First things first: Supybot *requires* at least Python 2.6.  There
isn't any way to get around it.  You can get it from the [Python homepage].

[Python homepage]:http://python.org/

# Recommended Software

The following libraries are not needed for running Limnoria, but enable
extra features you may want (ordered by decreasing estimated usefulness):

[charade] -- enables better encoding handling

[pytz] and [python-dateutil] -- enable additional features of the `Time` plugin

[python-gnupg] -- enables user authentication with GPG

[charade]:https://pypi.python.org/pypi/charade
[pytz]:https://pypi.python.org/pypi/pytz
[python-dateutil]:https://pypi.python.org/pypi/python-dateutil
[python-gnupg]:https://pypi.python.org/pypi/python-gnupg

To install them, run 

`pip install -r requirements.txt`

or for a local install (if you don't have or don't want to use root), 

`pip install -r requirements.txt --user`

For more information and help on how to use Supybot, check out
the [documentation], especially [GETTING_STARTED] and
[CONFIGURATION].

[documentation]:http://doc.supybot.aperio.fr/en/latest/use/index.html
[GETTING_STARTED]:http://doc.supybot.aperio.fr/en/latest/use/getting_started.html
[CONFIGURATION]:http://doc.supybot.aperio.fr/en/latest/use/configuration.html

So what do you do?  That depends on which operating system you're
running.  We've split this document up to address the different installation
methods, so find the section for your operating system and continue
from there.

# UNIX/Linux/BSD

If you're installing Python using your distributor's packages, you may
need a python-dev or python3-dev package installed, too.  If you don't have
a `/usr/lib/python2.x/distutils` directory or 
`/usr/lib/python2.x/config/Makefile`; or with Python 3 
`/usr/lib/python3.x/distutils` or `/usr/lib/python3.x/config/Makefile` (assuming `/usr/lib/python2.x` or `/usr/lib/python3.x` is where your Python 
libs are installed), then you will need a python-dev or python3-dev package.

## git

First start by git cloning Limnoria and moving to the cloned repository.

```
git clone https://github.com/ProgVal/Limnoria.git
cd Limnoria
```

The rest depends on whether you have root access and want a global or local install.

### Global install

Run

```
python setup.py install
```

`python` can be replaced with `python2` (if your distribution 
uses Python 3 by default) or `python3` if you want to use the Python 3 
version of the bot.

Now you have several new programs installed where Python scripts are normally
installed on your system (`/usr/bin` or `/usr/local/bin` are common on
UNIX systems).  The two that might be of particular interest to you as a
new user are 'supybot' and 'supybot-wizard'.  The former, 'supybot', is
the script to run an actual bot; the latter, 'supybot-wizard', is an
in-depth wizard that provides a nice user interface for creating a
registry file for your bot.

### Local install

Run

```
python setup.py install --user
```

`python` can be replaced with `python2` (if your distribution 
uses Python 3 by default) or `python3` if you want to use the Python 3 
version.

and you will have new programs installed in `~/.local/bin`. The two that might be of particular interest to you as a
new user are 'supybot' and 'supybot-wizard'.  The former, 'supybot', is
the script to run an actual bot; the latter, 'supybot-wizard', is an
in-depth wizard that provides a nice user interface for creating a
registry file for your bot.

By default you must run the bot with full path to the binary unless you specify a $PATH.

Run the following command to fix your PATH. We assume that you use bash 
(and if you don't, you probably already know how to do this with the shell you are using).

```
echo 'PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Pip

To install with pip, run:

```
sudo pip install -r https://raw.githubusercontent.com/ProgVal/Limnoria/master/requirements.txt
sudo pip install git+https://github.com/ProgVal/Limnoria.git@master
```

or for a local install:

```
pip install -r https://raw.githubusercontent.com/ProgVal/Limnoria/master/requirements.txt --user
pip install git+https://github.com/ProgVal/Limnoria.git@master --user
```

If you wish to use Python 3 or 2 instead of default of your distribution 
run `pipX` where X is either 2 or 3 (`pip2` or `pip3`) instead of `pip`.

If pip gives an error immediately instead of doing anything and you have git installed, try upgrading pip with `sudo pip install pip --upgrade` (or locally, `pip install pip --upgrade --user`).

### Upgrading

#### git

To upgrade, return to the cloned Limnoria repository and run:

```
git pull
```

and then install Limnoria normally. "python setup.py install" doesn't affect config files of the bot in any way.

If you don't have the cloned Limnoria repository, clone it again using the installation instructions.

### Pip

Run the first install command again, but add `--upgrade` to the 
end. Then run the second install command.

## Upgrading to Python 3

Upgrading to Python 3 happens the same way, but if you want to move from 2
to 3 or 3 to 2, you must remove the `build/` directory and the executable
`supybot*` files first. `The build/` directory is in same directory as
this file and the `supybot*` executables are usually in `/usr/local/bin`
or `~/.local/bin`.

```
rm -rf build/
rm /usr/local/bin/supybot*
rm ~/.local/bin/supybot*
```
