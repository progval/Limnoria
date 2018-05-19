History replacer using sed-style expressions.

### Configuration

Enable SedRegex on the desired channels: `config channel #yourchannel plugins.sedregex.enable True`

### Usage

After enabling SedRegex, typing a regex in the form `s/text/replacement/` will make the bot announce replacements.

```
20:24 <~GL> helli world
20:24 <~GL> s/i/o/
20:24 <@Lily> GL meant to say: hello world
```

You can also do `othernick: s/text/replacement/` to only replace messages from a certain user. Supybot ignores are respected by the plugin, and messages from ignored users will only be considered if their nick is explicitly given.

#### Regex flags

The following regex flags (i.e. the `g` in `s/abc/def/g`, etc.) are supported:

- `i`: case insensitive replacement
- `g`: replace all occurences of the original text
- `s`: *(custom flag specific to this plugin)* replace only messages from the caller
