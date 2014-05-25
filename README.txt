observed allows you to to sign up functions or methods to "observe" other
functions or methods:

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

This functionality is useful when connecting back-end logic to a GUI. By
using the @event decorator, the back-end class doesn't have to know
anything about the GUI objects which are observing it. This kind of loose
coupling makes your program much easier to organize and maintain.

Notable features include:

1. Being an observer does not keep an object alive. In other words, the
   observer code does not keep any strong references to objects which
   have signed up as observers.
2. The @event decorator can be used with unhashable types, and can be
   used on an arbitrary number of methods in each class.
3. Tests included :)


Installation
------------

1. Unpack the source distribution.
2. Navigate to the root directory of the unpacked distribution.
3. At command prompt:
      python setup.py install


News
----

See the file NEWS for the user-visible changes from previous releases.


License
------

observed is free (as in beer) software.  See the LICENSE file.


Downloading
-----------

observed can be obtained from the python package index

https://pypi.python.org/pypi/observed (Not quite yet)

or via git

https://github.com/DanielSank/observed.git


Documentation
-------------

Basic usage is illustrated at the top of this file. Further examples are
given in ./observed/example.py

The source code is documented. Docstrings are required in contributions.


Development
-----------

observed development is hosted on github. The current working repository
is given in the Downloading section above.


Bug Reporting
-------------

Please submit bug tickets on the github tracking system

https://github.com/DanielSank/observed/issues
