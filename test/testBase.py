import unittest
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
from observed import event


class Foo(object):
    
    def __init__(self, name, buf):
        self.name = name
        self.buf = buf
    
    @event
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))
    
    @event
    def milton(self, caller):
        if hasattr(caller, 'name'):
            name = caller.name
        else:
            name = caller.__name__
        self.buf.append("%smilton%s"%(self.name, name))
    
    def waldo(self, caller):
        if hasattr(caller, 'name'):
            name = caller.name
        else:
            name = caller.__name__
        self.buf.append("%swaldo%s"%(self.name, name))


def makeObservedDict(*objects):
    result = []
    for obj in objects:
        if isinstance(obj, Foo):
            result.append((obj.name+'.bar', getattr(obj, "bar")))
            result.append((obj.name+'.milton', getattr(obj, "milton")))
        else:
            result.append((obj.__name__, obj))
    return dict(result)


def makeObserverDict(*objects):
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
        # setUp and then just delete it here.
        Foo.bar.instances = {}

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.
        
        Also test identification of caller.
        """
        # Items is a tuple of (observed, [observers], expected buf)
        items = [('a.bar',
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
        
        for observedStr, observerStrs, expected in items:
            a = Foo('a', self.buf)
            b = Foo('b', self.buf)
            
            @event
            def f():
                self.buf.append('f')
            
            @event
            def g(caller):
                self.buf.append('g%s'%(caller,))
            
            observedThings = makeObservedDict(a, b, f)
            observerThings = makeObserverDict(a, b, f, g)

            observed = observedThings[observedStr]
            for observerStr, identifyObserved in observerStrs:
                observer = observerThings[observerStr]
                observed.addObserver(observer,
                    identifyObserved=identifyObserved)
            observed()
            del observed, observer, observerThings, observedThings
            self.buf.sort()
            self.assertEqual(expected, self.buf)
            del a, b
            self.assertEqual(len(Foo.bar.instances), 0)
            self.buf = []

    def test_discard(self):
        """
        Disarding observers disables callbacks.
        """
        a = Foo('a', self.buf)
        def f():
            self.buf.append('f')
        
        a.bar.addObserver(f)
        result = a.bar.discardObserver(f)
        self.assertEqual(result, True)
        result = a.bar.discardObserver(f)
        self.assertEqual(result, False)
        a.bar()
        self.assertEqual(self.buf, ['abar'])

    def test_callerIdentification(self):
        """
        The observed object passes itself as first argument if we want.
        """
        a = Foo('a', self.buf)
        
        @event
        def f():
            self.buf.append('f')
        
        def g(caller):
            self.buf.append('g%s'%(caller.__name__,))
        
        f.addObserver(g, identifyObserved=True)
        f.addObserver(a.milton, identifyObserved=True)
        f()
        self.buf.sort()
        self.assertEqual(self.buf, ['amiltonf','f', 'gf'])

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

    def test_cleanup(self):
        """
        As observing objects disappear their entries are removed from observed.
        """
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

    # Everything past here is probably already tested in above tests
    
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
        mn = a.bar.callbacks[id(b)][2]
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
        mn = a.bar.callbacks[id(b)][2]
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertEqual(len(mn), 2)
        self.assertTrue('bar' in mn)
        self.assertTrue('baz' in mn)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','bbar','bbaz'])

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

    def test_functionCallsFunction(self):
        @event
        def func(x):
            self.buf.append('func%s'%(x,))
        
        def bunc(x):
            self.buf.append('bunc%s'%(x,))
        
        func.addObserver(bunc)
        func('q')
        self.assertEqual(self.buf, ['funcq', 'buncq'])

    def test_functionCallsMethod(self):
        @event
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.baz)
        func()
        self.assertEqual(self.buf, ['func', 'abaz'])

    def test_functionCallsObservableMethod(self):
        @event
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.bar)
        func()
        self.assertEqual(self.buf, ['func', 'abar'])

    def test_objectCleanupFromObservableFunction(self):
        @event
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.addObserver(a.bar)
        del a
        func()
        self.assertEqual(self.buf, ['func'])


if __name__ == "__main__":
    unittest.main()
