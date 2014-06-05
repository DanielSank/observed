"""
This module demonstrates basic use of observed. In order to run it, just type
$ python example.py
from the directory containing this file. The example will use the observed
module in the source distribution. Even if you have installed observed, this
example will not use the installed code.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed import observable_function, observable_method

class Foo(object):
    def __init__(self, name):
        self.name = name

    @observable_method
    def bar(self, x):
        print("%s called bar with arg: %s"%(self.name, x))

    def baz(self, x):
        print("%s called baz with arg: %s"%(self.name, x))

@observable_function
def f(x):
    print("f called with arg: %s"%(x,))

def g(x):
    print("g called with arg: %s"%(x,))

# We make two instances of Foo,
a = Foo('a')
b = Foo('b')
# add a bunch of observers to a.bar,
a.bar.add_observer(g)
a.bar.add_observer(f)
a.bar.add_observer(b.bar)
a.bar.add_observer(b.baz)
# and then call a.bar(). Take a look at the console output when this function
# runs. You'll see a print statement for a.bar and for each of the observers.
print("Calling a.bar()...")
a.bar('banana')
