import weakref
import functools


class CallbackManager(object):
    """
    Other objects (callables) can sign up to be notified when I am called.
    """

    def __init__(self):
        self.callbacks = {} #observing object ID -> weak ref, info

    def addObserver(self, observer):
        """
        Register an observer to observe me.

        The observing function or method will be called whenever I am called,
        and with the same arguments and keyword arguments. If a bound method
        or function has already been registered to as a callback, trying to add
        it again does nothing. In other words, there is no way to sign up an
        observer to be called back multiple times. This was a conscious design
        choice which users are invited to complain about if there are use cases
        which make this inconvenient.
        """
        if hasattr(observer, "__self__"):
            self.addBoundMethod(observer)
        else:
            self.addFunction(observer)

    def addBoundMethod(self, boundMethod):
        obj = boundMethod.__self__
        objID = id(obj)
        name = boundMethod.__name__
        if objID in self.callbacks:
            s = self.callbacks[objID][1]
        else:
            wr = weakref.ref(obj, CleanupHandler(objID, self.callbacks))
            s = set()
            self.callbacks[objID] = (wr, s)
        s.add(name)

    def addFunction(self, func):
        objID = id(func)
        if objID not in self.callbacks:
            wr = weakref.ref(func, CleanupHandler(objID, self.callbacks))
            self.callbacks[objID] = (wr, None)

    def discardObserver(self, observer):
        """
        Un-register an observer.
        """
        if hasattr(observer, "__self__"):  # bound method
            objID = id(observer.__self__)
            if objID in self.callbacks:
                s = self.callbacks[objID][1]
                s.discard(observer.__name__)
                if len(s) == 0:
                    del self.callbacks[objID]
        else:  # regular function
            objID = id(obj)
            if id(obj) in self.callbacks:
                del self.callbacks[objID]


class ObservableCallable(CallbackManager):
    """
    A proxy for a callable which can be observed.

    I behave like a function or bound method, but other callables can
    subscribe to be called whenever I am called.
    """

    def __init__(self, func, obj=None):
        self.func = func
        functools.update_wrapper(self, func)
        self.inst = weakref.ref(obj) if obj else None
        CallbackManager.__init__(self)

    def __call__(self, *arg, **kw):
        """
        Invoke the callable which I proxy, and all of it's callbacks.

        The callbacks are called with the same *args and **kw as the main
        callable.
        """
        if self.inst:
            result = self.func(self.inst(), *arg, **kw)
        else:
            result = self.func(*arg, **kw)
        for ID in self.callbacks:
            wr, info = self.callbacks[ID]
            obj = wr()
            if info:
                for methodName in info:
                    getattr(obj, methodName)(*arg, **kw)
            else:
                obj(*arg, **kw)
        return result

    @property
    def __self__(self):
        """
        Get a strong reference to the object owning this ObservableCallable

        This is needed so that ObservableCallable instances can observe other
        ObservableCallable instances.
        """
        if self.inst:
            return self.inst()
        else:
            msg = "'function' object has no attribute '__self__'"
            raise AttributeError(msg)


class ObservableMethodDescriptor(object):

    def __init__(self, func):
        """
        To each instance of the class using this descriptor, I associate an
        ObservableCallable.
        """
        self.instances = {}  # Instance id -> (weak ref, ObservableCallable)
        self._func = func

    # Descriptor protocol for use with methods

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
            wr = weakref.ref(inst, CleanupHandler(ID, self.instances))
            om = ObservableCallable(self._func, inst)
            self.instances[ID] = (wr, om)
        return om

    def __set__(self, inst, val):
        raise RuntimeError("Assigning to ObservableCallable not supported")


def event(func):
    return ObservableMethodDescriptor(func)


class CleanupHandler(object):
    """
    I manage removal of weak references from dicts.

    Use me as a weakref.ref callback to remove an object's id from a dict
    when that object is garbage collected.
    """
    def __init__(self, key, d):
        self.key = key
        self.d = d

    def __call__(self, wr):
        if self.key in self.d:
            del self.d[self.key]
