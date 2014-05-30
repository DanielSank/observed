import unittest
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed.base import ObservableBoundMethodManager, ObservableFunction


class Foo(object):
    
    def __init__(self, name, buf):
        self.name = name
        self.buf = buf
    
    @ObservableBoundMethodManager
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))
    
    @ObservableBoundMethodManager
    def milton(self, caller):
        if hasattr(caller, '__self__'):
            name = caller.__self__.name
        else:
            name = caller.__name__
        self.buf.append("%smilton%s"%(self.name, name))
    
    def waldo(self, caller):
        if hasattr(caller, '__self__'):
            name = caller.__self__.name
        else:
            name = caller.__name__
        self.buf.append("%swaldo%s"%(self.name, name))


def make_observed_dict(*objects):
    result = []
    for obj in objects:
        if isinstance(obj, Foo):
            result.append((obj.name+'.bar', getattr(obj, "bar")))
            result.append((obj.name+'.milton', getattr(obj, "milton")))
        else:
            result.append((obj.__name__, obj))
    return dict(result)


def make_observer_dict(*objects):
    result = []
    for obj in objects:
        if isinstance(obj, Foo):
            result.append((obj.name+'.bar', getattr(obj, "bar")))
            result.append((obj.name+'.baz', getattr(obj, "baz")))
            result.append((obj.name+'.milton', getattr(obj, "milton")))
            result.append((obj.name+'.waldo', getattr(obj, "waldo")))
        else:
            result.append((obj.__name__, obj))
    return dict(result)


class Test(unittest.TestCase):
    def setUp(self):
        self.buf = []
    
    def tearDown(self):
        # Remove all instances in the Foo.bar descriptor's instance dict.
        # This should not be necessary if the cleanup mechanism works
        # properly because all instances should go out of scope when the
        # various tests complete. However, we do this explicitly so that
        # errors are more orthogonal. 
        # Another way to handle this would be to create the Foo class in
        # setUp and then just delete it here. This would be good for non
        # CPython implementations of python where ref counting isn't a thing.
        Foo.bar.instances = {}

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.
        
        Also test identification of caller.
        """
        # Items is a tuple of (observed, [observers], expected buf)
        items = [('a.bar',
                  [('b.baz', False)],  # False is "do not identify observed"
                  ['abar', 'bbaz']),
                 ('a.bar',
                  [('b.bar', False), ('b.baz', False)],
                  ['abar', 'bbar', 'bbaz']),
                 ('a.bar',
                  [('b.bar', False), ('b.baz', False), ('f', False)],
                  ['abar', 'bbar', 'bbaz', 'f']),
                 ('f',
                  [('b.bar', False), ('b.baz', False), ('a.bar', False)],
                  ['abar', 'bbar', 'bbaz', 'f']),
                 ('a.bar',
                  [('b.milton', True), ('b.waldo', True)],
                  ['abar', 'bmiltona', 'bwaldoa']),
                 ('f',
                  [('b.milton', True), ('b.baz', False)],
                  ['bbaz', 'bmiltonf', 'f'])
                ]
        
        for observedStr, observerStrs, expected in items:
            a = Foo('a', self.buf)
            b = Foo('b', self.buf)
            
            @ObservableFunction
            def f():
                self.buf.append('f')
            
            @ObservableFunction
            def g(caller):
                self.buf.append('g%s'%(caller,))
            
            observed_things = make_observed_dict(a, b, f)
            observer_things = make_observer_dict(a, b, f, g)

            observed = observed_things[observedStr]
            for observerStr, identify_observed in observerStrs:
                observer = observer_things[observerStr]
                observed.add_observer(observer,
                    identify_observed=identify_observed)
            observed()
            del observed, observer, observer_things, observed_things
            self.buf.sort()
            self.assertEqual(expected, self.buf)
            del a, b
            self.assertEqual(len(Foo.bar.instances), 0)
            self.buf = []


if __name__ == "__main__":
    unittest.main()
