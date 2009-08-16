Advanced Plugin Config
----------------------
This tutorial covers some of the more advanced plugin config features available
to Supybot plugin authors.

What's This Tutorial For?
=========================
  Brief overview of what this tutorial covers and the target audience.

Want to know the crazy advanced features available to you, the Supybot plugin
author? Well, this is the tutorial for you. This article assumes you've read
the Supybot plugin author tutorial since all the basics of plugin config are
handled there first.

In this tutorial we'll cover:

    * Using the configure function more effectively by using the functions
      provided in supybot.questions
    * Creating config variable groups and config variables underneath those
      groups.
    * The built-in config variable types ("registry types") for use with config
      variables
    * Creating custom registry types to handle config variable values more
      effectively

Using 'configure' effectively
=============================
  How to use 'configure' effectively using the functions from
  'supybot.questions'

In the original Supybot plugin author tutorial you'll note that we gloss over
the configure portion of the config.py file for the sake of keeping the
tutorial to a reasonable length. Well, now we're going to cover it in more
detail.

The supybot.questions module is a nice little module coded specifically to help
clean up the configure section of every plugin's config.py. The boilerplate
config.py code imports the four most useful functions from that module:

    * "expect" is a very general prompting mechanism which can specify certain
      inputs that it will accept and also specify a default response. It takes
      the following arguments:
          - prompt: The text to be displayed
          - possibilities: The list of possible responses (can be the empty
            list, [])
          - default (optional): Defaults to None. Specifies the default value
            to use if the user enters in no input.
          - acceptEmpty (optional): Defaults to False. Specifies whether or not
            to accept no input as an answer.

    * "anything" is basically a special case of expect which takes anything
      (including no input) and has no default value specified. It takes only
      one argument:
          - prompt: The text to be displayed

    * "something" is also a special case of expect, requiring some input and
      allowing an optional default. It takes the following arguments:
          - prompt: The text to be displayed
          - default (optional): Defaults to None. The default value to use if
            the user doesn't input anything.

    * "yn" is for "yes or no" questions and basically forces the user to input
      a "y" for yes, or "n" for no. It takes the following arguments:
          - prompt: The text to be displayed
          - default (optional): Defaults to None. Default value to use if the
            user doesn't input anything.

All of these functions, with the exception of "yn", return whatever string
results as the answer whether it be input from the user or specified as the
default when the user inputs nothing. The "yn" function returns True for "yes"
answers and False for "no" answers.

For the most part, the latter three should be sufficient, but we expose expect
to anyone who needs a more specialized configuration.

Let's go through a quick example configure that covers all four of these
functions. First I'll give you the code, and then we'll go through it,
discussing each usage of a supybot.questions function just to make sure you
realize what the code is actually doing. Here it is:

  def configure(advanced):
      # This will be called by supybot to configure this module.  advanced is
      # a bool that specifies whether the user identified himself as an advanced
      # user or not.  You should effect your configuration by manipulating the
      # registry as appropriate.
      from supybot.questions import expect, anything, something, yn
      WorldDom = conf.registerPlugin('WorldDom', True)
      if yn("""The WorldDom plugin allows for total world domination
               with simple commands.  Would you like these commands to
               be enabled for everyone?""", default=False):
          WorldDom.globalWorldDominationRequires.setValue("")
      else:
          cap = something("""What capability would you like to require for
                             this command to be used?""", default="Admin")
          WorldDom.globalWorldDominationRequires.setValue(cap)
      dir = expect("""What direction would you like to attack from in
                      your quest for world domination?""",
                   ["north", "south", "east", "west", "ABOVE"],
                   default="ABOVE")
      WorldDom.attackDirection.setValue(dir)

As you can see, this is the WorldDom plugin, which I am currently working on.
The first thing our configure function checks is to see whether or not the bot
owner would like the world domination commands in this plugin to be available
to everyone. If they say yes, we set the globalWorldDominationRequires
configuration variable to the empty string, signifying that no specific
capabilities are necessary. If they say no, we prompt them for a specific
capability to check for, defaulting to the "Admin" capability. Here they can
create their own custom capability to grant to folks which this plugin will
check for if they want, but luckily for the bot owner they don't really have to
do this since Supybot's capabilities system can be flexed to take care of this.

