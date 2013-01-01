=================================
Writing Your First Supybot Plugin
=================================

Introduction
============
Ok, so you want to write a plugin for Supybot. Good, then this is the place to
be. We're going to start from the top (the highest level, where Supybot code
does the most work for you) and move lower after that.

So have you used Supybot? If not, you need to go use it. This will help you
understand crucial things like the way the various commands work and it is
essential prior to embarking upon the plugin-development excursion detailed in
the following pages. If you haven't used Supybot, come back to this document
after you've used it for a while and gotten a feel for it.

So, now that we know you've used Supybot, we'll start getting into details.
We'll go through this tutorial by actually writing a new plugin, named Random
with just a few simple commands.

    Caveat: you'll need to have Supybot installed on the machine you
    intend to develop plugins on. This will not only allow you to test
    the plugins with a live bot, but it will also provide you with
    several nice scripts which aid the development of plugins. Most
    notably, it provides you with the supybot-plugin-create script which
    we will use in the next section...  Creating a minimal plugin This
    section describes using the 'supybot-plugin-create' script to create
    a minimal plugin which we will enhance in later sections.

The recommended way to start writing a plugin is to use the wizard provided,
:command:`supybot-plugin-create`. Run this from within your local plugins
directory, so we will be able to load the plugin and test it out.

It's very easy to follow, because basically all you have to do is answer three
questions. Here's an example session::

    [ddipaolo@quinn ../python/supybot]% supybot-plugin-create
    What should the name of the plugin be? Random

    Sometimes you'll want a callback to be threaded.  If its methods
    (command or regexp-based, either one) will take a significant amount
    of time to run, you'll want to thread them so they don't block the
    entire bot.

    Does your plugin need to be threaded? [y/n] n

    What is your real name, so I can fill in the copyright and license
    appropriately? Daniel DiPaolo

    Your new plugin template is in the Random directory.

It's that simple! Well, that part of making the minimal plugin is that simple.
You should now have a directory with a few files in it, so let's take a look at
each of those files and see what they're used for.

README.txt
==========
In :file:`README.txt` you put exactly what the boilerplate text says to put in
there:

    Insert a description of your plugin here, with any notes, etc. about
    using it.

A brief overview of exactly what the purpose of the plugin is supposed to do is
really all that is needed here. Also, if this plugin requires any third-party
Python modules, you should definitely mention those here. You don't have to
describe individual commands or anything like that, as those are defined within
the plugin code itself as you'll see later. You also don't need to acknowledge
any of the developers of the plugin as those too are handled elsewhere.

For our Random plugin, let's make :file:`README.txt` say this:

    This plugin contains commands relating to random numbers, and
    includes: a simple random number generator, the ability to pick a
    random number from within a range, a command for returning a random
    sampling from a list of items, and a simple dice roller.

And now you know what's in store for the rest of this tutorial, we'll be
writing all of that in one Supybot plugin, and you'll be surprised at just how
simple it is!

__init__.py
===========
The next file we'll look at is :file:`__init__.py`. If you're familiar with
the Python import mechanism, you'll know what this file is for. If you're not,
think of it as sort of the "glue" file that pulls all the files in this
directory together when you load the plugin. It's also where there are a few
administrative items live that you really need to maintain.

Let's go through the file. For the first 30 lines or so, you'll see the
copyright notice that we use for our plugins, only with your name in place (as
prompted in :command:`supybot-plugin-create`). Feel free to use whatever
license you choose, we don't feel particularly attached to the boilerplate
code so it's yours to license as you see fit even if you don't modify it. For
our example, we'll leave it as is.

The plugin docstring immediately follows the copyright notice and it (like
:file:`README.txt`) tells you precisely what it should contain:

    Add a description of the plugin (to be presented to the user inside
    the wizard) here.  This should describe *what* the plugin does.

The "wizard" that it speaks of is the :command:`supybot-wizard` script that is
used to create working Supybot config file. I imagine that in meeting the
prerequisite of "using a Supybot" first, most readers will have already
encountered this script. Basically, if the user selects to look at this plugin
from the list of plugins to load, it prints out that description to let the
user know what it does, so make sure to be clear on what the purpose of the
plugin is. This should be an abbreviated version of what we put in our
:file:`README.txt`, so let's put this::

    Provides a number of commands for selecting random things.

Next in :file:`__init__.py` you see a few imports which are necessary, and
then four attributes that you need to modify for your bot and preferably keep
up with as you develop it: ``__version__``, ``__author__``,
``__contributors__``, ``__url__``.

