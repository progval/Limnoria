Advanced Plugin Testing
-----------------------
  The complete guide to writing tests for your plugins.

Why Write Tests?
================
  Why should I write tests for my plugin? Here's why.

For those of you asking "Why should I write tests for my plugin? I tried it
out, and it works!", read on. For those of you who already realize that
Testing is Good (TM), skip to the next section.

Here are a few quick reasons why to test your Supybot plugins.

    * When/if we rewrite or change certain features in Supybot, tests make
    sure your plugin will work with these changes. It's much easier to run
    supybot-test MyPlugin after upgrading the code and before even reloading
    the bot with the new code than it is to load the bot with new code and
    then load the plugin only to realize certain things don't work. You may
    even ultimately decide you want to stick with an older version for a while
    as you patch your custom plugin. This way you don't have to rush a patch
    while restless users complain since you're now using a newer version that
    doesn't have the plugin they really like.

    * Running the automated tests takes a few seconds, testing plugins in IRC
    on a live bot generally takes quite a bit longer. We make it so that
    writing tests generally doesn't take much time, so a small initial
    investment adds up to lots of long-term gains.

    * If you want your plugin to be included in any of our releases (the core
    Supybot if you think it's worthy, or our supybot-plugins package), it has
    to have tests. Period.

For a bigger list of why to write unit tests, check out this article:

  http://www.onjava.com/pub/a/onjava/2003/04/02/javaxpckbk.html

and also check out what the Extreme Programming folks have to say about unit
tests:

  http://www.extremeprogramming.org/rules/unittests.html

Plugin Tests
============
  How to write tests for commands in your plugins.

Introduction

This tutorial assumes you've read through the plugin author tutorial, and that
you used supybot-plugin-create to create your plugin (as everyone should). So,
you should already have all the necessary imports and all that boilerplate
stuff in test.py already, and you have already seen what a basic plugin test
looks like from the plugin author tutorial. Now we'll go into more depth about
what plugin tests are available to Supybot plugin authors.

Plugin Test Case Classes

Supybot comes with two plugin test case classes, PluginTestCase and
ChannelPluginTestCase. The former is used when it doesn't matter whether or
not the commands are issued in a channel, and the latter is used for when it
does. For the most part their API is the same, so unless there's a distinction
between the two we'll treat them as one and the same when discussing their
functionality.

The Most Basic Plugin Test Case

At the most basic level, a plugin test case requires three things:

    * the class declaration (subclassing PluginTestCase or
      ChannelPluginTestCase)
    * a list of plugins that need to be loaded for these tests (does not
      include Owner, Misc, or Config, those are always automatically loaded) -
      often this is just the name of the plugin that you are writing tests for
    * some test methods

Here's what the most basic plugin test case class looks like (for a plugin
named MyPlugin):

    class MyPluginTestCase(PluginTestCase):
        plugins = ('MyPlugin',)

        def testSomething(self):
            # assertions and such go here

Your plugin test case should be named TestCase as you see above, though it
doesn't necessarily have to be named that way (supybot-plugin-create puts that
in place for you anyway). As you can see we elected to subclass PluginTestCase
because this hypothetical plugin apparently doesn't do anything
channel-specific.

As you probably noticed, the plugins attribute of the class is where the list
of necessary plugins goes, and in this case just contains the plugin that we
are testing. This will be the case for probably the majority of plugins. A lot
of the time test writers will use a bot function that performs some function
that they don't want to write code for and they will just use command nesting
to feed the bot what they need by using that plugin's functionality. If you
choose to do this, only do so with core bot plugins as this makes distribution
of your plugin simpler. After all, we want people to be able to run your
plugin tests without having to have all of your plugins!

One last thing to note before moving along is that each of the test methods
should describe what they are testing. If you want to test that your plugin
only responds to registered users, don't be afraid to name your test method
testOnlyRespondingToRegisteredUsers or testNotRespondingToUnregisteredUsers.
You may have noticed some rather long and seemingly unwieldy test method names
in our code, but that's okay because they help us know exactly what's failing
when we run our tests. With an ambiguously named test method we may have to
crack open test.py after running the tests just to see what it is that failed.
For this reason you should also test only one thing per test method. Don't
write a test method named testFoobarAndBaz. Just write two test methods,
testFoobar and testBaz. Also, it is important to note that test methods must
begin with test and that any method within the class that does begin with test
will be run as a test by the supybot-test program. If you want to write
utility functions in your test class that's fine, but don't name them
something that begins with test or they will be executed as tests.

Including Extra Setup

Some tests you write may require a little bit of setup. For the most part it's
okay just to include that in the individual test method itself, but if you're
duplicating a lot of setup code across all or most of your test methods it's
best to use the setUp method to perform whatever needs to be done prior to
each test method.

The setUp method is inherited from the whichever plugin test case class you
chose for your tests, and you can add whatever functionality you want to it.
Note the important distinction, however: you should be adding to it and not
overriding it. Just define setUp in your own plugin test case class and it
will be run before all the test methods are invoked.

Let's do a quick example of one. Let's write a setUp method which registers a
test user for our test bot:

    def setUp(self):
        ChannelPluginTestCase.setUp(self)  # important!!
        # Create a valid user to use
        self.prefix = 'foo!bar@baz'
        self.feedMsg('register tester moo', to=self.nick, frm=self.prefix))
        m = self.getMsg()  # Response to registration.

