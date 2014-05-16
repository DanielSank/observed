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
    
    def test_callback(self):
        """
        
        """
        a = Foo('a')
        b = Foo('b')
        a.bar.addObserver(b.baz)
        self.assertEqual(len(a.bar.callbacks), 1)
        self.assertTrue(id(b) in a.bar.callbacks)
        a.bar()
        self.assertEqual(Foo.buf, ['abar','bbaz'])
    
    def test_callbackObservableMethod(self):
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

if __name__ == "__main__":
    unittest.main()
