# PagerUnit

A simple Nagios alternative made to look like unit tests.

This is probably a bad idea but I wanted to get something on paper (as it were) so I could get back to [real](https://github.com/devstructure/blueprint) [work](https://github.com/devstructure/blueprint-io).

## Usage

Configure PagerUnit so it can send email in `/etc/pagerunit.cfg` or `~/.pagerunit.cfg`:

	[mail]
	address = recipient@example.com
	password = password
	port = 587
	server = smtp.gmail.com
	username = sender@gmail.com

Define some tests a la [Nose](http://somethingaboutorange.com/mrl/projects/nose/1.0.0/):

	def foo():
	    """
	    Docstring for foo.
	    """
	    assert False, 'Assertion for foo.'

Run them every 10 seconds:

	PYTHONPATH="$PWD" PATH="$PATH:$PWD/bin" pagerunit --loop example.py

## Installation

Prerequisites:

* Python >= 2.6

### From source

	git clone git://github.com/rcrowley/pagerunit.git
	cd pagerunit && make && sudo make install

### From DevStructure's Debian archive

<pre><code>echo "deb http://packages.devstructure.com <em>release</em> main" | sudo tee /etc/apt/sources.list.d/devstructure.list
sudo wget -O /etc/apt/trusted.gpg.d/devstructure.gpg http://packages.devstructure.com/keyring.gpg
sudo apt-get update
sudo apt-get -y install pagerunit</code></pre>

Replace  <code><em>release</em></code> with "`lenny`", "`squeeze`", "`lucid`", "`maverick`", or "`natty`" as your situation requires.

### From PyPI

	pip install pagerunit