Now notice how the first line calls the parent class's setUp method first?
This must be done first. Otherwise several problems are likely to arise. For
one, you wouldn't have an irc object at self.irc that we use later on nor
would self.nick be set.

As for the rest of the method, you'll notice a few things that are available
to the plugin test author. self.prefix refers to the hostmask of the
hypothetical test user which will be "talking" to the bot, issuing commands.
We set it to some generically fake hostmask, and then we use feedMsg to send
a private message (using the bot's nick, accessible via self.nick) to the bot
registering the username "tester" with the password "moo". We have to do it
this way (rather than what you'll find out is the standard way of issuing
commands to the bot in test cases a little later) because registration must be
done in private. And lastly, since feedMsg doesn't dequeue any messages from
the bot after being fed a message, we perform a getMsg to get the response.
You're not expected to know all this yet, but do take note of it since using
these methods in test-writing is not uncommon. These utility methods as well as
all of the available assertions are covered in the next section.

So, now in any of the test methods we write, we'll be able to count on the
fact that there will be a registered user "tester" with a password of "moo",
and since we changed our prefix by altering self.prefix and registered after
doing so, we are now identified as this user for all messages we send unless
we specify that they are coming from some other prefix.

The Opposite of Setting-up: Tearing Down

If you did some things in your setUp that you want to clean up after, then
this code belongs in the tearDown method of your test case class. It's
essentially the same as setUp except that you probably want to wait to invoke
the parent class's tearDown until after you've done all of your tearing down.
But do note that you do still have to invoke the parent class's tearDown
method if you decide to add in your own tear-down stuff.

Setting Config Variables for Testing

Before we delve into all of the fun assertions we can use in our test methods
it's worth noting that each plugin test case can set custom values for any
Supybot config variable they want rather easily. Much like how we can simply
list the plugins we want loaded for our tests in the plugins attribute of our
test case class, we can set config variables by creating a mapping of
variables to values with the config attribute.

So if, for example, we wanted to disable nested commands within our plugin
testing for some reason, we could just do this:

    class MyPluginTestCase(PluginTestCase):
        config = {'supybot.commands.nested': False}

        def testThisThing(self):
            # stuff

And now you can be assured that supybot.commands.nested is going to be off for
all of your test methods in this test case class.

Plugin Test Methods
===================
  The full list of test methods and how to use them.

Introduction

You know how to make plugin test case classes and you know how to do just
about everything with them except to actually test stuff. Well, listed below
are all of the assertions used in tests. If you're unfamiliar with what an
assertion is in code testing, it is basically a requirement of something that
must be true in order for that test to pass. It's a necessary condition. If
any assertion within a test method fails the entire test method fails and it
goes on to the next one.

Assertions

All of these are methods of the plugin test classes themselves and hence are
accessed by using self.assertWhatever in your test methods. These are sorted
in order of relative usefulness.

    * assertResponse(query, expectedResponse) - Feeds query to the bot as a
        message and checks to make sure the response is expectedResponse. The
        test fails if they do not match (note that prefixed nicks in the
        response do not need to be included in the expectedResponse).

    * assertError(query) - Feeds query to the bot and expects an error in
        return. Fails if the bot doesn't return an error.

    * assertNotError(query) - The opposite of assertError. It doesn't matter
        what the response to query is, as long as it isn't an error. If it is
        not an error, this test passes, otherwise it fails.

    * assertRegexp(query, regexp, flags=re.I) - Feeds query to the bot and
        expects something matching the regexp (no m// required) in regexp with
        the supplied flags. Fails if the regexp does not match the bot's
        response.

    * assertNotRegexp(query, regexp, flags=re.I) - The opposite of
        assertRegexp. Fails if the bot's output matches regexp with the
        supplied flags.

    * assertHelp(query) - Expects query to return the help for that command.
        Fails if the command help is not triggered.

    * assertAction(query, expectedResponse=None) - Feeds query to the bot and
        expects an action in response, specifically expectedResponse if it is
        supplied. Otherwise, the test passes for any action response.

    * assertActionRegexp(query, regexp, flags=re.I) - Basically like
        assertRegexp but carries the extra requirement that the response must
        be an action or the test will fail.

Utilities

    * feedMsg(query, to=None, frm=None) - Simply feeds query to whoever is
        specified in to or to the bot itself if no one is specified. Can also
        optionally specify the hostmask of the sender with the frm keyword.
        Does not actually perform any assertions.

    * getMsg(query) - Feeds query to the bot and gets the response.

Other Tests
===========
  If you had to write helper code for a plugin and want to test it, here's
  how.

Previously we've only discussed how to test stuff in the plugin that is
intended for IRC. Well, we realize that some Supybot plugins will require
utility code that doesn't necessarily require all of the overhead of setting
up IRC stuff, and so we provide a more lightweight test case class,
SupyTestCase, which is a very very light wrapper around unittest.TestCase
(from the standard unittest module) that basically just provides a little
extra logging. This test case class is what you should use for writing those
test cases which test things that are independent of IRC.

For example, in the MoobotFactoids plugin there is a large chunk of utility
code dedicating to parsing out random choices within a factoid using a class
called OptionList. So, we wrote the OptionListTestCase as a SupyTestCase for
the MoobotFactoids plugin. The setup for test methods is basically the same as
before, only you don't have to define plugins since this is independent of
IRC.

You still have the choice of using setUp and tearDown if you wish, since those
are inherited from unittest.TestCase. But, the same rules about calling the
setUp or tearDown method from the parent class still apply.

With all this in hand, now you can write great tests for your Supybot plugins!

