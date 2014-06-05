import weakref
import functools


class ObserverFunction(object):
    """
    I am a function which observes another function or method.
    """
    def __init__(self, func, observed_obj, weakref_info):
        """
        func is the observer who will be called back.
        observed_obj is the object being observed.
        weakref_info is the information I need in order to clean myself up if
        and when my inst is garbage collected.
        """
        # For some reason, if we put the update_wrapper after we make the
        # weak reference to func, the call to weakref.ref returns a function
        # instead of a weak ref. So, don't move the next line :\
        functools.update_wrapper(self, func)
        self.observed_obj = observed_obj
        key, d = weakref_info
        self.func = weakref.ref(func, CleanupHandler(key, d))
    
    def __call__(self, *arg, **kw):
        """Call me, maybe?"""
        if self.observed_obj:
            return self.func()(self.observed_obj, *arg, **kw)
        else:
            return self.func()(*arg, **kw)


class ObserverBoundMethod(object):
    """
    I am a bound method which observes another function or method.
    """
    def __init__(self, inst, method_name, observed_obj, weakref_info):
        """
        inst is the object to which I am bound.
        method_name is the name of the function I wrap.
        observed_obj is the object I observe.
        weakref_info is the information I need in order to clean myself up when
        my inst is garbage collected.
        """
        self.observed_obj = observed_obj
        key, d = weakref_info
        self.inst = weakref.ref(inst, CleanupHandler(key, d))
        self.method_name = method_name
    
    def __call__(self, *arg, **kw):
        """call me, baby"""
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
        
        If identify_observed is True, then I will be passed as an additional
        first argument to the observer. If I am a bound method you can
        access the object to which I'm bound via .__self__.
        
        If a bound method or function has already been registered to as a
        callback, trying to add it again does nothing. In other words, there is
        no way to sign up an observer to be called back multiple times. This
        was a conscious design choice which users are invited to complain about
        if there are use cases which make this inconvenient.
        
        Returns True if the observer was added, False otherwise.
        """
        if hasattr(observer, "__self__"):  # observer is a bound method
            result = self._add_bound_method(observer, identify_observed)
        else:  # observer is a normal function
            result = self._add_function(observer, identify_observed)
        return result

    def _add_function(self, func, identify_observed):
        """Add a function as an observer."""
        key = self.make_key(func)
        if key not in self.callbacks:
            self.callbacks[key] = ObserverFunction(
                func, self if identify_observed else None,
                (key, self.callbacks))
            return True
        else:
            return False

    def _add_bound_method(self, bound_method, identify_observed):
        """Add an bound method as an observer."""
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
        """Make a suitable key for a function or bound method."""
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
    """
    I am a bound method which fires callbacks when I am called.
    """
    def __init__(self, func, inst, callbacks):
        """
        func is the function I wrap.
        
        inst is the object instance to which I'm bound.
        
        callbacks is a dict shared by the ObservableBoundMethodManager which
        created me. See the documentation for ObservableBoundMethodManager.
        """
        self.func = func
        functools.update_wrapper(self, func)
        self.inst = inst
        self.callbacks = callbacks

    def __call__(self, *arg, **kw):
        """
        Call the function I wrap and all of my callbacks.
        """
        result = self.func(self.inst, *arg, **kw)
        for key in self.callbacks:
            self.callbacks[key](*arg, **kw)
        return result

    @property
    def __self__(self):
        """
        Return the instance to which I'm bound.
        """
        return self.inst


class ObservableBoundMethodManager(object):
    """
    I manage access to ObservableBoundMethods.
    
    I store no strong references to the instances I manage. This guarantees
    that I don't prevent garbage collection of the instances I manage.
    
    When an instance accesses me, I create an ObservableBoundMethod for that
    instance and return it. Observers can be added to that
    ObservableBoundMethod, and they are persisted so that any future invokation
    by that instance fires the callbacks.
    """
    # We persist the callbacks here because if we try to persist them inside
    # the ObservableBoundMethods then we have to persist the
    # ObservableBoundMethods. That would be bad, because then the reference to
    # the inst inside the ObservableBoundMethod would be persisted and would
    # prevent garbage collection of the inst. We can't use a weak ref to fix
    # this because the ObservableBoundMethod _should_ prevent garbage
    # collection of the inst as long as the ObservableBoundMethod is alive. If
    # this doesn't make sense draw a picture of what references what and it
    # will become clear.
    def __init__(self, func):
        """
        Initialize me.
        
        func is the function I will give to the ObservableBoundMethods I
        create.
        """
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
        # Only weak references to instances are stored. This guarantees that
        # the descriptor cannot prevent the instances it manages from being
        # garbage collected.
        # We can't use a WeakKeyDict because not all instances are hashable.
        # Instead we use the instance's id as a key which maps to a tuple of a
        # weak ref to the instance, and the callbacks for that instance. The
        # weak ref has a callback set up to clear the dict entry when the
        # instance is finalized.
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
        return ObservableBoundMethod(self._func, inst, callbacks)

    def __set__(self, inst, val):
        """Disallow setting because we don't guarantee behavior."""
        raise RuntimeError("Assignment not supported")


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


def observable_function(func):
    """
    I turn a function into something that can be observed by other callables.
    
    Use me as a decorator on a function, like this:
    
    @observable_function
    def my_func(x):
        print("my_func called with arg: %s"%(x,))
    
    Now other functions and methods can sign up to get notified when my_func is
    called:
    
    def callback(x):
        print("callback called with arg: %s"%(x,))
    
    class Foo(object):
        def bar(self, x):
            print("Foo object's .bar called with arg: %s"%(x,))
    
    f = Foo()
    my_func.add_observer(callback)
    my_func.add_observer(f.bar)
    my_func('banana')
    
    >>> my_func called with arg: banana
    >>> callback called with arg: banana
    >>> Foo object's .bar called with arg: banana
    
    To decorate methods use observable_method.
    """
    return ObservableFunction(func)


def observable_method(func):
    """
    I turn a method into something that can be observed by other callables.
    
    Use me as a decorator on a method, like this:
    
    class Foo(object):
        __init__(self, name):
            self.name = name
        
        @observable_method
        def bar(self, x):
            print("%s called bar with arg: %s"%(self.name, x))
    
    Now other functions and methods can sign up to get notified when my_func is
    called:
    
    def callback(x):
        print("callback called with arg: %s"%(x,))
    
    a = Foo('a')
    b = Foo('b')
    a.bar.add_observer(callback)
    a.bar.add_observer(b.bar)
    a.bar('banana')
    >>> a called bar with arg: banana
    >>> b called bar with arg: banana
    >>> callback called with arg: banana
    
    To decorate functions use observable_function.
    """
    return ObservableBoundMethodManager(func)
