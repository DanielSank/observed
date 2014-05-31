**observed** allows you to to sign up functions or methods to "observe"
other functions or methods:

.. code:: python

    from observed import observable_function
    
    @observable_function
    def observed_func(arg):
        print("observed_func: %s"%(arg,))
    
    def observer_func(arg):
        print("observer_func: %s"%(arg,))
    
    observed_func.add_observer(observer_func)
    observed_func('banana')
    
    >>> observed_func: banana
    >>> observer_func: banana

You can also register observers for bound methods:

.. code:: python

    from observed import observable_method
    
    class Foo(object):
        def __init__(self, name):
            self.name = name
        
        @observable_method
        def bar(self, arg):
            print("Object %s invoked bar with arg='%s'"%(self.name, arg))

        @observable_method
        def baz(self, arg):
            print("Object %s invoked baz with arg='%s'"%(self.name, arg))
    
    def callback(arg):
        print("callback was invoked with arg='%s'"%(arg,))
    
    a = Foo('a')
    b = Foo('b')
    a.bar.add_observer(b.bar)
    a.bar.add_observer(b.baz)
    a.bar.add_observer(callback)
    a.bar('banana')
    
    >>> Object a invoked bar with arg='banana'
    >>> Object b invoked bar with arg='banana'
    >>> Object b invoked baz with arg='banana'
    >>> callback was invoked with arg='banana'

You can ask that the observed object pass itself as the first argument
whenever it calls observers:

.. code:: python

    from observed import observable_function

    @observable_function
    def observed_func():
        print("observed_func: I was called")

    def observer_func(observed):
        print("observer_func: %s called me"%(observed.__name__,))

    observed_func.add_observer(observer_func, identify_observed=True)
    observed_func()

    >>> observed_func: I was called
    >>> observer_func: observed_func called me

When observed bound methods pass themselves as the observed object, keep in
mind that you can always access the associated instance via .__self__:

.. code:: python

    from observed import observable_method

    class Foo(object):
        def __init__(self, name):
            self.name = name
        
        @observable_method
        def bar(self):
            print("Object %s invoked bar"%(self.name,))

    def callback(observed):
        print("callback was invoked by='%s'"%(observed.__self__.name,))

    a = Foo('a')
    a.bar.add_observer(callback, identify_observed=True)
    a.bar()

    >>> Object a invoked bar
    >>> callback was invoked by a

Notable features include:

* A function or bound method is not kept alive just because it is
  observing something else. This is because the observed object does
  not keep any strong references to the observing objects.
* The @event decorator can be used on methods in classes which are
  unhashable types, and can be used on an arbitrary number of
  methods in each class.
* Tests included :)


Installation
============

**observed** exists on the python package index, so you can do
``pip install observed`` to install it. Alternatively, you can
download the source distribution and in the root directory of the
distribution do

``$ python setup.py install``.


News
====

See the file NEWS for the user-visible changes from previous releases.


License
=======

observed is free (as in beer) software.  See the LICENSE file.


Downloading
===========

observed can be obtained from the python package index

`https://pypi.python.org/pypi/observed <https://pypi.python.org/pypi/observed/>`_

or via git

`https://github.com/DanielSank/observed.git <https://github.com/DanielSank/observed.git/>`_


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

`https://github.com/DanielSank/observed/issues <https://github.com/DanielSank/observed/issues/>`_
