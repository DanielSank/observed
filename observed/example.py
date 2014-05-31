from observed import observable_method, observable_function

class Foo(object):
    __init__(self, name):
        self.name = name
    
    @observable_method
    def bar(self, x):
        print("%s called bar with arg: %s"%(self.name, x))
    
    def baz(self, x):
        print("%s called baz with arg: %s"%(self.name, x))

@observable_function
def func(x):
    print("func called with arg: %s"%(x,))

def callback(x):
    print("callback called with arg: %s"%(x,))

a = Foo('a')
b = Foo('b')
a.bar.add_observer(callback)
a.bar.add_observer(func)
a.bar.add_observer(b.bar)
a.bar.add_observer(b.baz)
a.bar('banana')
