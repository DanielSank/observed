from observed import event

class Foo(object):
    def __init__(self, name):
        self.name = name
    
    @event
    def bar(self, arg):
        print("Object %s invoked bar with arg='%s'"%(self.name,arg))


def callback(arg):
    print("callback was invoked with arg='%s'"%(arg,))


a = Foo('a')
b = Foo('b')
# Sign up b.bar and callback to "observe" a.bar
a.bar.addObserver(b.bar)
a.bar.addObserver(callback)
# Now when we call a.bar, b.bar and callback will be invoked with the same
# arguments
a.bar('baz')
