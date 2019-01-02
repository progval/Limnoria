# Contributing to Limnoria

## Guidelines

Follow the [Style Guidelines].

When adding a string that will be shown on IRC, always internationalize
it (wrap it in a call to `_()`).
When making a trivial change to an internationalized string that does not
affect the meaning of the string (typo fix, etc.), please update the
`msgid` entry in localization file. It helps preserve the translation
without the translator having to review it.

Last rule: you shouldn't add a mandatory dependency. Limnoria does not
come with any (besides Python), so please try to keep all dependencies
optional.

[Style Guidelines]:https://limnoria.readthedocs.io/en/latest/develop/style.html

## Sending patches

When you send a pull request, **send it to the testing branch**. 
It will be merged to master when it's considered to be stable enough to be 
supported.

Don't fear that you spam Limnoria by sending many pull requests. According 
to @ProgVal, it's easier for them to accept pull requests than to 
cherry-pick everything manually.

Having at least one test case in any non-trivial pull-request
is very appreciated.

See also [Contributing to Limnoria] at [Limnoria documentation].

[Contributing to Limnoria]:https://limnoria.readthedocs.io/en/latest/contribute/index.html

[Limnoria documentation]:https://limnoria.readthedocs.io/