``__version__`` is just a version string representing the current working
version of the plugin, and can be anything you want. If you use some sort of
RCS, this would be a good place to have it automatically increment the version
string for any time you edit any of the files in this directory. We'll just
make ours "0.1".

``__author__`` should be an instance of the :class:`supybot.Author` class. A
:class:`supybot.Author` is simply created by giving it a full name, a short
name (preferably IRC nick), and an e-mail address (all of these are optional,
though at least the second one is expected). So, for example, to create my
Author user (though I get to cheat and use supybot.authors.strike since I'm a
main dev, muahaha), I would do::

    __author__ = supybot.Author('Daniel DiPaolo', 'Strike',
                                'somewhere@someplace.xxx')

Keep this in mind as we get to the next item...

``__contributors__`` is a dictionary mapping supybot.Author instances to lists
of things they contributed. If someone adds a command named foo to your
plugin, the list for that author should be ``["foo"]``, or perhaps even
``["added foo command"]``. The main author shouldn't be referenced here, as it
is assumed that everything that wasn't contributed by someone else was done by
the main author.  For now we have no contributors, so we'll leave it blank.

Lastly, the ``__url__`` attribute should just reference the download URL for
the plugin. Since this is just an example, we'll leave this blank.

The rest of :file:`__init__.py` really shouldn't be touched unless you are
using third-party modules in your plugin. If you are, then you need to take
special note of the section that looks like this::

    import config
    import plugin
    reload(plugin) # In case we're being reloaded.
    # Add more reloads here if you add third-party modules and want them
    # to be reloaded when this plugin is reloaded.  Don't forget to
    # import them as well!

As the comment says, this is one place where you need to make sure you import
the third-party modules, and that you call :func:`reload` on them as well.
That way, if we are reloading a plugin on a running bot it will actually
reload the latest code. We aren't using any third-party modules, so we can
just leave this bit alone.

We're almost through the "boring" part and into the guts of writing Supybot
plugins, let's take a look at the next file.

config.py
=========
:file:`config.py` is, unsurprisingly, where all the configuration stuff
related to your plugin goes. If you're not familiar with Supybot's
configuration system, I recommend reading the config tutorial before going any
further with this section.

So, let's plow through config.py line-by-line like we did the other files.

Once again, at the top is the standard copyright notice. Again, change it to
how you see fit.

Then, some standard imports which are necessary.

Now, the first peculiar thing we get to is the configure function. This
function is what is called by the supybot-wizard whenever a plugin is selected
to be loaded. Since you've used the bot by now (as stated on the first page of
this tutorial as a prerequisite), you've seen what this script does to
configure plugins. The wizard allows the bot owner to choose something
different from the default plugin config values without having to do it through
the bot (which is still not difficult, but not as easy as this). Also, note
that the advanced argument allows you to differentiate whether or not the
person configuring this plugin considers himself an advanced Supybot user. Our
plugin has no advanced features, so we won't be using it.

So, what exactly do we do in this configure function for our plugin? Well, for
the most part we ask questions and we set configuration values. You'll notice
the import line with supybot.questions in it. That provides some nice
convenience functions which are used to (you guessed it) ask questions. The
other line in there is the conf.registerPlugin line which registers our plugin
with the config and allows us to create configuration values for the plugin.
You should leave these two lines in even if you don't have anything else to put
in here. For the vast majority of plugins, you can leave this part as is, so we
won't go over how to write plugin configuration functions here (that will be
handled in a separate article). Our plugin won't be using much configuration,
so we'll leave this as is.

Next, you'll see a line that looks very similar to the one in the configure
function. This line is used not only to register the plugin prior to being
called in configure, but also to store a bit of an alias to the plugin's config
group to make things shorter later on. So, this line should read::

    Random = conf.registerPlugin('Random')

Now we get to the part where we define all the configuration groups and
variables that our plugin is to have. Again, many plugins won't require any
configuration so we won't go over it here, but in a separate article dedicated
to sprucing up your config.py for more advanced plugins. Our plugin doesn't
require any config variables, so we actually don't need to make any changes to
this file at all.

Configuration of plugins is handled in depth at the Advanced Plugin Config
Tutorial

plugin.py
=========
Here's the moment you've been waiting for, the overview of plugin.py and how to
make our plugin actually do stuff.

