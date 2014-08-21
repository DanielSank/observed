import weakref
import functools

__version__ = "0.5"


class ObserverFunction(object):
    """
    I wrap a function which is observing another function or method.
    
    I use a weak reference to the observing function so that being an observer
    does not prevent the observing function from being garbage collected.
    """
    def __init__(self, func, identify_observed, weakref_info):
        """
        func is the observing function which will be called when the observed
        is called.
        
        identify_observed = True means that we will pass the observed thing
        as the first argument to func whenever we call func.
        
        weakref_info is the information I need in order to clean myself up if
        and when func is garbage collected.
        """
        # For some reason, if we put the update_wrapper after we make the
        # weak reference to func, the call to weakref.ref returns a function
        # instead of a weak ref. So, don't move the next line :\
        functools.update_wrapper(self, func)
        self.identify_observed = identify_observed
        key, d = weakref_info
        self.func = weakref.ref(func, CleanupHandler(key, d))
    
    def __call__(self, observed_obj, *arg, **kw):
        """Call me, maybe?"""
        if self.identify_observed:
            return self.func()(observed_obj, *arg, **kw)
        else:
            return self.func()(*arg, **kw)


class ObserverBoundMethod(object):
    """
    I am a bound method which observes another function or method.
    """
    def __init__(self, inst, method_name, identify_observed, weakref_info):
        """
        inst is the object to which I am bound.
        
        method_name is the name of the function I wrap.
        
        observed_obj is the object I observe.
        
        weakref_info is the information I need in order to clean myself up when
        my inst is garbage collected.
        """
        self.identify_observed = identify_observed
        key, d = weakref_info
        self.inst = weakref.ref(inst, CleanupHandler(key, d))
        self.method_name = method_name
    
    def __call__(self, observed_obj, *arg, **kw):
        """call me, baby"""
        bound_method = getattr(self.inst(), self.method_name)
        if self.identify_observed:
            return bound_method(observed_obj, *arg, **kw)
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
        # observer is a bound method
        if hasattr(observer, "__self__"):
            result = self._add_bound_method(observer, identify_observed)
        # Assume observer is a normal function. Note that we do not handle
        # class methods or static methods.
        else:
            result = self._add_function(observer, identify_observed)
        return result

    def _add_function(self, func, identify_observed):
        """Add a function as an observer."""
        key = self.make_key(func)
        if key not in self.callbacks:
            self.callbacks[key] = ObserverFunction(
                func, identify_observed, (key, self.callbacks))
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
                inst, method_name, identify_observed, (key, self.callbacks))
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
            key = (id(inst), method_name)
        else:
            key = id(observer)
        return key

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
            self.callbacks[key](self, *arg, **kw)
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
            self.callbacks[key](self, *arg, **kw)
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
        
        If accessed by class I return the the descriptor itself (ie. myself).
        This is useful for testing, but is not compatible with how class based
        method access is supposed to work in python. We need to fix this.
        """
        if inst is None:
            return self
        # Only weak references to instances are stored. This guarantees that
        # the descriptor cannot prevent the instances it manages from being
        # garbage collected.
        # We can't use a WeakKeyDict because not all instances are hashable.
        # Instead we use the instance's id as a key which maps to a tuple of a
        # weak ref to the instance, and the callbacks for that instance. The
        # weak ref has an expiration callback set up to clear the dict entry
        # when the instance is finalized.
        inst_id = id(inst)
        if inst_id in self.instances:
            wr, callbacks = self.instances[inst_id]
            if wr() is None:
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