Lastly, we check to find out what direction they want to attack from as they
venture towards world domination. I prefer "death from above!", so I made that
the default response, but the more boring cardinal directions are available as
choices as well.

Using Config Groups
===================
  A brief overview of how to use config groups to organize config variables

Supybot's Hierarchical Configuration

Supybot's configuration is inherently hierarchical, as you've probably already
figured out in your use of the bot. Naturally, it makes sense to allow plugin
authors to create their own hierarchies to organize their configuration
variables for plugins that have a lot of plugin options. If you've taken a look
at the plugins that Supybot comes with, you've probably noticed that several of
them take advantage of this. In this section of this tutorial we'll go over how
to make your own config hierarchy for your plugin.

Here's the brilliant part about Supybot config values which makes hierarchical
structuring all that much easier - values are groups. That is, any config value
you may already defined in your plugins can already be treated as a group, you
simply need to know how to add items to that group.

Now, if you want to just create a group that doesn't have an inherent value you
can do that as well, but you'd be surprised at how rarely you have to do that.
In fact if you look at most of the plugins that Supybot comes with, you'll only
find that we do this in a handful of spots yet we use the "values as groups"
feature quite a bit.

Creating a Config Group
=======================

As stated before, config variables themselves are groups, so you can create a
group simply by creating a configuration variable:

    conf.registerGlobalValue(WorldDom, 'globalWorldDominationRequires',
        registry.String('', """Determines the capability required to access the
                               world domination commands in this plugin."""))

As you probably know by now this creates the config variable
supybot.plugins.WorldDom.globalWorldDominationRequires which you can access/set
using the Config plugin directly on the running bot. What you may not have
known prior to this tutorial is that that variable is also a group.
Specifically, it is now the WorldDom.globalWorldDominationRequires group, and
we can add config variables to it! Unfortunately, this particular bit of
configuration doesn't really require anything underneath it, so let's create a
new group which does using the "create only a group, not a value" command.

Let's create a configurable list of targets for different types of attacks
(land, sea, air, etc.). We'll call the group attackTargets. Here's how you
create just a config group alone with no value assigned:

    conf.registerGroup(WorldDom, 'attackTargets')

The first argument is just the group under which you want to create your new
group (and we got WorldDom from conf.registerPlugin which was in our
boilerplate code from the plugin creation wizard). The second argument is, of
course, the group name. So now we have WorldDom.attackTargets (or, fully,
supybot.plugins.WorldDom.attackTargets).

Adding Values to a Group
========================

Actually, you've already done this several times, just never to a custom group
of your own. You've always added config values to your plugin's config group.
With that in mind, the only slight modification needed is to simply point to
the new group:

    conf.registerGlobalValue(WorldDom.attackTargets, 'air',
        registry.SpaceSeparatedListOfStrings('', """Contains the list of air
                                                    targets."""))

And now we have a nice list of air targets! You'll notice that the first
argument is WorldDom.attackTargets, our new group. Make sure that the
conf.registerGroup call is made before this one or else you'll get a nasty
AttributeError.

The Built-in Registry Types
===========================
  A rundown of all of the built-in registry types available for use with config
  variables.

The "registry" module defines the following config variable types for your use
(I'll include the 'registry.' on each one since that's how you'll refer to it in
code most often). Most of them are fairly self-explanatory, so excuse the
boring descriptions:

    * registry.Boolean - A simple true or false value. Also accepts the
        following for true: "true", "on" "enable", "enabled", "1", and the
        following for false: "false", "off", "disable", "disabled", "0",

    * registry.Integer - Accepts any integer value, positive or negative.

    * registry.NonNegativeInteger - Will hold any non-negative integer value.

    * registry.PositiveInteger - Same as above, except that it doesn't accept 0
        as a value.

    * registry.Float - Accepts any floating point number.

    * registry.PositiveFloat - Accepts any positive floating point number.

    * registry.Probability - Accepts any floating point number between 0 and 1
        (inclusive, meaning 0 and 1 are also valid).

    * registry.String - Accepts any string that is not a valid Python command

    * registry.NormalizedString - Accepts any string (with the same exception
        above) but will normalize sequential whitespace to a single space..

    * registry.StringSurroundedBySpaces - Accepts any string but assures that
        it has a space preceding and following it. Useful for configuring a
        string that goes in the middle of a response.

    * registry.StringWithSpaceOnRight - Also accepts any string but assures
        that it has a space after it. Useful for configuring a string that
        begins a response.

    * registry.Regexp - Accepts only valid (Perl or Python) regular expressions

    * registry.SpaceSeparatedListOfStrings - Accepts a space-separated list of
        strings.

