Supybot is a robust (it doesn't crash), user friendly (it's easy to
configure) and programmer friendly (plugins are *extremely* easy to
write) Python IRC bot.  It aims to be an adequate replacement for most
existing IRC bots.  It includes a very flexible and powerful ACL system
for controlling access to commands, as well as more than 50 builtin plugins
providing around 400 actual commands.

Limnoria is a project which continues development of Supybot (you can
call it a fork) by fixing bugs and adding features (see the
[list of added features](https://github.com/ProgVal/Limnoria/wiki/LGC) for
more details).

# Build status

Master branch: [![Build Status (master branch)](https://travis-ci.org/ProgVal/Limnoria.png?branch=master)](https://travis-ci.org/ProgVal/Limnoria)

Testing branch: [![Build Status (testing branch)](https://travis-ci.org/ProgVal/Limnoria.png?branch=testing)](https://travis-ci.org/ProgVal/Limnoria)

Limnoria supports CPython 2.6, 2.7, 3.2, 3.3, 3.4, 3.5, nightly;
and Pypy 2 and 3. It works best with CPython 3.3 and higher.
Python 2.5 and older versions are not supported.

# Support

## Documentation

If this is your first install, there is an [install guide](http://doc.supybot.aperio.fr/en/latest/use/install.html).
You will probably be pointed to it if you ask on IRC how to install
Limnoria.

There is extensive documentation at [supybot.aperio.fr] and at
[Gribble wiki]. We took the time to write it; you should take the time to
read it.

## Installing from cloned repo

*If you haven't cloned this repository, please see the previous two
paragraphs for easier installation methods.*

```
sudo pip install -r requirements.txt
sudo python setup.py install --user
```

alternatively without root

```
pip install -r requirements.txt --user
python setup.py install --user
```

[supybot.aperio.fr]:http://doc.supybot.aperio.fr/
[Gribble wiki]:https://sourceforge.net/apps/mediawiki/gribble/index.php?title=Main_Page

## IRC channels

### In English

If you have any trouble, feel free to swing by [#supybot and #limnoria](ircs://chat.freenode.net:6697/#supybot,#limnoria) on
[freenode](https://freenode.net/) or [#supybot](ircs://irc.oftc.net:6697/#supybot) at [OFTC](http://oftc.net/) (we have a Limnoria there relaying,
so either network works) and ask questions.  We'll be happy to help
wherever we can.  And by all means, if you find anything hard to
understand or think you know of a better way to do something,
*please* post it on the [issue tracker] so we can improve the bot!

[issue tracker]:https://github.com/ProgVal/Limnoria/issues

### In Other languages

Only in French at the moment, located at [#supybot-fr on freenode](ircs://chat.freenode.net:6697/#supybot-fr).

