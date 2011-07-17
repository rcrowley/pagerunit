VERSION=0.0.3
BUILD=2

PYTHON=$(shell which python2.7 || which python27 || which python2.6 || which python26 || which python)
PYTHON_VERSION=$(shell $(PYTHON) -c "from distutils.sysconfig import get_python_version; print(get_python_version())")

prefix=/usr/local
bindir=$(prefix)/bin
libdir=$(prefix)/lib
pydir=$(shell $(PYTHON) pydir.py $(libdir))
mandir=$(prefix)/share/man

all:

clean:
	rm -rf \
		control *.deb \
		setup.py build dist *.egg *.egg-info \
		man/man*/*.html
	find . -name \*.pyc -delete

test:
	nosetests --with-coverage --cover-package=pagerunit

install: install-bin install-lib install-man

install-bin:
	install -d $(DESTDIR)$(bindir)
	find bin -type f -printf %P\\0 | xargs -0r -I__ install bin/__ $(DESTDIR)$(bindir)/__

install-lib:
	find pagerunit -type d -printf %P\\0 | xargs -0r -I__ install -d $(DESTDIR)$(pydir)/pagerunit/__
	find pagerunit -type f -name \*.py -printf %P\\0 | xargs -0r -I__ install -m644 pagerunit/__ $(DESTDIR)$(pydir)/pagerunit/__
	PYTHONPATH=$(DESTDIR)$(pydir) $(PYTHON) -mcompileall $(DESTDIR)$(pydir)/pagerunit

install-man:
	find man -type d -printf %P\\0 | xargs -0r -I__ install -d $(DESTDIR)$(mandir)/__
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ install -m644 man/__ $(DESTDIR)$(mandir)/__
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ gzip $(DESTDIR)$(mandir)/__

uninstall: uninstall-bin uninstall-lib uninstall-man

uninstall-bin:
	find bin -type f -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(bindir)/__
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(bindir) || true

uninstall-lib:
	find pagerunit -type f -name \*.py -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(pydir)/pagerunit/__ $(DESTDIR)$(pydir)/pagerunit/__c
	find pagerunit -depth -mindepth 1 -type d -printf %P\\0 | xargs -0r -I__ rmdir $(DESTDIR)$(pydir)/pagerunit/__ || true
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(pydir)/pagerunit || true

uninstall-man:
	find man -type f -name \*.[12345678] -printf %P\\0 | xargs -0r -I__ rm -f $(DESTDIR)$(mandir)/__.gz
	find man -depth -mindepth 1 -type d -printf %P\\0 | xargs -0r -I__ rmdir $(DESTDIR)$(mandir)/__ || true
	rmdir -p --ignore-fail-on-non-empty $(DESTDIR)$(mandir) || true

build: build-deb build-pypi

build-deb:
	make install prefix=/usr DESTDIR=debian
	fpm -s dir -t deb -C debian \
		-n pagerunit -v $(VERSION)-$(BUILD)py$(PYTHON_VERSION) -a all \
		-d python$(PYTHON_VERSION) \
		-m "Richard Crowley <r@rcrowley.org>" \
		--url "https://github.com/rcrowley/pagerunit" \
		--description "A simple Nagios alternative made to look like unit tests."
	make uninstall prefix=/usr DESTDIR=debian

build-pypi:
	m4 -D__VERSION__=$(VERSION) setup.py.m4 >setup.py
	$(PYTHON) setup.py bdist_egg

deploy: deploy-deb deploy-pypi

deploy-deb:
	scp -i ~/production.pem pagerunit_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb ubuntu@packages.devstructure.com:
	make deploy-deb-py$(PYTHON_VERSION)
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "rm pagerunit_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb"

deploy-deb-py2.6:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add pagerunit_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/lenny apt/squeeze apt/lucid apt/maverick"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight cache apt/lenny apt/squeeze apt/lucid apt/maverick"

deploy-deb-py2.7:
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight add pagerunit_$(VERSION)-$(BUILD)py$(PYTHON_VERSION)_all.deb apt/natty"
	ssh -i ~/production.pem -t ubuntu@packages.devstructure.com "sudo freight cache apt/natty"

deploy-pypi:
	$(PYTHON) setup.py sdist upload

man:
	find man -name \*.ronn | xargs -n1 ronn --manual=PagerUnit --style=toc

gh-pages: man
	mkdir -p gh-pages
	find man -name \*.html | xargs -I__ mv __ gh-pages/
	git checkout -q gh-pages
	cp -R gh-pages/* ./
	rm -rf gh-pages
	git add .
	git commit -m "Rebuilt manual."
	git push origin gh-pages
	git checkout -q master

.PHONY: all clean install install-bin install-lib install-man uninstall uninstall-bin uninstall-lib uninstall-man build build-deb build-pypi deploy deploy-deb deploy-deb-py2.6 deploy-deb-py2.7 deploy-pypi man gh-pages