There are a few other built-in registry types that are available but are not
usable in their current state, only by creating custom registry types, which
we'll go over in the next section.

Custom Registry Types
=====================
  How to create and use your own custom registry types for use in customizing
  plugin config variables.

Why Create Custom Registry Types?

For most configuration, the provided types in the registry module are
sufficient. However, for some configuration variables it's not only convenient
to use custom registry types, it's actually recommended. Customizing registry
types allows for tighter restrictions on the values that get set and for
greater error-checking than is possible with the provided types.

What Defines a Registry Type?

First and foremost, it needs to subclass one of the existing registry types
from the registry module, whether it be one of the ones in the previous section
or one of the other classes in registry specifically designed to be subclassed.

Also it defines a number of other nice things: a custom error message for your
type, customized value-setting (transforming the data you get into something
else if wanted), etc.

Creating Your First Custom Registry Type

As stated above, priority number one is that you subclass one of the types in
the registry module. Basically, you just subclass one of those and then
customize whatever you want. Then you can use it all you want in your own
plugins. We'll do a quick example to demonstrate.

We already have registry.Integer and registry.PositiveInteger, but let's say we
want to accept only negative integers. We can create our own NegativeInteger
registry type like so:

    class NegativeInteger(registry.Integer):
        """Value must be a negative integer."""
        def setValue(self, v):
            if v >= 0:
                self.error()
            registry.Integer.setValue(self, v)

All we need to do is define a new error message for our custom registry type
(specified by the docstring for the class), and customize the setValue
function. Note that all you have to do when you want to signify that you've
gotten an invalid value is to call self.error(). Finally, we call the parent
class's setValue to actually set the value.

What Else Can I Customize?

Well, the error string and the setValue function are the most useful things
that are available for customization, but there are other things. For examples,
look at the actual built-in registry types defined in registry.py (in the src
directory distributed with the bot).

What Subclasses Can I Use?

Chances are one of the built-in types in the previous section will be
sufficient, but there are a few others of note which deserve mention:

    * registry.Value - Provides all the core functionality of registry types
        (including acting as a group for other config variables to reside
        underneath), but nothing more.

    * registry.OnlySomeStrings - Allows you to specify only a certain set of
        strings as valid values. Simply override validStrings in the inheriting
        class and you're ready to go.

    * registry.SeparatedListOf - The generic class which is the parent class to
        registry.SpaceSeparatedListOfStrings. Allows you to customize four
        things: the type of sequence it is (list, set, tuple, etc.), what each
        item must be (String, Boolean, etc.), what separates each item in the
        sequence (using custom splitter/joiner functions), and whether or not
        the sequence is to be sorted.  Look at the definitions of
        registry.SpaceSeparatedListOfStrings and
        registry.CommaSeparatedListOfStrings at the bottom of registry.py for
        more information. Also, there will be an example using this in the
        section below.

Using My Custom Registry Type

Using your new registry type is relatively straightforward. Instead of using
whatever registry built-in you might have used before, now use your own custom
class. Let's say we define a registry type to handle a comma-separated list of
probabilities:

    class CommaSeparatedListOfProbabilities(registry.SeparatedListOf):
        Value = registry.Probability
        def splitter(self, s):
            return re.split(r'\s*,\s*', s)
        joiner = ', '.join

Now, to use that type we simply have to specify it whenever we create a config
variable using it:

    conf.registerGlobalValue(SomePlugin, 'someConfVar',
        CommaSeparatedListOfProbabilities('0.0, 1.0', """Holds the list of
        probabilities for whatever."""))

Note that we initialize it just the same as we do any other registry type, with
two arguments: the default value, and then the description of the config
variable.

