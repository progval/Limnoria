JADE=/usr/bin/jade
STYLESHEET=/usr/share/sgml/docbook/stylesheet/dsssl/modular/html/docbook.dsl

example: example.sgml 
	$(JADE) -t xml -d $(STYLESHEET) $<

clean:
	rm -f *.html
