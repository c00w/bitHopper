import sys
from thread import get_ident
from peak.util.decorators import rewrap, cache_source, classy, decorate

__all__ = [
    'Service', 'replaces', 'setting', 'InputConflict', 'DynamicRuleError',
    'State', 'Action', 'resource', 'registry', 'new', 'empty',
    'lookup', 'manager', 'reraise', 'with_', 'call_with', 'ScopeError',
    'resource_registry',
]

_in_place = """__iadd__ __isub__ __imul__ __idiv__ __itruediv__ __ifloordiv__
__imod__ __ipow__ __ilshift__ __irshift__ __iand__ __ixor__ __ior__""".split()

_ignore = dict.fromkeys("""
    __name__ __module__ __return__ __slots__ get __init__ __metaclass__ __doc__
    __call__ __new__""".split() + _in_place
).__contains__

def _no_in_place(self, *args):
    raise TypeError(
        "In-place operators (other than <<=) cannot be performed on a"
        " service class"
    )

def _ilshift(cls, factory):
    State[cls] = factory
    return cls

def _mod(cls, expr):
    return 'lambda: '+expr

_std_attrs = dict(
    [(k,_no_in_place) for k in _in_place], __ilshift__=_ilshift, __mod__=_mod
)






def redirect_attribute(cls, name, payload):
    setattr(type(cls), name, property(
        lambda s: getattr(s.get(), name),
        lambda s,v: setattr(s.get(), name, v),
        lambda s: delattr(s.get(), name),
    ))


class _ClassDelegate(classy):
    """Type whose attributes/methods are delegated to ``cls.get()``"""

    __slots__ = ()

    get = None  # dummy

    decorate(classmethod)
    def __class_init__(cls, name, bases, cdict, supr):
        meta = type(cls)
        if getattr(meta, '__for_class__', None) is not cls:
            cls.__class__ = meta = type(meta)(
                cls.__name__+'Class', (meta,),
                dict(_std_attrs, __module__=cls.__module__, __for_class__=cls)
            )
            # XXX activate_attrs(meta)?

        supr()(cls, name, bases, cdict, supr)

        if 'get' not in cdict:
            cls.get = staticmethod(classmethod(lookup).__get__(None, cls))

        for k, v in cdict.items():
            if not isinstance(k, basestring):
                continue
            if not isinstance(v, (classmethod,staticmethod))and not _ignore(k):
                redirect_attribute(cls, k, v)






class State(_ClassDelegate):
    """A thread's current configuration and state"""

    def __new__(cls, *rules, **attrs):
        return attrs and object.__new__(cls) or empty()

    def __init__(self, **attrs):
        """Create an empty state with `rules` in effect"""
        self.__dict__.update(attrs)

    def __getitem__(self, key):
        """Get the rule for `key`"""
        return self.getRule(key)

    def __setitem__(self, key, rule):
        """Set the rule for `key`"""
        return self.setRule(key, rule)

    def swap(self):
        """Make this state current and return the old one"""
        raise NotImplementedError("Can't switch to the root state")

    def child(self, *rules):
        """Return a new child state of this one, with `rules` in effect"""
        raise NotImplementedError   # this method is replaced on each instance

    def __enter__(self):
        """Make this state a single-use nested state"""
        raise NotImplementedError("Can't enter the root state")

    def __exit__(self, typ, val, tb):
        """Close this state and invoke exit callbacks"""
        raise NotImplementedError("Can't exit the root state")

    def on_exit(self, callback):
        """Add a `callback(typ,val,tb)` to be invoked at ``__exit__`` time"""
        raise NotImplementedError   # this method is replaced on each instance




    decorate(staticmethod)
    def get(key=None):
        """Return the current state (no args) or a current rule (w/key)"""
        # this method is replaced later below
        raise NotImplementedError

    parent = None


class InputConflict(Exception):
    """Attempt to set a rule that causes a visible conflict in the state"""

class DynamicRuleError(Exception):
    """A fallback or wildcard rule attempted to access dynamic state"""

class ScopeError(Exception):
    """A problem with scoping occurred"""


_exc_info = {}
nones = None, None, None

def _swap_exc_info(data):
    this_thread = get_ident()
    old = _exc_info.get(this_thread, nones)
    _exc_info[this_thread] = data
    return old


