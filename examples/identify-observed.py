"""
This module demonstrates identification of the observed object. In order to run
it, just type
$ python identify-caller.py
from the directory containing this file. The example will use the observed
module in the source distribution. Even if you have installed observed, this
example will not use the installed code.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed import observable_function, observable_method

@observable_function
def f(x):
    print("f called with arg: %s"%(x,))

def g(observed, x):
    print("g called by %s with arg: %s"%(observed, x))

f.add_observer(g, identify_observed=True)
f('banana')
