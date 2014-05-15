from observed.observed import event

class Foo(object):
    def __init__(self, name):
        self.name = name
    
    @event
    def bar(self, arg):
        print("Object %s invoked bar with arg='%s'"%(self.name,arg))

def main():
    """
    This function runs through example uses of observed
    """
    a = Foo('a')
    b = Foo('b')
    # Sign up b.bar to "observe" a.bar
    a.bar.addObserver(b.bar)
    # Now when we call a.bar, b.bar will be invoked with the same arguments
    a.bar('baz')

if __name__ == "__main__":
    main()
