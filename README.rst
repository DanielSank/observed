observed allows you to to sign up functions or methods to "observe" other
functions or methods::

    from observed import event

    class Foo(object):
        def __init__(self, name):
            self.name = name
        
        @event
        def bar(self, arg):
            print("Object %s invoked bar with arg='%s'"%(self.name,arg))


    def callback(arg):
        print("callback was invoked with arg='%s'"%(arg,))

    a = Foo('a')
    b = Foo('b')
    # Sign up b.bar and callback to "observe" a.bar
    a.bar.addObserver(b.bar)
    a.bar.addObserver(callback)
    # Now when we call a.bar, b.bar will be invoked with the same arguments
    a.bar('baz')

    >>> Object a invoked bar with arg='baz'
    >>> Object b invoked bar with arg='baz'
    >>> callback was invoked with arg='baz'

This example is included in ./observed/example.py.

You can also ask that the observed object pass itself as the first argument
whenever it calls observers::

    from observed import event

    @event
    def observed_func():
        print("observed_func: I was called")

    def observer_func(observed):
        print("observer_func: %s called me"%(observed.__name__,))

    observed_func.addObserver(observer_func, identifyObserved=True)
    observed_func()

    >>> observed_func: I was called
    >>> observer_func: observed_func called me

Notable features include:

* Being an observer does not keep an object alive. In other words, the
  observer code does not keep any strong references to objects which
  have signed up as observers.
* The @event decorator can be used with unhashable types, and can be
  used on an arbitrary number of methods in each class.
* Tests included :)


Installation
============

pip install observed

or

Unpack the source distribution.
Navigate to the root directory of the unpacked distribution.
At command prompt:
  python setup.py install


News
====

See the file NEWS for the user-visible changes from previous releases.


License
=======

observed is free (as in beer) software.  See the LICENSE file.


Downloading
===========

observed can be obtained from the python package index

https://pypi.python.org/pypi/observed

or via git

https://github.com/DanielSank/observed.git


Documentation
=============

Basic usage is illustrated at the top of this file. Further examples are
given in ./observed/example.py

The source code is documented. Docstrings are required in contributions.


Development
===========

observed development is hosted on github. The current working repository
is given in the Downloading section above.


Bug Reporting
=============

Please submit bug tickets on the github tracking system

https://github.com/DanielSank/observed/issues
