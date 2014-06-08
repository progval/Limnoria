Anonymous allows you to send messages anonymously as the bot. If 
`supybot.plugins.Anonymous.allowPrivateTarget` is `True`, you can send 
messages in query too.

## Usage examples

### Identifying to NickServ

One usage example is to identify the bot with NickServ if it fails to 
identify for some reason.

However this isn't recommended unless you don't use CertFP.

#### SASL

```
@config networks.<network>.sasl.username NSACCOUNTNAME
@config networks.<network>.sasl.password NSPASSWORD
```

Next time when your bot connects it should identify before connecting with 
SASL.

#### CertFP

For help with generating the certificate [please see this page.](https://mkaysi.github.io/pages/external/identifying.html#certfp)

When you have generated the certificate tell the bot to use it by either 
of thse two commands (or both). The first tells the bot to use the 
certificate everywhere and the second only on one network. If you run 
the first, the second isn't necressary unless you have multiple 
certificates.

```
@config protocols.irc.certfile /home/username/bot/bot.pem
@config networks.<network>.certfile /home/username/bot/bot.pem
```

### Proving that you are the owner.

When you ask for cloak/vhost for your bot, the network operators will 
often ask you to prove that you own the bot. You can do this for example 
with the following method:

```
@load Anonymous
@config plugins.anonymous.requirecapability owner
@config plugins.anonymous.allowprivatetarget True
@anonymous say <operator nick> Hi, my owner is <your nick> :)
```

This
* Loads the plugin.
* Makes the plugin require that you are the owner
    * If anyone could send private messages as the bot, they could also 
    access network services.
* Allows sending private messages
* Sends message `Hi, my owner is <your nick> :)` to `operator nick`.
    * Note that you won't see the messages that are sent to the bot.
