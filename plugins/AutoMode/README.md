This plugin sets channel modes on users when they join the channel 
depending on the configuration.

If
* `plugins.automode.op` is set to `True`, users with the `#channel,op` 
capability are opped when they join.
* `plugins.automode.halfop` is set to `True`, users with the 
`#channel,halfop` are halfopped when they join.
* `plugins.automode.voice` is set to `True`, users with the 
`#channel,voice` are voiced when they join.

This plugin also kbans people on `@channel ban list` 
(`config plugins.automode.ban`) when they join and if moding users with 
lower capability is enabled, that is also applied to users with higher 
capability (`config plugins.automode.fallthrough).
