# Contributing to Limnoria

## Guidelines

Follow the [Style Guidelines].

When adding a string that will be shown on IRC, always internationalize
it (wrap it in a call to `_()`).
When making a trivial change to an internationalized string that does not
affect the meaning of the string (typo fix, etc.), please update the
`msgid` entry in localization file. It helps preserve the translation
without the translator having to review it.


[Style Guidelines]:http://supybot.aperio.fr/doc/develop/style.html

## Sending patches

When you send a pull request, **send it to the testing branch**. 
It will be merged to master when it's considered to be enough stable to be 
supported.

Don't fear that you spam Limnoria by sending many pull requests. According 
to @ProgVal, it's easier for them to accept pull requests than to 
cherry-pick everything manually.

See also [Contributing to Limnoria] at [Limnoria documentation].

[Contributing to Limnoria]:http://supybot.aperio.fr/doc/contribute/index.html#contributing-to-limnoria

[Limnoria documentation]:http://supybot.aperio.fr/doc/index.html
