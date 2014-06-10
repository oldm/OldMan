.. _installation:

============
Installation
============

Python 2.7 is required, so if in your distribution you have both Python 2.7 and Python 3.x,
please make sure you are using the right version (usually, the command `python` links
to Python 3.x).

Virtualenv
----------

Because OldMan is still a young project, you will have to use development versions of some
external libraries, such as RDFlib.

Thus, we recommend you to isolate the installation of OldMan and its dependencies by using
Virtualenv.

If virtualenv is not already installed on your computer, you can install it with `easy_install` or `pip`::

    $ sudo easy_install-2.7 install virtualenv

or::

    $ sudo pip2 install virtualenv

Now create a directory where to install your virtualenv. For instance::

    $ mkdir -p ~/envs/oldman-2.7
Move in, init  and activae your virtualenv::

    $ cd ~/envs/oldman-2.7
    $ virtualenv2 .
    $ source bin/activate


Install OldMan and its dependencies
-----------------------------------
::

    $ mkdir src
    $ cd src
    $ git clone https://github.com/oldm/OldMan.git oldman
    $ cd oldman

Install first the concrete requirements::

    $ pip install -r requirements.txt

And then install oldman and its abstract (not yet fulfilled) dependencies::

    $ python setup.py install

To test your installation, we encourage you to install the `nose` testing library::

    $ pip install nose

You can run the tests::

    $ nosetests tests/

Hope everything is ok!

Continue to the :ref:`quickstart <quickstart>` example.
