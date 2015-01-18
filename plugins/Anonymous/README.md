Anonymous allows you to send messages anonymously as the bot. If 
`supybot.plugins.Anonymous.allowPrivateTarget` is `True`, you can send 
messages in query too.

## Usage examples

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
