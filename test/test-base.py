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
        Foo.bar._manager.instances = {}

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.
        
        Also test identification of caller.
        
        Note: There is a built-in problem with the way some of these tests
        work. I use deletion of objects to exercise the automatic cleanup
        functionality, but this relies on CPython's reference counting in order
        to work right. Not all implementations of python use reference
        counting.
        """
        # Each item is a tuple of
        #   (observed,
        #   [(observer, identify_observed),...],
        #   expected buf)
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
            del observed, observer, observer_things, observed_things
            self.buf.sort()
            self.assertEqual(expected, self.buf)
            # This will only work in CPython. In other implementations we
            # probably have to explicitly run the garbage collector.
            del a, b
            self.assertEqual(len(Foo.bar._manager.instances), 0)
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

    def test_singleObservableMethodInstance(self):
        """
        Invoking a decorated method activates the descriptor.
        
        Also check that decorated methods can be called.
        """
        a = Foo('a', self.buf)
        a.bar()
        self.assertEqual(len(Foo.bar._manager.instances), 1)
        self.assertEqual(Foo.bar._manager.instances.keys(), [id(a)])
        self.assertEqual(len(a.bar.observers), 0)
        self.assertEqual(self.buf, ['abar'])
        del a
        self.assertEqual(len(Foo.bar._manager.instances), 0)

    def test_twoObservableMethodInstances(self):
        """
        Invoking a decorated method activates the descriptor.
        
        If the docrator is accessed from two different instances, they should
        both be added to the descriptor's instance dict.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar()
        b.bar()
        self.assertEqual(len(Foo.bar._manager.instances), 2)
        self.assertEqual(set(Foo.bar._manager.instances.keys()), set([id(a), id(b)]))
        self.assertEqual(len(a.bar.observers), 0)
        self.assertEqual(len(b.bar.observers), 0)
        self.assertEqual(self.buf, ['abar', 'bbar'])
        del a
        self.assertEqual(len(Foo.bar._manager.instances), 1)
        del b
        self.assertEqual(len(Foo.bar._manager.instances), 0)

    def test_cleanup(self):
        """
        As observing objects disappear their entries are removed from observed.
        
        This won't work in non-CPython implementations of python!
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.add_observer(b.baz)
        self.assertEqual(len(a.bar.observers), 1)
        a.bar()
        del b
        self.assertEqual(len(a.bar.observers), 0)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','abar', 'bbaz'])
        self.assertEqual(len(Foo.bar._manager.instances), 1)
        del a
        self.assertEqual(len(Foo.bar._manager.instances), 0)

    # Everything past here is probably already tested in above tests
    
    def test_methodCallsMethod(self):
        """
        Normal methods observe decorated methods.
        
        Adding a normal (no decorator) method as a callback causes that method
        to run when the observed method runs.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.add_observer(b.baz)
        self.assertEqual(len(a.bar.observers), 1)
        self.assertTrue((id(b), 'baz') in a.bar.observers)
        a.bar()
        self.assertEqual(self.buf, ['abar','bbaz'])

    def test_methodCallsObservableMethod(self):
        """
        decorated methods observe other decorated methods.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.add_observer(b.bar)
        cb = a.bar.observers
        self.assertEqual(len(cb), 1)
        self.assertTrue((id(b), 'bar') in cb)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','bbar'])

    def test_methodCallsObservableMethodAndMethod(self):
        """
        decorated and normal methods simultaneously observe decorated methods.
        """
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.add_observer(b.bar)
        a.bar.add_observer(b.baz)
        cb = a.bar.observers
        self.assertEqual(len(cb), 2)
        ids = set(cb.keys())
        self.assertTrue((id(b), 'bar') in ids)
        self.assertTrue((id(b), 'baz') in ids)
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar','bbar','bbaz'])

    def test_methodCallsFunction(self):
        """
        Function observes decorated method.
        """
        def func():
            self.buf.append('func')
        
        a = Foo('a', self.buf)
        a.bar.add_observer(func)
        a.bar()
        self.assertEqual(self.buf, ['abar', 'func'])

    def test_methodCallsMethodAndObservableMethodAndFunction(self):
        """
        Method observed by function, method, and decorated method.
        """
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        a.bar.add_observer(b.baz)
        a.bar.add_observer(b.bar)
        a.bar.add_observer(func)
        self.assertEqual(len(a.bar.observers), 3)
        self.assertEqual(set(a.bar.observers.keys()),
            set([(id(b), 'bar'), (id(b), 'baz'), id(func)]))
        a.bar()
        self.buf.sort()
        self.assertEqual(self.buf, ['abar', 'bbar', 'bbaz', 'func'])

    def test_functionCallsFunction(self):
        """
        Function observes function.
        """
        @observable_function
        def func(x):
            self.buf.append('func%s'%(x,))
        
        def bunc(x):
            self.buf.append('bunc%s'%(x,))
        
        func.add_observer(bunc)
        func('q')
        self.assertEqual(self.buf, ['funcq', 'buncq'])

    def test_functionCallsMethod(self):
        """
        Function observed by method.
        """
        @observable_function
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.add_observer(a.baz)
        func()
        self.assertEqual(self.buf, ['func', 'abaz'])

    def test_functionCallsObservableMethod(self):
        """
        Function observed by decorated method.
        """
        @observable_function
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.add_observer(a.bar)
        func()
        self.assertEqual(self.buf, ['func', 'abar'])

    def test_objectCleanupFromObservableFunction(self):
        """
        Observable function releases observers
        """
        @observable_function
        def func():
            self.buf.append('func')
        a = Foo('a', self.buf)
        func.add_observer(a.bar)
        del a
        func()
        self.assertEqual(self.buf, ['func'])


if __name__ == "__main__":
    unittest.main()
