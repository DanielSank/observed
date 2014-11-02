import unittest
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed import observable_function, observable_method

class Foo(object):
    
    def __init__(self, name, buf):
        self.name = name
        self.buf = buf
    
    @observable_method
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))
    
    @observable_method
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


class TestObserverExecution(unittest.TestCase):

    # Each item is a tuple of
    #   (observed,
    #   [(observer, identify_observed),...],
    #   expected buf)
    ITEMS = [('a.bar',
              [('b.baz', False)],
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

    def setUp(self):
        self.buf = []
    
    def tearDown(self):
        pass    

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.
        
        Also test identification of caller.
        """
        for observedStr, observerStrs, expected in self.ITEMS:
            a = Foo('a', self.buf)
            b = Foo('b', self.buf)
            
            @observable_function
            def f():
                self.buf.append('f')
            
            @observable_function
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
            self.buf.sort()
            self.assertEqual(expected, self.buf)
            self.buf = []

    def test_discard(self):
        """
        discard_observer prevents future ivocation.
        """
        a = Foo('a', self.buf)
        def f():
            self.buf.append('f')
        
        a.bar.add_observer(f)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, True)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, False)
        a.bar()
        self.assertEqual(self.buf, ['abar'])

    def test_unbound_method(self):
        f = Foo('f', self.buf)

        def func():
            self.buf.append('func')

        f.bar.add_observer(func)
        Foo.bar(f)
        self.assertEqual(self.buf, ['fbar', 'func'])

    def test_equality(self):
        f = Foo('f', self.buf)
        g = Foo('g', self.buf)

        @observable_function
        def func():
            self.buf.append('func')

        self.assertEqual(Foo.bar, Foo.bar)
        self.assertEqual(f.bar, f.bar)
        self.assertNotEqual(f.bar, g.bar)
        self.assertEqual(func, func)

    def test_callerIdentification(self):
        """
        The observed object can pass itself as first argument.
        """
        a = Foo('a', self.buf)
        
        @observable_function
        def f():
            self.buf.append('f')
        
        def g(caller):
            self.buf.append('g%s'%(caller.__name__,))
        
        f.add_observer(g, identify_observed=True)
        f.add_observer(a.milton, identify_observed=True)
        f()
        self.buf.sort()
        self.assertEqual(self.buf, ['amiltonf','f', 'gf'])


if __name__ == "__main__":
    unittest.main()