def new():
    """Return a new child of the current state"""
    return State.child()









def _let_there_be_state():
    """Create a world of states, manipulable only by exported functions"""

    states = {}

    def _swap(what):
        this_thread = get_ident()
        old = states.setdefault(this_thread, what)
        states[this_thread] = what
        return old

    def lookup(key):
        """Return the value of `key` in the current state"""
        try:
            state, getRule, lookup, child = states[get_ident()]
        except KeyError:
            empty().swap()
            state, getRule, lookup, child = states[get_ident()]
        return lookup(key)

    def get(key=None):
        try:
            state, getRule, lookup, child = states[get_ident()]
        except KeyError:
            empty().swap()
            state, getRule, lookup, child = states[get_ident()]
        if key is None:
            return state
        return getRule(key)

    def disallow(key):
        raise DynamicRuleError(
            "default rule or exit function tried to read dynamic state", key
        )

    def empty():
        """Return a new, empty State instance"""
        state = new_state(root_getrule)
        state.parent = root
        return state

    def new_state(inherit=None, inheritedDistances=None, propagate=None):

        buffer = {}
        rules = {}
        values = {}
        distances = {}
        computing = {}

        get_stack, set_stack = computing.get, computing.setdefault

        def getRule(key):
            """Get my rule for `key`"""
            try:
                rule = rules[key]
            except KeyError:
                try:
                    rule = buffer[key]
                except KeyError:
                    rule = buffer.setdefault(key, __fallback(key))

                # snapshot the currently-set value - this is thread-safe
                # because setdefault is atomic, so rules[key] will only *ever*
                # have one value, even if it's not the one now in the buffer
                #
                rule = rules.setdefault(key, rule)
                if key not in distances:
                    if inheritedDistances is not None and inherit(key)==rule:
                        distances.setdefault(key, inheritedDistances[key]+1)
                    else:
                        distances.setdefault(key, 0)

            if computing:
                # Ensure that any value being computed in this thread has a
                # maximum propagation distance no greater than this rule's
                # distance.
                stack = get_stack(get_ident())
                if stack:
                    stack[-1] = min(stack[-1], distances[key])

            return rule

        def setRule(key, rule):
            """Set my rule for `key`, or raise an error if inconsistent"""
            buffer[key] = rule
            # as long as a snapshot hasn't been taken yet, `old` will be `rule`
            old = rules.get(key, rule)
            if old is not rule and old != rule:
                raise InputConflict(key, old, rule)

        def getValue(key):
            """Get the dynamic value of `key`"""
            try:
                value = values[key]

            except KeyError:
                this_thread = get_ident()
                rule = getRule(key)     # this ensures distances[key] is known

                stack = set_stack(this_thread, [])
                stack.append(distances[key])

                try:
                    value = key.__apply__(key, rule)
                finally:
                    distance = stack.pop()
                    if not stack:
                        del computing[this_thread]
                    else:
                        stack[-1] = min(stack[-1], distance)

                value = publish(distance, key, value)

            else:
                if computing:
                    stack = get_stack(get_ident())
                    if stack:
                        stack[-1] = min(stack[-1], distances[key])

            return value



        def publish(distance, key, value):
            """Accept value from this state or child, and maybe propagate it"""

            # It's safe to update distances here because no thread can depend
            # on the changed distance for propagation unless *some* thread has
            # already finished the relevant computation -- i.e., done this very
            # update.  Otherwise, there would be no values[key], therefore the
            # thread would have to follow the same code path, ending up by
            # being the thread doing this update!  Ergo, this is a safe update.
            #
            distances[key] = distance

            if distance and propagate:
                # pass it up to the parent, but use the value the parent has.
                # therefore, the parent at "distance" height from us will be
                # the arbiter of the value for all its children, ensuring that
                # exactly one value is used for the entire subtree!
                #
                value = propagate(distance-1, key, value)

            # Return whatever value wins at this level to our children
            return values.setdefault(key, value)


        def child():
            """Return a new child state"""
            s = new_state(getRule, distances, publish)
            s.parent = this
            return s


        def __fallback(key):
            """Compute the fallback for key"""
            old = _swap(disabled)
            try:
                return key.__fallback__(inherit, key)
            finally:
                _swap(old)



        def swap():
            if exited:
                raise ScopeError("Can't switch to an exited state")
            state, get, lookup, old_child = old = _swap(enabled)
            if lookup is disallow:
                _swap(old)
                raise DynamicRuleError(
                    "default rule or exit function tried to change states"   # XXX
                )
            return state

        def __enter__():
            if my_parent or exited:
                raise ScopeError("Can't re-enter a previously-entered state")
            elif active_child:
                raise ScopeError("State already has an active child")
            elif get() is this:
                raise ScopeError("State is already current")
            parent, xx, xx, parents_child = old = states[get_ident()]
            if parents_child:
                raise ScopeError("Current state already has an active child")
            swap()
            my_parent.append(old); parents_child.append(this)
            return this

        def __exit__(typ, val, tb):
            if exited:
                raise ScopeError("State already exited")
            elif not my_parent:
                raise ScopeError("State hasn't been entered yet")
            elif active_child:
                raise ScopeError("Nested state(s) haven't exited yet")
            elif get() is not this:
                raise ScopeError("Can't exit a non-current state")
            parents_child = my_parent[0][-1]
            _swap(my_parent.pop()) # reactivate parent state
            parents_child.pop()
            exited.append(1)
            values.clear()
            return call_exitfuncs(typ, val, tb)

        active_child = []
        my_parent = []
        exited = []
        exit_functions = []

        def call_exitfuncs(typ, val, tb):
            old = _swap(disabled)
            try:
                for func in exit_functions:
                    try:
                        func(typ, val, tb)
                    except:
                        typ, val, tb = sys.exc_info()
            finally:
                _swap(old)
                del typ, val, tb

        def on_exit(callback):
            if exited:
                raise ScopeError("State already exited")
            elif not my_parent:
                raise ScopeError("State hasn't been entered yet")
            if callback not in exit_functions:
                exit_functions.append(callback)

        this = State(
            getRule=getRule, setRule=setRule, swap=swap, child=child,
            __enter__=__enter__, __exit__=__exit__, on_exit = on_exit
        )
        enabled  = this, getRule, getValue, active_child
        disabled = None, getRule, disallow, active_child
        return this

    State.get = staticmethod(get)
    State.root = root = new_state(); root.child = empty
    root_getrule = root.getRule
    del root.swap, root.__enter__, root.__exit__
    return lookup, empty

