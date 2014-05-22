import unittest
from observed import event


class Foo(object):
    
    buf = []
    
    def __init__(self, name):
        self.name = name
    
    @event
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))


class Test(unittest.TestCase):
    def setUp(self):
        Foo.buf = []
    
    def tearDown(self):
        # Remove all instances in the Foo.bar descriptor's instance dict.
        # This should not be necessary if the cleanup mechanism works
        # properly because all instances should go out of scope when the
        # various tests complete. However, we do this explicitly so that
        # errors are more orthogonal.
        # Another way to handle this would be to create the Foo class in
        # setUp and then just delete it here.
        Foo.bar.instances = {}
    
    def test_singleInstance(self):
        """
        Invoking a method decorated by @event activates the descriptor.
        
        Also check that decorated methods can be called.
        """
        a = Foo('a')
        a.bar()
        self.assertEqual(len(Foo.bar.instances), 1)
        self.assertEqual(Foo.bar.instances.keys(), [id(a)])
        self.assertEqual(len(a.bar.callbacks), 0)
        self.assertEqual(Foo.buf, ['abar'])
    
    def test_twoInstances(self):
        """
        Invoking a method decorated by @event activates the descriptor.
        
        If an @event is called from two different instances, they should both
        be added to the descriptor's instance dict.
        """
        a = Foo('a')
        b = Foo('b')
        a.bar()
        b.bar()
        self.assertEqual(len(Foo.bar.instances), 2)
        self.assertEqual(set(Foo.bar.instances.keys()), set([id(a), id(b)]))
        self.assertEqual(len(a.bar.callbacks), 0)
        self.assertEqual(len(b.bar.callbacks), 0)
        self.assertEqual(Foo.buf, ['abar', 'bbar'])
    
    def test_methodCallback(self):
        """
        Normal methods observe @event methods.
        
        Adding a normal (no @event) method as a callback causes that
        method to run when the observed method runs.
        """
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.baz)
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertTrue(id(b) in a.bar.callbacks)
        a.bar()
        self.assertEqual(Foo.buf, ['abar','bbaz'])
    
    def test_eventCallback(self):
        """
        @event methods observe other @event methods.
        """
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.bar)
        mn = a.bar.callbacks[id(b)][1]
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertEqual(len(mn), 1)
        self.assertTrue('bar' in mn)
        a.bar()
        Foo.buf.sort()
        self.assertEqual(Foo.buf, ['abar','bbar'])
    
    def test_methodAndEventCallback(self):
        """
        @event and normal methods simultaneously observe @event methods.
        """
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.bar)
        a.bar.addObserver(b.baz)
        mn = a.bar.callbacks[id(b)][1]
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertEqual(len(mn), 2)
        self.assertTrue('bar' in mn)
        self.assertTrue('baz' in mn)
        a.bar()
        Foo.buf.sort()
        self.assertEqual(Foo.buf, ['abar','bbar','bbaz'])
    
    def test_cleanup(self):
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.baz)
        self.assertEqual(len(a.bar.callbacks), 1)
        del b
        self.assertEqual(len(a.bar.callbacks), 0)
        a.bar()
        self.assertEqual(Foo.buf, ['abar'])
        self.assertEqual(len(Foo.bar.instances), 1)
        del a
        self.assertEqual(len(Foo.bar.instances), 0)
    
    def test_functionCallback(self):
        def func():
            Foo.buf.append('func')
        
        a = Foo('a')
        a.bar.addObserver(func)
        a.bar()
        self.assertEqual(Foo.buf, ['abar', 'func'])

    def test_methodAndEventAndFunctionCallback(self):
        def func():
            Foo.buf.append('func')
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.baz)
        a.bar.addObserver(b.bar)
        a.bar.addObserver(func)
        self.assertEqual(len(a.bar.callbacks), 2) # b and func
        self.assertEqual(set(a.bar.callbacks.keys()), set([id(b), id(func)]))
        a.bar()
        Foo.buf.sort()
        self.assertEqual(Foo.buf, ['abar', 'bbar', 'bbaz', 'func'])

if __name__ == "__main__":
    unittest.main()
