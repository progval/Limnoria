PYTHON=`which python3`
DESTDIR=/
PROJECT=limnoria

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make buildrpm - Generate a rpm package"
	@echo "make builddeb_py2 - Generate a deb package for Python 2"
	@echo "make builddeb_py3 - Generate a deb package for Python 3"
	@echo "make clean - Get rid of scratch and byte files"

test:
	PATH=./scripts/:${PATH} PYTHONPATH=. $(PYTHON) ./scripts/supybot-test test --plugins-dir=plugins/

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE)

buildrpm:
	$(PYTHON) setup.py bdist_rpm

builddeb_py2:
	cp debian/control.py2 debian/control
	debuild -us -uc
	rm debian/control

builddeb_py3:
	cp debian/control.py3 debian/control
	debuild -us -uc
	rm debian/control

clean:
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete
	rm debian/control

.PHONY: test