At the top, same as always, is the standard copyright block to be used and
abused at your leisure.

Next, some standard imports. Not all of them are used at the moment, but you
probably will use many (if not most) of them, so just let them be.  Since
we'll be making use of Python's standard 'random' module, you'll need to add
the following line to the list of imports::

  import random

Now, the plugin class itself. What you're given is a skeleton: a simple
subclass of callbacks.Plugin for you to start with. The only real content it
has is the boilerplate docstring, which you should modify to reflect what the
boilerplate text says - it should be useful so that when someone uses the
plugin help command to determine how to use this plugin, they'll know what they
need to do. Ours will read something like::

    """This plugin provides a few random number commands and some
    commands for getting random samples.  Use the "seed" command to seed
    the plugin's random number generator if you like, though it is
    unnecessary as it gets seeded upon loading of the plugin.  The
    "random" command is most likely what you're looking for, though
    there are a number of other useful commands in this plugin.  Use
    'list random' to check them out.  """

It's basically a "guide to getting started" for the plugin. Now, to make the
plugin do something. First of all, to get any random numbers we're going to
need a random number generator (RNG). Pretty much everything in our plugin is
going to use it, so we'll define it in the constructor of our plugin, __init__.
Here we'll also seed it with the current time (standard practice for RNGs).
Here's what our __init__ looks like::

    def __init__(self, irc):
        self.__parent = super(Random, self)
        self.__parent.__init__(irc)
        self.rng = random.Random()   # create our rng
        self.rng.seed()   # automatically seeds with current time

Now, the first two lines may look a little daunting, but it's just
administrative stuff required if you want to use a custom __init__. If we
didn't want to do so, we wouldn't have to, but it's not uncommon so I decided
to use an example plugin that did. For the most part you can just copy/paste
those lines into any plugin you override the __init__ for and just change them
to use the plugin name that you are working on instead.

So, now we have a RNG in our plugin, let's write a command to get a random
number. We'll start with a simple command named random that just returns a
random number from our RNG and takes no arguments. Here's what that looks
like::

    def random(self, irc, msg, args):
        """takes no arguments

        Returns the next random number from the random number generator.
        """
        irc.reply(str(self.rng.random()))
    random = wrap(random)

And that's it. Now here are the important points.

First and foremost, all plugin commands must have all-lowercase function
names. If they aren't all lowercase they won't show up in a plugin's list of
commands (nor will they be useable in general). If you look through a plugin
and see a function that's not in all lowercase, it is not a plugin command.
Chances are it is a helper function of some sort, and in fact using capital
letters is a good way of assuring that you don't accidentally expose helper
functions to users as commands.

You'll note the arguments to this class method are (self, irc, msg, args). This
is what the argument list for all methods that are to be used as commands must
start with. If you wanted additional arguments, you'd append them onto the end,
but since we take no arguments we just stop there. I'll explain this in more
detail with our next command, but it is very important that all plugin commands
are class methods that start with those four arguments exactly as named.

Next, in the docstring there are two major components. First, the very first
line dictates the argument list to be displayed when someone calls the help
command for this command (i.e., help random). Then you leave a blank line and
start the actual help string for the function. Don't worry about the fact that
it's tabbed in or anything like that, as the help command normalizes it to
make it look nice. This part should be fairly brief but sufficient to explain
the function and what (if any) arguments it requires. Remember that this should
fit in one IRC message which is typically around a 450 character limit.

Then we have the actual code body of the plugin, which consists of a single
line: irc.reply(str(self.rng.random())). The irc.reply function issues a reply
to wherever the PRIVMSG it received the command from with whatever text is
provided. If you're not sure what I mean when I say "wherever the PRIVMSG it
received the command from", basically it means: if the command is issued in a
channel the response is sent in the channel, and if the command is issued in a
private dialog the response is sent in a private dialog. The text we want to
display is simply the next number from our RNG (self.rng). We get that number
by calling the random function, and then we str it just to make sure it is a
nice printable string.

Lastly, all plugin commands must be 'wrap'ed. What the wrap function does is
handle argument parsing for plugin commands in a very nice and very powerful
way. With no arguments, we simply need to just wrap it. For more in-depth
information on using wrap check out the wrap tutorial (The astute Python
programmer may note that this is very much like a decorator, and that's
precisely what it is. However, we developed this before decorators existed and
haven't changed the syntax due to our earlier requirement to stay compatible
with Python 2.3.  As we now require Python 2.6 or greater, this may eventually
change to support work via decorators.)

