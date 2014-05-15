This directory contains the 0.1 release of observed

What does this module do?
-------------------------

observed allows you to to sign up methods to "observe" when other methods
run.

from observed import event

class Foo(object):
    def __init__(self, name):
        self.name = name
    
    @event
    def bar(self, arg):
        print("Object %s invoked bar with arg='%s'"%(self.name,arg))

a = Foo('a')
b = Foo('b')
# Sign up b.bar to "observe" a.bar
a.bar.addObserver(b.bar)
# Now when we call a.bar, b.bar will be invoked with the same arguments
a.bar('baz')

>>> Object a invoked bar with arg='baz'
>>> Object b invoked bar with arg='baz'

This example is included in ./observed.usage.py.

observed has the special feature that an object is not kept alive just by
being an observer.

News
----

See the file NEWS for the user-visible changes from previous releases.


Licese
------

observed is free (as in beer) software.  See the LICENSE file.


Downloading
-----------

observed can be obtained from the python package index

XXX

or via git

https://github.com/DanielSank/observed.git


Documentation
-------------

Basic usage is illustrated at the top of this file. Further examples are
given in ./observed/usage.py


Development
-----------

observed development is hosted on github. The current working repository
is given in the Downloading section above.


Bug Reporting
-------------

Please submit bug tickets on the github tracking system

https://github.com/DanielSank/observed/issues
