import unittest
import sys
import os
import itertools
sys.path.insert(0, os.path.abspath('..'))
import observed
from observed import observable_function, observable_method


def get_caller_name(caller):
    """Find the name of a calling (i.e. observed) object.

    Args:
        caller: The observed object which is calling an observer.

    Returns:
        The name of the caller. If the caller is a function we return that
        function's .__name__. If the caller is a Foo instance we return its
        .name.
    """

    if isinstance(caller, Foo):
        name = caller.name
    else:
        # caller is a function.
        name = caller.__name__
    return name


def clear_list(l):
    """Remove all entries from a list in place.

    Args:
        l: The list to be cleared.
    """

    while True:
        try:
            l.pop(0)
        except IndexError:
            break


class Foo(object):
    """A class with some observable methods and some normal methods.

    Attributes:
        name - string: A string naming the instance.
        buf - list: A buffer for collecting a record of called methods. My
            methods are set up to append a string to buf when they are called.
            The strings are formatted in one of two ways. If the method being
            called accepts the observed object as a first argument, the string
            is:
            "%s%s%s"%(self.name, method_name, caller_name)
            where method_name is the name of the method being called on me and
            caller_name is the name of the calling Foo instance or the name of
            the calling function. Note that the name of the calling instance is
            NOT the same thing as the name of the calling method, which doesn't
            exist. If the method being called does not accept the caller as a
            first argument, the string written to buf is:
            "%s%s"%(self.name, method_name).
    """

    def __init__(self, name, buf):
        """Initialize a Foo object.

        Args:
            name: A name for this instance.
            buf: A buffer (list) into which I write data when my methods are
                called. See the class docstring for details.
        """

        self.name = name
        self.buf = buf
    
    @observable_method
    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    
    def baz(self):
        self.buf.append("%sbaz"%(self.name,))
    
    @observable_method
    def milton(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%smilton%s"%(self.name, caller_name))
    
    def waldo(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%swaldo%s"%(self.name, caller_name))

    def observable_methods(self):
        """Get all of this object's observable methods.

        We don't include milton because our testing procedure isn't smart
        enough to know to call it with an argument.

        Returns:
            A list of the names of my observable methods.
        """

        return [self.bar]

    def method_info(self):
        """Get a list of method names and whether they want caller id.

        Returns:
            A list of tuples. Each tuple is
            (str: method name, bool: identify_observed).
        """

        return [(self.bar, False),
                (self.baz, False),
                (self.milton, True),
                (self.waldo, True)]


class Goo(Foo):
    """Same as Foo but using the descriptor strategy for observer persistence.

    I am entirely similar to Foo except that my observable methods use the
    descriptor persistence strategy. See the docstring for observable_method
    for a detailed explanation.
    """

    def bar(self):
        self.buf.append("%sbar"%(self.name,))
    bar = observable_method(bar, strategy='descriptor')

    def milton(self, caller):
        caller_name = get_caller_name(caller)
        self.buf.append("%smilton%s"%(self.name, caller_name))
    milton = observable_method(milton, strategy='descriptor')


def get_observables(*objs):
    """Get a list observables from some objects.

    Args:
        Any number of objects. Each object must be either a Foo (or subclass)
        instance or a function.

    Returns:
        A list of observable things. Each element is either an
        ObservableFunction or an ObservableBoundMethod. Each function passed in
        as an argument is placed directly into the returned list. For each Foo
        instance passed in, we get each of that instance's observable methods
        and place each one in the output list.        
    """

    observables = []
    for obj in objs:
        if isinstance(obj, Foo):
            observables.extend(obj.observable_methods())
        elif isinstance(obj, observed.ObservableFunction):
            observables.append(obj)
        else:
            raise TypeError("Object of type %s not observable"%(type(obj),))
    return observables


def get_observer_sets(*objs):
    """Get observers from a set of objects.

    Returns:
        A list of tuples. Each tuple is an observer and a boolean corresponding
        to the value of identify_observed which should be used when registering
        that observer.
    """
    observer_sets = []
    single_observers = []
    for obj in objs:
        if isinstance(obj, Foo):
            single_observers.extend(obj.method_info())
        else:
            single_observers.append((obj[0], obj[1]))
    # for num_observers in range(len(single_observers)):
    for comb in itertools.combinations(single_observers, 1):
        observer_sets.append(comb)
    return observer_sets


def get_items(observables, observer_sets):
    """Get all combinations of observer/observed and expected test data.

    Returns:
        A list of tuples. Each tuple contains:
            an observable object
            a list of (observer, identify_observed) tuples
            expected buffer data for this combination
            expected buffer data for calling the obsevable after all observers
            have been un-registered.
    """
    def get_buff_data(observable, observer, identify_observed):
        """Get the buffer data an object will write."""
        if hasattr(observer, '__self__'):  # Observer is a bound method
            expected = observer.__self__.name + observer.__name__
        else:
            expected = observer.__name__
        if identify_observed:
            if hasattr(observable, '__self__'):
                additional = observable.__self__.name
            else:
                additional = observable.__name__
            expected = expected + additional
        return expected

    items = []
    for observable, observer_set in itertools.product(observables, observer_sets):
        # Don't include this combination if it would cause infinite recursion.
        recursion = False
        for observer, _ in observer_set:
            if type(observer) == type(observable) and observer == observable:
                recursion = True
        if recursion:
            continue
        expected_buf = []
        if isinstance(observable, observed.ObservableBoundMethod):
            final = observable.__self__.name + observable.__name__
        elif isinstance(observable, observed.ObservableFunction):
            final = observable.__name__
        for observer, caller_id in observer_set:
            expected_buf.append(get_buff_data(observable, observer, caller_id))
        expected_buf.insert(0, final)
        expected_buf.sort()
        items.append((observable, observer_set, expected_buf, [final]))
    return items


class TestBasics(unittest.TestCase):
    """Test that observers are called when the observed object is called."""

    def setUp(self):
        self.buf = []
    
    def tearDown(self):
        pass    

    def test_callbacks(self):
        """
        Test all combinations of types acting as observed and observer.

        For each combination of observed and observer we check that all
        observers are called. We also check that after discarding the
        observers subsequent invocations of the observed object do not call
        any observers.
        """

        a = Foo('a', self.buf)
        b = Foo('b', self.buf)
        c = Goo('c', self.buf)
        d = Goo('d', self.buf)

        @observable_function
        def f():
            self.buf.append('f')
        
        @observable_function
        def g(caller):
            self.buf.append('g%s'%(get_caller_name(caller),))

        # We don't include g in our set of observables because the testing
        # code isn't smart enough to call it with an argument.
        observables = get_observables(a)#, b, c, d, f)
        observer_sets = get_observer_sets(a)#, b, c, d, (f, False), (g, True))
        items = get_items(observables, observer_sets)

        for observed, observer_set, expected_buf, final_buf in items:
            for observer, identify_observed in observer_set:
                observed.add_observer(observer,
                    identify_observed=identify_observed)
            observed()
            self.buf.sort()
            self.assertEqual(self.buf, expected_buf)
            clear_list(self.buf)
            for observer, _ in observer_set:
                observed.discard_observer(observer)
            observed()
            self.assertEqual(self.buf, final_buf)
            clear_list(self.buf)

    def test_discard(self):
        """Test that discard_observer prevents future ivocation."""

        a = Foo('a', self.buf)
        def f():
            self.buf.append('f')
        
        a.bar.add_observer(f)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, True)
        result = a.bar.discard_observer(f)
        self.assertEqual(result, False)
        a.bar()
        self.assertEqual(self.buf, ['abar'])

    def test_unbound_method(self):
        """Test that calling an unbound method invokes observers."""

        f = Foo('f', self.buf)

        def func():
            self.buf.append('func')

        f.bar.add_observer(func)
        Foo.bar(f)
        self.assertEqual(self.buf, ['fbar', 'func'])

    def test_equality(self):
        """Test equality of observable bound methods."""

        f = Foo('f', self.buf)
        g = Foo('g', self.buf)

        @observable_function
        def func():
            self.buf.append('func')

        self.assertEqual(Foo.bar, Foo.bar)
        self.assertEqual(f.bar, f.bar)
        self.assertNotEqual(f.bar, g.bar)
        self.assertEqual(func, func)

    def test_callerIdentification(self):
        """The observed object can pass itself as first argument."""

        a = Foo('a', self.buf)
        
        @observable_function
        def f():
            self.buf.append('f')
        
        def g(caller):
            self.buf.append('g%s'%(caller.__name__,))
        
        f.add_observer(g, identify_observed=True)
        f.add_observer(a.milton, identify_observed=True)
        f()
        self.buf.sort()
        self.assertEqual(self.buf, ['amiltonf','f', 'gf'])


if __name__ == "__main__":
    unittest.main()
