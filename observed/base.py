import weakref
import functools


class ObserverFunction(object):
    """
    
    """
    def __init__(self, func, observed_obj, weakref_info):
        """
        func is the observer who will be called back.
        
        observed_obj is the object being observed.
        """
        self.observed_obj = observed_obj
        key, d = weakref_info
        self.func = weakref.ref(func, CleanupHandler(key, d))
    
    def __call__(self, *arg, **kw):
        if self.observed_obj:
            return self.func()(self.observed_obj, *arg, **kw)
        else:
            return self.func()(*arg, **kw)


class ObserverBoundMethod(object):
    def __init__(self, inst, method_name, observed_obj, weakref_info):
        self.observed_obj = observed_obj
        key, d = weakref_info
        self.inst = weakref.ref(inst, CleanupHandler(key, d))
        self.method_name = method_name
    
    def __call__(self, *arg, **kw):
        bound_method = getattr(self.inst(), self.method_name)
        if self.observed_obj:
            return bound_method(self.observed_obj, *arg, **kw)
        else:
            return bound_method(*arg, **kw)


class ObservableFunction(object):
    """
    A function which can be observed.
    
    I wrap a function and allow other callables to subscribe to be called
    whenever I am called.
    
    Observers (ie. callbacks) are added and removed from me through the
    following two methods:
    
    add_observer(observer)
        registers observer to be called whenever I am called
    
    discard_observer(observer)
        discards observer from the set of callbacks
    """

    def __init__(self, func):
        """Initialize an ObservableFunction"""
        functools.update_wrapper(self, func)
        self.func = func
        self.callbacks = {} #observing object ID -> weak ref, info

    def add_observer(self, observer, identify_observed=False):
        """
        Register an observer to observe me.
        
        The observing function or method will be called whenever I am called,
        and with the same arguments and keyword arguments.
        
        If identify_observed is True, then the observed function will be passed
        as an additional first argument to the observer.
        
        If a bound method or function has already been registered to as a
        callback, trying to add it again does nothing. In other words, there is
        no way to sign up an observer to be called back multiple times. This
        was a conscious design choice which users are invited to complain about
        if there are use cases which make this inconvenient.
        
        Returns True if the observer was odded, False otherwise.
        """
        if hasattr(observer, "__self__"):  # observer is a bound method
            result = self._add_bound_method(observer, identify_observed)
        else:  # observer is a normal function
            result = self._add_function(observer, identify_observed)
        return result

    def _add_function(self, func, identify_observed):
        key = self.make_key(func)
        if key not in self.callbacks:
            self.callbacks[key] = ObserverFunction(
                func, self if identify_observed else None,
                (key, self.callbacks))
            return True
        else:
            return False

    def _add_bound_method(self, bound_method, identify_observed):
        inst = bound_method.__self__
        method_name = bound_method.__name__
        key = self.make_key(bound_method)
        if key not in self.callbacks:
            self.callbacks[key] = ObserverBoundMethod(
                inst, method_name, self if identify_observed else None,
                (key, self.callbacks))
            return True
        else:
            return False

    def discard_observer(self, observer):
        """
        Un-register an observer.
        
        Returns true if an observer was removed, False otherwise.
        """
        discarded = False
        key = self.make_key(observer)
        if key in self.callbacks:
            del self.callbacks[key]
            discarded = True
        return discarded

    @staticmethod
    def make_key(observer):
        if hasattr(observer, "__self__"):
            inst = observer.__self__
            method_name = observer.__name__
            return (id(inst), method_name)
        else:
            return id(observer)

    def __call__(self, *arg, **kw):
        """
        Invoke the callable which I proxy, and all of my observers.

        The observers are called with the same *args and **kw as the main
        callable.
        
        Note:
        I think it is possible for observers to disappear while we execute
        callbacks. It might be better to make strong references to all
        observers before we start callback execution.
        """
        result = self.func(*arg, **kw)
        for key in self.callbacks:
            self.callbacks[key](*arg, **kw)
        return result


class ObservableBoundMethod(ObservableFunction):
    def __init__(self, inst, func, callbacks):
        self.func = func
        functools.update_wrapper(self, func)
        self.inst = inst #Should this be weak? No! Bound methods have strong references to their instances.
        self.callbacks = callbacks
    
    def __call__(self, *arg, **kw):
        result = self.func(self.inst, *arg, **kw)
        for key in self.callbacks:
            self.callbacks[key](*arg, **kw)
        return result
    
    @property
    def __self__(self):
        return self.inst


class ObservableBoundMethodManager(object):
    """
    I manage access to ObservableBoundMethods.
    
    I store no strong references to the instances I manage.
    """
    def __init__(self, func):
        self._func = func
        # instance id -> (inst weak ref, callbacks)
        self.instances = {}

    def __get__(self, inst, cls):
        """
        If accessed by instance I return an ObservableBoundMethod which handles
        that instance.
        
        If accessed by class I return myself; this is not yet compatible with
        how class access of a method is supposed to work.
        """
        if inst is None:
            return self
        # Only weak references to instances are stored. This garuntees that
        # the descriptor cannot prevent the instnaces it manages from being
        # garbage collected.
        # We can't use a WeakKeyDict because not all instances are hashable. We
        # handle this by using the instance's id as a key and setting up an
        # appropriate weakref callback which fires if the instance is
        # finalized.
        inst_id = id(inst)
        if inst_id in self.instances:
            wr, callbacks = self.instances[inst_id]
            if not wr():
                msg = "Unreachable: instance id=%d not cleaned up"%(inst_id,)
                raise RuntimeError(msg)
        else:
            wr = weakref.ref(inst, CleanupHandler(inst_id, self.instances))
            callbacks = {}
            self.instances[inst_id] = (wr, callbacks)
        return ObservableBoundMethod(inst, self._func, callbacks)

    def __set__(self, inst, val):
        """Disallow setting because we don't garuntee behavior."""
        raise RuntimeError("Assignment not supported")


def event(func):
    """
    I turn a callable into something that can be observed by other callables.
    
    Use me as a decorator on a function or method, like this:
    
    @event
    def my_func(x):
        print("my_func called with arg: %s"%(x,))
    
    Now other functions can sign up to get notified when my_func is called:
    
    def callback(x):
        print("callback called with arg: %s"%(x,))
    
    my_func.addObserver(callback)
    my_func('banana')
    >>> my_func called with arg: banana
    >>> callback called with arg: banana
    
    You can decorate methods in the same way, and you can sign up bound methods
    as callbacks.
    """
    return ObservableCallable(func)


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