Now let's create a command with some arguments and see how we use those in our
plugin commands. Let's allow the user to seed our RNG with their own seed
value. We'll call the command seed and take just the seed value as the argument
(which we'll require be a floating point value of some sort, though technically
it can be any hashable object). Here's what this command looks like::

    def seed(self, irc, msg, args, seed):
        """<seed>

        Sets the internal RNG's seed value to <seed>.  <seed> must be a
        floating point number.
        """
        self.rng.seed(seed)
        irc.replySuccess()
    seed = wrap(seed, ['float'])

You'll notice first that argument list now includes an extra argument, seed. If
you read the wrap tutorial mentioned above, you should understand how this arg
list gets populated with values. Thanks to wrap we don't have to worry about
type-checking or value-checking or anything like that. We just specify that it
must be a float in the wrap portion and we can use it in the body of the
function.

Of course, we modify the docstring to document this function. Note the syntax
on the first line. Arguments go in <> and optional arguments should be
surrounded by [] (we'll demonstrate this later as well).

The body of the function should be fairly straightforward to figure out, but it
introduces a new function - irc.replySuccess. This is just a generic "I
succeeded" command which responds with whatever the bot owner has configured to
be the success response (configured in supybot.replies.success). Note that we
don't do any error-checking in the plugin, and that's because we simply don't
have to. We are guaranteed that seed will be a float and so the call to our
RNG's seed is guaranteed to work.

Lastly, of course, the wrap call. Again, read the wrap tutorial for fuller
coverage of its use, but the basic premise is that the second argument to wrap
is a list of converters that handles argument validation and conversion and it
then assigns values to each argument in the arg list after the first four
(required) arguments. So, our seed argument gets a float, guaranteed.

With this alone you'd be able to make some pretty usable plugin commands, but
we'll go through two more commands to introduce a few more useful ideas. The
next command we'll make is a sample command which gets a random sample of items
from a list provided by the user::

    def sample(self, irc, msg, args, n, items):
        """<number of items> <item1> [<item2> ...]

        Returns a sample of the <number of items> taken from the remaining
        arguments.  Obviously <number of items> must be less than the number
        of arguments given.
        """
        if n > len(items):
            irc.error('<number of items> must be less than the number '
                      'of arguments.')
            return
        sample = self.rng.sample(items, n)
        sample.sort()
        irc.reply(utils.str.commaAndify(sample))
    sample = wrap(sample, ['int', many('anything')])

This plugin command introduces a few new things, but the general structure
should look fairly familiar by now. You may wonder why we only have two extra
arguments when obviously this plugin can accept any number of arguments. Well,
using wrap we collect all of the remaining arguments after the first one into
the items argument. If you haven't caught on yet, wrap is really cool and
extremely useful.

Next of course is the updated docstring. Note the use of [] to denote the
optional items after the first item.

The body of the plugin should be relatively easy to read. First we check and
make sure that n (the number of items the user wants to sample) is not larger
than the actual number of items they gave. If it does, we call irc.error with
the error message you see. irc.error is kind of like irc.replySuccess only it
gives an error message using the configured error format (in
supybot.replies.error). Otherwise, we use the sample function from our RNG to
get a sample, then we sort it, and we reply with the 'utils.str.commaAndify'ed
version. The utils.str.commaAndify function basically takes a list of strings
and turns it into "item1, item2, item3, item4, and item5" for an arbitrary
length. More details on using the utils module can be found in the utils
tutorial.

Now for the last command that we will add to our plugin.py. This last command
will allow the bot users to roll an arbitrary n-sided die, with as many sides
as they so choose. Here's the code for this command::

    def diceroll(self, irc, msg, args, n):
        """[<number of sides>]

        Rolls a die with <number of sides> sides.  The default number of sides
        is 6.
        """
        s = 'rolls a %s' % self.rng.randrange(1, n)
        irc.reply(s, action=True)
    diceroll = wrap(diceroll, [additional(('int', 'number of sides'), 6)])

The only new thing learned here really is that the irc.reply method accepts an
optional argument action, which if set to True makes the reply an action
instead. So instead of just crudely responding with the number, instead you
should see something like * supybot rolls a 5. You'll also note that it uses a
more advanced wrap line than we have used to this point, but to learn more
about wrap, you should refer to the wrap tutorial

And now that we're done adding plugin commands you should see the boilerplate
stuff at the bottom, which just consists of::

    Class = Random

And also some vim modeline stuff. Leave these as is, and we're finally done
with plugin.py!

test.py
=======
Now that we've gotten our plugin written, we want to make sure it works. Sure,
an easy way to do a somewhat quick check is to start up a bot, load the plugin,
and run a few commands on it. If all goes well there, everything's probably
okay. But, we can do better than "probably okay". This is where written plugin
tests come in. We can write tests that not only assure that the plugin loads
and runs the commands fine, but also that it produces the expected output for
given inputs. And not only that, we can use the nifty supybot-test script to
test the plugin without even having to have a network connection to connect to
IRC with and most certainly without running a local IRC server.

The boilerplate code for test.py is a good start. It imports everything you
need and sets up RandomTestCase which will contain all of our tests. Now we
just need to write some test methods. I'll be moving fairly quickly here just
going over very basic concepts and glossing over details, but the full plugin
test authoring tutorial has much more detail to it and is recommended reading
after finishing this tutorial.

Since we have four commands we should have at least four test methods in our
test case class. Typically you name the test methods that simply checks that a
given command works by just appending the command name to test. So, we'll have
testRandom, testSeed, testSample, and testDiceRoll. Any other methods you want
to add are more free-form and should describe what you're testing (don't be
afraid to use long names).