lookup, empty = _let_there_be_state(); del _let_there_be_state

class _GeneratorContextManager(object):
    """Helper for @context.manager decorator."""

    def __init__(self, gen):
        self.gen = gen

    def __enter__(self):
        for value in self.gen:
            return value
        else:
            raise RuntimeError("generator didn't yield")

    def __exit__(self, typ, value, traceback):
        if typ is None:
            for value in self.gen:
                raise RuntimeError("generator didn't stop")
        else:
            try:
                old = _swap_exc_info((typ, value,traceback))
                try:
                    self.gen.next()
                finally:
                    _swap_exc_info(old)

                raise RuntimeError("generator didn't stop after throw()")

            except StopIteration, exc:
                # Suppress the exception *unless* it's the same exception that
                # was passed to throw().  This prevents a StopIteration
                # raised inside the "with" statement from being suppressed
                return exc is not value
            except:
                # only re-raise if it's *not* the exception that was
                # passed to throw(), because __exit__() must not raise
                # an exception unless __exit__() itself failed.  But throw()
                # has to raise the exception to signal propagation, so this
                # fixes the impedance mismatch between the throw() protocol
                # and the __exit__() protocol.
                if sys.exc_info()[1] is not value:
                    raise

def manager(func):
    """Emulate 2.5 ``@contextlib.contextmanager`` decorator"""
    gcm = _GeneratorContextManager
    return rewrap(func, lambda *args, **kwds: gcm(func(*args, **kwds)))

def with_(ctx, func):
    """Perform PEP 343 "with" logic for Python versions <2.5

    The following examples do the same thing at runtime::

        Python 2.5+          Python 2.3/2.4
        ------------         --------------
        with x as y:         z = with_(x,f)
            z = f(y)

    This function is used to implement the ``call_with()`` decorator, but
    can also be used directly.  It's faster and more compact in the case where
    the function ``f`` already exists.
    """
    inp = ctx.__enter__()
    try:
        retval = func(inp)
    except:
        if not ctx.__exit__(*sys.exc_info()):
            raise
    else:
        ctx.__exit__(None, None, None)
        return retval

