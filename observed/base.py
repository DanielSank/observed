import weakref
import functools

class ObservableMethod(object):
    """
    A proxy for a bound method which can be observed.

    I behave like a bound method, but other bound methods can subscribe to be
    called whenever I am called.
    """

    def __init__(self, obj, func):
        self.func = func
        functools.update_wrapper(self, func)
        self.objectWeakRef = weakref.ref(obj)
        self.callbacks = {}  #observing object ID -> weak ref, methodNames

    def addObserver(self, boundMethod):
        """
        Register a bound method to observe this ObservableMethod.

        The observing method will be called whenever this ObservableMethod is
        called, and with the same arguments and keyword arguments. If a
        boundMethod has already been registered to as a callback, trying to add
        it again does nothing. In other words, there is no way to sign up an
        observer to be called back multiple times.
        """
        obj = boundMethod.__self__
        ID = id(obj)
        if ID in self.callbacks:
            s = self.callbacks[ID][1]
        else:
            wr = weakref.ref(obj, Cleanup(ID, self.callbacks))
            s = set()
            self.callbacks[ID] = (wr, s)
        s.add(boundMethod.__name__)

    def discardObserver(self, boundMethod):
        """
        Un-register a bound method.
        """
        obj = boundMethod.__self__
        if id(obj) in self.callbacks:
            self.callbacks[id(obj)][1].discard(boundMethod.__name__)

    def __call__(self, *arg, **kw):
        """
        Invoke the method which I proxy, and all of it's callbacks.

        The callbacks are called with the same *args and **kw as the main
        method.
        """
        result = self.func(self.objectWeakRef(), *arg, **kw)
        for ID in self.callbacks:
            wr, methodNames = self.callbacks[ID]
            obj = wr()
            for methodName in methodNames:
                getattr(obj, methodName)(*arg, **kw)
        return result

    @property
    def __self__(self):
        """
        Get a strong reference to the object owning this ObservableMethod

        This is needed so that ObservableMethod instances can observe other
        ObservableMethod instances.
        """
        return self.objectWeakRef()


class ObservableMethodDescriptor(object):

    def __init__(self, func):
        """
        To each instance of the class using this descriptor, I associate an
        ObservableMethod.
        """
        self.instances = {}  # Instance id -> (weak ref, Observablemethod)
        self._func = func

    def __get__(self, inst, cls):
        if inst is None:
            return self
        ID = id(inst)
        if ID in self.instances:
            wr, om = self.instances[ID]
            if not wr():
                msg = "Object id %d should have been cleaned up"%(ID,)
                raise RuntimeError(msg)
        else:
            wr = weakref.ref(inst, Cleanup(ID, self.instances))
            om = ObservableMethod(inst, self._func)
            self.instances[ID] = (wr, om)
        return om

    def __set__(self, inst, val):
        raise RuntimeError("Assigning to ObservableMethod not supported")


def event(func):
    return ObservableMethodDescriptor(func)


class Cleanup(object):
    """
    I manage remove elements from a dict whenever I'm called.

    Use me as a weakref.ref callback to remove an object's id from a dict
    when that object is garbage collected.
    """
    def __init__(self, key, d):
        self.key = key
        self.d = d

    def __call__(self, wr):
        del self.d[self.key]
