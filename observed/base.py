import weakref
import functools


class ObservableCallable(object):
    """
    A callable (function or bound method) which can be observed.
    
    I wrap a function or bound method, and allow other callables to subscribe
    to be called whenever I am called.
    
    Observers (ie. callbacks) are added and removed from me through the
    following two methods:
    
    add_observer(observer)
        registers observer to be called whenever I am called
    
    discard_observer(observer)
        discards observer from the set of callbacks
    
    Note that I implement __get__ and __set__. This makes me a descriptor. I
    use this so that I can wrap methods. However, I have only been tested to
    work with bound methods, and functionality with @classmethods or
    @staticmethods is not attempted.
    """

    def __init__(self, func, obj=None):
        self.func = func
        # Update various attributes to look like func.
        # This is actually probably not what we want when we're acting as a
        # descriptor. Not sure how to fix this.
        functools.update_wrapper(self, func)
        self.inst = weakref.ref(obj) if obj else None
        self.callbacks = {} #observing object ID -> weak ref, info
        # When acting as a descriptor, we need a dict of instances
        self.instances = {} # instance id -> (inst weak ref, ObservableCallable)

    # Callback management

    def add_observer(self, observer, identify_observed=False):
        """
        Register an observer to observe me.

        The observing function or method will be called whenever I am called,
        and with the same arguments and keyword arguments.
        
        if identify_observed is True, then the observed object will pass itself
        as an additional first argument to the callback.
        
        If a bound method or function has already been registered to as a
        callback, trying to add it again does nothing. In other words, there is
        no way to sign up an observer to be called back multiple times. This
        was a conscious design choice which users are invited to complain about
        if there are use cases which make this inconvenient.
        """
        if hasattr(observer, "__self__"):
            self._add_bound_method(observer, identify_observed)
        else:
            self._add_function(observer, identify_observed)

    def _add_bound_method(self, bound_method, _identify_observed):
        observer_inst = bound_method.__self__
        method_name = bound_method.__name__
        objID = id(observer_inst)
        if objID in self.callbacks:
            s = self.callbacks[objID][2]
        else:
            wr = weakref.ref(observer_inst,
                             CleanupHandler(objID, self.callbacks))
            s = {} # method name -> information
            self.callbacks[objID] = (wr, 'bound_method', s)
        s[method_name] = (_identify_observed,)

    def _add_function(self, func, _identify_observed):
        objID = id(func)
        if objID not in self.callbacks:
            wr = weakref.ref(func, CleanupHandler(objID, self.callbacks))
            self.callbacks[objID] = (wr, 'function', (_identify_observed,))

    def discard_observer(self, observer):
        """
        Un-register an observer.
        
        Returns true if an observer was removed, False otherwise.
        """
        discarded = False
        if hasattr(observer, "__self__"):  # bound method
            objID = id(observer.__self__)
            if objID in self.callbacks:
                discarded = True
                s = self.callbacks[objID][2]
                del s[observer.__name__]
                if len(s) == 0:
                    del self.callbacks[objID]
        else:  # regular function
            objID = id(observer)
            if objID in self.callbacks:
                discarded = True
                del self.callbacks[objID]
        return discarded

    def __call__(self, *arg, **kw):
        """
        Invoke the callable which I proxy, and all of it's callbacks.

        The callbacks are called with the same *args and **kw as the main
        callable.
        
        Note:
        I think it is possible for observers to disappear while we execute
        callbacks. It might be better to make strong references to all
        observers before we start callback execution.
        """
        caller = self.inst() if self.inst else self
        # Call main function or method (ie. the one we wrap)
        if self.inst:
            result = self.func(self.inst(), *arg, **kw)
        else:
            result = self.func(*arg, **kw)
        # Call callbacks
        for ID in self.callbacks:
            wr, callback_type, info = self.callbacks[ID]
            observer = wr()
            if callback_type == 'function':
                _identify_observed, = info
                callback = observer
                if _identify_observed:
                    callback(caller, *arg, **kw)
                else:
                    callback(*arg, **kw)
            elif callback_type == 'bound_method':
                for methodName in info:
                    _identify_observed, = info[methodName]
                    callback = getattr(observer, methodName)
                    if _identify_observed:
                        callback(caller, *arg, **kw)
                    else:
                        callback(*arg, **kw)
            else:
                msg = "Callback type %s not recognized"%(callback_type,)
                raise RuntimeError(msg)
        return result

    # Partial implementation of bound method behavior.
    # Only for cases where we _are_ a bound method!

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

    # Descriptor interface

    def __get__(self, inst, cls):
        """
        Handle access as descriptor.
        
        If accessed by class I return myself.
        
        If accessed by instance I return an ObservableCallable which handles
        that instance.
        """
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
            om = ObservableCallable(self.func, inst)
            self.instances[ID] = (wr, om)
        return om

    def __set__(self, inst, val):
        raise RuntimeError("Assigning to ObservableCallable not supported")


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