def reraise():
    """Reraise the current contextmanager exception, if any"""
    typ,val,tb = _exc_info.get(get_ident(), nones)
    if typ:
        try:
            raise typ,val,tb
        finally:
            del typ,val,tb




def call_with(ctxmgr):
    """Emulate the PEP 343 "with" statement for Python versions <2.5

    The following examples do the same thing at runtime::

        Python 2.5+          Python 2.4
        ------------         -------------
        with x as y:         @call_with(x)
            print y          def do_it(y):
                                 print y

    ``call_with(foo)`` returns a decorator that immediately invokes the
    function it decorates, passing in the same value that would be bound by
    the ``as`` clause of the ``with`` statement.  Thus, by decorating a
    nested function, you can get most of the benefits of "with", at a cost of
    being slightly slower and perhaps a bit more obscure than the 2.5 syntax.

    Note: because of the way decorators work, the return value (if any) of the
    ``do_it()`` function above will be bound to the name ``do_it``.  So, this
    example prints "42"::

        @call_with(x)
        def do_it(y):
            return 42

        print do_it

    This is rather ugly, so you may prefer to do it this way instead, which
    more explicitly calls the function and gets back a value::

        def do_it(y):
            return 42

        print with_(x, do_it)
    """
    return with_.__get__(ctxmgr, type(ctxmgr))





noop = lambda key, rule: rule
mngr = lambda key, rule: Action.manage(rule())
call = lambda key, rule: rule()

class Service(_ClassDelegate):
    """A replaceable, thread-local singleton"""

    __slots__ = ()  # pure mixin class

    def __default__(cls):
        return cls()

    __default__ = classmethod(__default__)

    def __fallback__(cls, inherit, key):
        if inherit: return inherit(key)
        return cls.__default__

    __fallback__ = classmethod(__fallback__)
    __apply__ = staticmethod(call)

    def new(cls, factory=None):
        factory = factory or cls
        state = State.child().__enter__()
        try:
            # we use a lambda below to ensure that the rule is unique; that way,
            # we are guaranteed to get a *new* instance of the service in the
            # scope, rather than reusing the existing one.
            state[cls.get.im_self] = lambda: factory()
            yield cls.get()
            reraise()
        except:
            state.__exit__(*sys.exc_info())
            raise
        else:
            state.__exit__(None, None, None)

    new = classmethod(manager(new))



class Scope(Service):
    """A scope for resources"""

    def __init__(self):
        self.state = State.get()
        self.cache = {}

    def __compute__(cls, key, func, input):
        self = cls.get()
        cache = self.cache
        if cache is None:
            raise ScopeError(self.__class__.__name__+" is already exited")
        elif input is not self.state[key]:
            raise ScopeError("Redefined rule in sub-state")
        elif key in cache:
            return cache[key]
        else:
            old = self.state.swap()
            try:
                cache[key] = value = self.manage(func(input))
                self.state.on_exit(self.atexit)
                return value
            finally:
                old.swap()

    __compute__ = classmethod(__compute__)

    def manage(self, ob):
        """Do any necessary magic on 'ob' and return the new value"""
        return ob

    def atexit(self, *exc):
        self.cache = None

    def __default__(cls):
        raise RuntimeError("No %s is currently active" % (cls.__name__))
    __default__ = classmethod(__default__)




    def resource(cls, func):
        """Decorator to create a scoped resource"""
        return setting(func, wrap=cls.__compute__)
    resource = classmethod(resource)

    def resource_registry(cls, func):
        """Decorator to create a scoped resource registry"""
        return registry(func, wrap=cls.__compute__)
    resource_registry = classmethod(resource_registry)


class Action(Scope):
    """Service for managing transaction-scoped resources"""

    def __init__(self):
        self.managers = []
        super(Action, self).__init__()

    def atexit(self, *exc):
        super(Action, self).atexit(*exc)
        managers, self.managers = self.managers, None
        while managers:
            managers.pop().__exit__(*exc)  # XXX how do we handle errors?

    def manage(self, ob):
        enter = getattr(ob, '__enter__', None)
        if enter is None:
            return ob
        ctx = ob
        ob  = ctx.__enter__()

        # don't call __exit__ unless __enter__ succeeded
        # (if there was an error, we wouldn't have gotten this far)
        self.managers.append(ctx)
        return ob
        # XXX return self.manage(ob)