First we'll write the testRandom method::

    def testRandom(self):
        # difficult to test, let's just make sure it works
        self.assertNotError('random')

Since we can't predict what the output of our random number generator is going
to be, it's hard to specify a response we want. So instead, we just make sure
we don't get an error by calling the random command, and that's about all we
can do.

Next, testSeed. In this method we're just going to check that the command
itself functions. In another test method later on we will check and make sure
that the seed produces reproducible random numbers like we would hope it would,
but for now we just test it like we did random in 'testRandom'::

    def testSeed(self):
        # just make sure it works
        self.assertNotError('seed 20')

Now for testSample. Since this one takes more arguments it makes sense that we
test more scenarios in this one. Also this time we have to make sure that we
hit the error that we coded in there given the right conditions::

    def testSample(self):
        self.assertError('sample 20 foo')
        self.assertResponse('sample 1 foo', 'foo')
        self.assertRegexp('sample 2 foo bar', '... and ...')
        self.assertRegexp('sample 3 foo bar baz', '..., ..., and ...')

So first we check and make sure trying to take a 20-element sample of a
1-element list gives us an error. Next we just check and make sure we get the
right number of elements and that they are formatted correctly when we give 1,
2, or 3 element lists.

And for the last of our basic "check to see that it works" functions,
testDiceRoll::

    def testDiceRoll(self):
        self.assertActionRegexp('diceroll', 'rolls a \d')

We know that diceroll should return an action, and that with no arguments it
should roll a single-digit number. And that's about all we can test reliably
here, so that's all we do.

Lastly, we wanted to check and make sure that seeding the RNG with seed
actually took effect like it's supposed to. So, we write another test method::

    def testSeedActuallySeeds(self):
        # now to make sure things work repeatably
        self.assertNotError('seed 20')
        m1 = self.getMsg('random')
        self.assertNotError('seed 20')
        m2 = self.getMsg('random')
        self.failUnlessEqual(m1, m2)
        m3 = self.getMsg('random')
        self.failIfEqual(m2, m3)

So we seed the RNG with 20, store the message, and then seed it at 20 again. We
grab that message, and unless they are the same number when we compare the two,
we fail. And then just to make sure our RNG is producing random numbers, we get
another random number and make sure it is distinct from the prior one.

Conclusion
==========
You are now very well-prepared to write Supybot plugins. Now for a few words of
wisdom with regards to Supybot plugin-writing.

* Read other people's plugins, especially the included plugins and ones by
  the core developers. We (the Supybot dev team) can't possibly document
  all the awesome things that Supybot plugins can do, but we try.
  Nevertheless there are some really cool things that can be done that
  aren't very well-documented.

* Hack new functionality into existing plugins first if writing a new
  plugin is too daunting.

* Come ask us questions in #supybot on Freenode or OFTC. Going back to the
  first point above, the developers themselves can help you even more than
  the docs can (though we prefer you read the docs first).

* Share your plugins with the world and make Supybot all that more
  attractive for other users so they will want to write their plugins for
  Supybot as well.

* Read, read, read all the documentation.

* And of course, have fun writing your plugins.
