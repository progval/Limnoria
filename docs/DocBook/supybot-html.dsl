(define %stylesheet% "../stylesheets/supybot.css")

(element botcommand
    (make element gi: "span"
        attributes: '(("class" "botcommand"))
        (process-children)))

(element plugin
    (make element gi: "span"
        attributes: '(("class" "plugin"))
        (process-children)))

(element flag
    (make element gi: "span"
        attributes: '(("class" "flag"))
        (process-children)))

(element nick
    (make element gi: "span"
        attributes: '(("class" "nick"))
        (process-children)))

(element capability
    (make element gi: "span"
        attributes: '(("class" "capability"))
        (process-children)))

(element registrygroup
    (make element gi: "span"
        attributes: '(("class" "registrygroup"))
        (process-children)))

(element ircsession
    (make element gi: "pre"
        attributes: '(("class" "ircsession"))
        (process-children)))

(element script
    (make element gi: "span"
        attributes: '(("class" "script"))
        (process-children)))

(element channel
    (make element gi: "span"
        attributes: '(("class" "channel"))
        (process-children)))