resource = Action.resource
resource_registry = Action.resource_registry


def nop(): pass

class setting(object):
    """Decorator that turns a function into a contextual variable"""

    __class__ = type(nop)
    func_code = nop.func_code
    func_defaults = ()

    __argnames__ = ('value','expr'),

    def __init__(self, func, wrap=None):
        if func.func_code.co_argcount != len(self.__argnames__):
            raise TypeError(
                type(self).__name__+" function must have exactly %d argument(s)"
                % len(self.__argnames__)
            )
        for num, (var, names) in enumerate(
            zip(func.func_code.co_varnames, self.__argnames__)
        ):
            if var not in names:
                raise TypeError(
                    type(self).__name__+" function argument %d must be named '%s'"
                    % (num+1, "' or '".join(names))
                )
        if self.__argnames__ and (not func.func_defaults or len(func.func_defaults)!=1):
            raise TypeError(
                type(self).__name__ +
                " function must have a default value for last argument"
            )

        self.__function__  = func
        self.__module__    = func.__module__
        self.__name__      = func.__name__
        self.__doc__       = func.__doc__
        if wrap: self.__wrap__ = wrap

    __call__ = lookup



    def __apply__(self, key, input):
        return self.__wrap__(key, self.__function__, input)

    def __wrap__(self, key, func, input):
        return func(input)

    def __fallback__(self, inherit, key):
        if inherit is None:
            return self.__function__.func_defaults[0]
        else:
            return inherit(key)

    def __ilshift__(self, value):
        State[self] = value
        return self

    def __repr__(self):
        if self.__module__: return self.__module__ + '.' + self.__name__
        return self.__name__

    def __mod__(self, other):
        if self.__function__.func_code.co_varnames[
            len(type(self).__argnames__)-1
        ]=='expr':
            return 'lambda: '+other
        return other















def _with_prefix((pre, func), suffix):
    return func(pre+suffix)

def _prefixer(prefix, func):
    return _with_prefix.__get__((prefix, func), tuple)

if _prefixer(1, 2) != _prefixer(1, 2):  # 2.3 and 2.4 don't compare selves
    class _prefixer(tuple):
        __slots__ = []
        def __new__(cls, prefix, func):
            return tuple.__new__(cls, (prefix, func))
        def __init__(cls, prefix, func):
            pass
        def __call__(self, suffix):
            return self[1](self[0]+suffix)

class wildcard(setting):
    """Object used to do parent namespace rule lookups"""

    def __init__(self, registry):
        self.__module__ = registry.__module__
        self.__name__   = registry.__name__ + '.*'
        self.__function__ = registry.__function__
        self.__namespace__ = registry

    def __mod__(self, other):
        return 'lambda suffix: '+other

    def __apply__(self, key, input):
        return input

    def __fallback__(self, inherit, key):
        parent = self.__namespace__
        if parent.__namespace__:
            func = State.get(parent.__namespace__['*'])
            if func is not None:
                prefix = self.__name__.split('.')[-2]+'.'
                return _prefixer(prefix, func)
        # couldn't find a parent wildcard rule, return None


