JADE=/usr/bin/jade
JADETEX=/usr/bin/jadetex
DVIPDF=/usr/bin/dvipdfm
HTMLSTYLESHEET=/usr/share/sgml/docbook/stylesheet/dsssl/modular/html/docbook.dsl
PRINTSTYLESHEET=/usr/share/sgml/docbook/stylesheet/dsssl/modular/print/docbook.dsl 

html: example.sgml capabilities.sgml
	$(JADE) -t xml -d $(HTMLSTYLESHEET) $<

example.dvi: example.sgml
	$(JADE) -t tex -d $(PRINTSTYLESHEET) $<
	$(JADETEX) $(addsuffix .tex, $(basename $<))

example.pdf: example.dvi
	$(DVIPDF) -o $(addsuffix .pdf, $(basename $<)) $<

capabilities.dvi: capabilities.sgml
	$(JADE) -t tex -d $(PRINTSTYLESHEET) $<
	$(JADETEX) $(addsuffix .tex, $(basename $<))

capabilities.pdf: capabilities.dvi
	$(DVIPDF) -o $(addsuffix .pdf, $(basename $<)) $<

clean:
	rm -f *.html
