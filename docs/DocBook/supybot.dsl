<!DOCTYPE style-sheet PUBLIC "-//James Clark//DTD DSSSL Style Sheet//EN" [
  <!ENTITY print-ss PUBLIC 
  "-//Norman Walsh//DOCUMENT DocBook Print Stylesheet//EN" CDATA DSSSL>
  <!ENTITY html-ss PUBLIC
  "-//Norman Walsh//DOCUMENT DocBook HTML Stylesheet//EN" CDATA DSSSL>
  <!ENTITY supybot-print SYSTEM "supybot-print.dsl">
  <!ENTITY supybot-html SYSTEM "supybot-html.dsl">
]>

<style-sheet>
<style-specification id="print" use="print-stylesheet">
    <style-specification-body>
    &supybot-print;
    </style-specification-body>
</style-specification>
<style-specification id="html" use="html-stylesheet">
    <style-specification-body>
    &supybot-html;
    </style-specification-body>
</style-specification>
<external-specification id="print-stylesheet" document="print-ss">
<external-specification id="html-stylesheet" document="html-ss">
</style-sheet>