class registry(setting):
    """Decorator that turns a function into a contextual registry"""

    __argnames__ = ('suffix',), ('value','expr')
    func_code = (lambda key, default: None).func_code
    func_defaults = (None,)

    def __init__(self, func, ns=None, name='', wrap=None):
        setting.__init__(self, func, wrap)
        self.__name__ = name or self.__name__
        self.__namespace__ = ns
        self.__contents__ = {'*': wildcard(self)}

    def __getitem__(self, key):
        if '.' in key:
            for key in key.split('.'): self = self[key]
            return self
        try:
            return self.__contents__[key]
        except KeyError:
            s = self.__dict__[key] = self.__contents__.setdefault(key, registry(
                self.__function__, self, self.__name__ + '.' + key,
                self.__dict__.get('__wrap__')
            ))
            return s

    def __getattr__(self, key):
        if key.startswith('__') and key.endswith('__'):
            raise AttributeError(key)
        return self[key]

    def __contains__(self,key):
        if '.' in key:
            for key in key.split('.'):
                if key not in self.__contents__:
                    return False
                self = self[key]
            else:
                return True
        return key in self.__contents__

    def __iter__(self):
        return iter([key for key in self.__contents__ if key!='*'])

    def __call__(self, key, default=None):
        if key not in self:
            return default
        return lookup(self[key])

    def __apply__(self, key, input):
        return self.__wrap__(key, self.__function__.__get__(''), input)

    def __fallback__(self, inherit, key):
        if self.__namespace__:
            # Not the root registry, try looking up wildcard rule(s)
            suffix = key.__name__[len(self.__namespace__.__name__)+1:]
            finder = State.get(self.__namespace__['*'])
            if finder is not None:
                return finder(suffix)

        # No wildcards in registries above me, so try to inherit instead:
        if inherit is not None:
            return inherit(key)

        # We're in the root state; make sure we're in the root registry too
        while self.__namespace__: self = self.__namespace__

        # And then invoke the registry function with the suffix
        suffix = key.__name__[len(self.__name__)+1:]
        return self.__function__(suffix)

    def __setitem__(self, key, value):
        if value is not self[key]:
            raise TypeError("Registries are read-only")

    def __setattr__(self, key, value):
        if key.startswith('__') and key.endswith('__'):
            return object.__setattr__(self, key, value)
        else:
            self[key] = value


class Source(object):
    """Object representing a source file (or pseudo-file)"""

    __slots__ = "filename", "__weakref__"

    def __init__(self, filename, source=None):
        global linecache; import linecache
        self.filename = filename
        if source is not None:
            cache_source(filename, source, self)

    def compile(self, *args, **kw):
        return Line(''.join(self), self, 1).compile(*args, **kw)

    def __getitem__(self, key):
        return Line(linecache.getlines(self.filename)[key], self, key+1)

    def __repr__(self):
        return "Source(%r)" % self.filename

    def recode(self, code, offset=0):
        import new
        if not isinstance(code, new.code):
            return code
        return new.code(
            code.co_argcount, code.co_nlocals, code.co_stacksize,
            code.co_flags, code.co_code,
            tuple([self.recode(c, offset) for c in code.co_consts]+[self]),
            code.co_names, code.co_varnames, code.co_filename, code.co_name,
            code.co_firstlineno+offset, code.co_lnotab, code.co_freevars,
            code.co_cellvars
        )









class Line(str):
    """String that knows its file and line number"""

    def __new__(cls, text, source, line):
        return str.__new__(cls, text)

    def __init__(self, text, source, line):
        self.source = source
        self.line = line

    def compile(self, *args, **kw):
        # XXX needs syntax error trapping, unicode encoding support
        code = compile(self, self.source.filename, *args, **kw)
        return self.source.recode(code, self.line-1)

    def eval(self, *args):
        return eval(self.compile('eval'), *args)

    def splitlines(self, *args, **kw):
        return [Line(line, self.source, self.line+offset)
            for offset, line in enumerate(str.splitlines(self, *args, **kw))]

    for m in [
        'capitalize', 'center', 'expandtabs', 'ljust', 'lower', 'lstrip',
        'replace', 'rjust', 'rstrip', 'strip', 'swapcase', 'title',
        'translate', 'upper', 'zfill', '__add__', '__radd__', '__getslice__',
        '__mod__', '__rmod__',
    ]:
        if hasattr(str, m):
            locals()[m] = (lambda f:
                lambda self,*args,**kw: Line(
                    f(self,*args,**kw), self.source, self.line
                )
            )(getattr(str,m))







def replaces(target):
    """Class decorator to indicate that this service replaces another"""

    def decorator(cls):
        if not issubclass(cls, Service):
            raise TypeError(
                "context.replaces() can only be used in a context.Service"
                " subclass"
            )
        cls.get = staticmethod(target.get)
        return cls

    from peak.util.decorators import decorate_class
    decorate_class(decorator)

    # Ensure that context.replaces() is used only once per class suite
    cdict = sys._getframe(1).f_locals

    if cdict.setdefault('get', target.get) is not target.get:
        raise ValueError(
            "replaces() must be used only once per class;"
            " there is already a value for ``get``: %r"
            % (cdict['get'],)
        )

















