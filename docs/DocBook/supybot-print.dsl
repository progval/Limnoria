(define %mono-font-family% "Courier New")

(element botcommand
    (make sequence
        font-family-name: %mono-font-family%))

(element plugin
    (make sequence
        font-weight: 'bold))

(element flag
    (make sequence
        font-posture: 'italic))

(element nick
    (make sequence
        font-family-name: %mono-font-family%))

(element capability
    (make sequence
        font-weight: 'bold))

(element registrygroup
    (make sequence
        font-weight: 'bold))

(element ircsession
    (make paragraph
        font-family-name: %mono-font-family%
        space-before: 12pt
        space-after: 12pt
        start-indent: 6pt
        lines: 'asis
        input-whitespace-treatment: 'preserve))

(element script
    (make sequence
        font-family-name: %mono-font-family%))

(element channel
    (make sequence
        font-weight: 'bold))

