import unittest
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed import event
from observed.base import ObservableCallable


class Foo(object):
    
    def __init__(self, name, buf):
        self.name = name
        self.buf = buf
    
    @event
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))


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
        # setUp and then just delete it here.
        Foo.bar.instances = {}
    
    # Observed object is a bound method
    
    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.
        """
        # Items is a tuple of (observed, [observers], expected buf)
        items = [('a.bar',
                    ['b.baz'],
                    ['abar', 'bbaz']),
                 ('a.bar',
                    ['b.bar', 'b.baz'],
                    ['abar', 'bbar', 'bbaz']),
                 ('a.bar',
                    ['b.bar', 'b.baz', 'f'],
                    ['abar', 'bbar', 'bbaz', 'f']),
                 ('f',
                    ['b.bar', 'b.baz', 'a.bar'],
                    ['abar', 'bbar', 'bbaz', 'f'])
                ]
        
        for observedStr, observerStrs, expected in items:
            a = Foo('a', self.buf)
            b = Foo('b', self.buf)
            
            @ObservableCallable
            def f():
                self.buf.append('f')
            
            observed = {'a.bar':a.bar, 'b.bar':b.bar, 'f':f}[observedStr]
            for observerStr in observerStrs:
                observer = {'a.bar':a.bar, 'b.bar':b.bar,
                            'b.baz':b.baz, 'f':f}[observerStr]
                observed.addObserver(observer)
            observed()
            del observed, observer
            self.buf.sort()
            self.assertEqual(expected, self.buf)
            del a, b
            self.assertEqual(len(Foo.bar.instances), 0)
            self.buf = []
    
    def test_singleObservableMethodInstance(self):
        """
        Invoking a method decorated by @event activates the descriptor.
        
        Also check that decorated methods can be called.
        """
        a = Foo('a', self.buf)
        a.bar()
        self.assertEqual(len(Foo.bar.instances), 1)
        self.assertEqual(Foo.bar.instances.keys(), [id(a)])
        self.assertEqual(len(a.bar.callbacks), 0)
        self.assertEqual(self.buf, ['abar'])
        del a
        self.assertEqual(len(Foo.bar.instances), 0)
    
    def test_twoObservableMethodInstances(self):
        """
        Invoking a method decorated by @event activates the descriptor.
        
        If an @event is called from two different instances, they should both
        be added to the descriptor's instance dict.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar()
        b.bar()
        self.assertEqual(len(Foo.bar.instances), 2)
        self.assertEqual(set(Foo.bar.instances.keys()), set([id(a), id(b)]))
        self.assertEqual(len(a.bar.callbacks), 0)
        self.assertEqual(len(b.bar.callbacks), 0)
        self.assertEqual(self.buf, ['abar', 'bbar'])
        del a
        self.assertEqual(len(Foo.bar.instances), 1)
        del b
        self.assertEqual(len(Foo.bar.instances), 0)

    def test_methodCallsMethod(self):
        """
        Normal methods observe @event methods.
        
        Adding a normal (no @event) method as a callback causes that
        method to run when the observed method runs.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.addObserver(b.baz)
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertTrue(id(b) in a.bar.callbacks)
        a.bar()
        self.assertEqual(self.buf, ['abar','bbaz'])
    
    def test_methodCallsObservableMethod(self):
        """
        @event methods observe other @event methods.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.addObserver(b.bar)
        mn = a.bar.callbacks[id(b)][1]
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertEqual(len(mn), 1)
        self.assertTrue('bar' in mn)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','bbar'])
    
    def test_methodCallsObservableMethodAndMethod(self):
        """
        @event and normal methods simultaneously observe @event methods.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.addObserver(b.bar)
        a.bar.addObserver(b.baz)
        mn = a.bar.callbacks[id(b)][1]
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertEqual(len(mn), 2)
        self.assertTrue('bar' in mn)
        self.assertTrue('baz' in mn)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','bbar','bbaz'])
    
    def test_cleanup(self):
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.addObserver(b.baz)
        self.assertEqual(len(a.bar.callbacks), 1)
        a.bar()
        del b
        self.assertEqual(len(a.bar.callbacks), 0)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','abar', 'bbaz'])
        self.assertEqual(len(Foo.bar.instances), 1)
        del a
        self.assertEqual(len(Foo.bar.instances), 0)
    
    def test_methodCallsFunction(self):
        def func():
            self.buf.append('func')
        
        a = Foo('a', self.buf)
        a.bar.addObserver(func)
        a.bar()
        self.assertEqual(self.buf, ['abar', 'func'])

    def test_methodCallsMethodAndObservableMethodAndFunction(self):
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.addObserver(b.baz)
        a.bar.addObserver(b.bar)
        a.bar.addObserver(func)
        self.assertEqual(len(a.bar.callbacks), 2) # b and func
        self.assertEqual(set(a.bar.callbacks.keys()), set([id(b), id(func)]))
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar', 'bbar', 'bbaz', 'func'])

    # Observed object is a function
    
    def test_functionCallsFunction(self):
        @ObservableCallable
        def func(x):
            self.buf.append('func%s'%(x,))
        
        def bunc(x):
            self.buf.append('bunc%s'%(x,))
        
        func.addObserver(bunc)
        func('q')
        self.assertEqual(self.buf, ['funcq', 'buncq'])

    def test_functionCallsMethod(self):
        @ObservableCallable
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.baz)
        func()
        self.assertEqual(self.buf, ['func', 'abaz'])

    def test_functionCallsObservableMethod(self):
        @ObservableCallable
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.bar)
        func()
        self.assertEqual(self.buf, ['func', 'abar'])

    def test_objectCleanupFromObservableFunction(self):
        @ObservableCallable
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.bar)
        del a
        func()
        self.assertEqual(self.buf, ['func'])


if __name__ == "__main__":
    unittest.main()
