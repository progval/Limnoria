This plugin allows the user to create various aliases (known as "Akas", 
since Alias is the name of another plugin Aka is based on) to other 
commands or combinations of other commands (via nested commands).  
It is a good idea to always quote the commands that are being aliased so 
that any nested commands are not immediately run.

Basic usage
-----------

### Alias

Add an aka, Alias, which eases the transitioning to Aka from Alias.

First we will load Alias and Aka.

```
<jamessan> @load Alias
<bot> jamessan: The operation succeeded.
<jamessan> @load Aka
<bot> jamessan: The operation succeeded.

```

Then we import the Alias database to Aka in case it exists and unload 
Alias.

```
<jamessan> @importaliasdatabase
<bot> jamessan: The operation succeeded.
<jamessan> @unload Alias
<bot> jamessan: The operation succeeded.
```

And now we will finally add the Aka `alias` itself.

```
<jamessan> @aka add "alias" "aka $1 $*"
<bot> jamessan: The operation succeeded.
```

Now you can use Aka as you used Alias before.

### Trout

Add an aka, trout, which expects a word as an argument

```
<jamessan> @aka add trout "reply action slaps $1 with a large trout"
<bot> jamessan: The operation succeeded.
<jamessan> @trout me
* bot slaps me with a large trout
```

This `trout` aka requires the plugin `Reply` to be loaded since it 
provides the `action` command.

### LastFM

Add an aka, `lastfm`, which expects a last.fm username and replies with 
their most recently played item.

```
@aka add lastfm "rss [format concat http://ws.audioscrobbler.com/1.0/user/ [format concat [web urlquote $1] /recenttracks.rss]]"
```

This `lastfm` aka requires the following plugins to be loaded: `RSS`, 
`Format` and `Web`.

`RSS` provides `rss`, `Format provides `concat` and `Web` provides 
`urlquote`.

Note that if the nested commands being aliased hadn't been quoted, then
those commands would have been run immediately, and `@lastfm` would always
reply with the same information, the result of those commands.
