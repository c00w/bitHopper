import pkg_resources
from peak.util.decorators import struct
from peak.util import context

__all__ = ['Hook', 'Extensible', 'PluginManager']

def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt', package='__main__',
        optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
    )

class Extensible(object):
    """An object that can load hooks to extend itself (usually add-ons)"""
    __slots__ = ()  # pure mixin
    extend_with = ()

    def load_extensions(self):
        """Load extensions

        This method invokes each callable found by flattening the extensible's
        ``extend_with`` attribute, which must be a callable, a sequence of
        callables, or a sequence of sequences of callables (recursively).
        (Notice that this means ``extend_with`` can be a ``Hook`` instance, or
        even a sequence mixing callables and ``Hook`` objects.)

        Each callable found is invoked with ``self`` as the sole argument.
        """
        for ext in _flatten_callables(self.extend_with):
            ext(self)

def _flatten_callables(ob):
    if callable(ob):
        yield ob
    else:
        for sub_ob in ob:
            for ob in _flatten_callables(sub_ob):
                yield ob


class Hook(object):
    """A virtual collection of registered implementations"""

    __slots__ = ()  # pure mixin

    def __iter__(self):
        """Yield the registered entry points for this hook"""
        return PluginManager.iterHooks(self.group, self.impl)

    def register(self, ob, impl=None):
        if impl and self.impl and impl != self.impl:
            raise ValueError("Can only register "+self.impl+" implementations")
        return PluginManager.addEntryPoint(self.group, impl or self.impl, ob)
        
    def notify(self, *args, **kw):
        """Call all registered hooks with the given arguments"""
        for hook in self.query(*args, **kw):
            pass

    def query(self, *args, **kw):
        """Call registered hooks (w/given args), yielding each result"""
        if kw:
            for hook in self:
                yield hook(*args, **kw)
        elif args:
            for hook in self:
                yield hook(*args)
        else:
            for hook in self:
                yield hook()


struct(Hook)
def Hook(group, impl=None):
    """Easy access to a specific entry point or group of entry points"""
    return group, impl





_implementations = {}     # global implementation registry

class PluginManager(context.Service):
    """Manage plugin eggs"""

    def addEntryPoint(self, group, impl, ob):
        """Register an object as a hook"""
        _implementations.setdefault(group,[]).append((impl, ob))

    def iterHooks(self, group, impl=None, project=None):
        """Yield hooks for the given group, implementation name, and project

        Hooks registered via ``addEntryPoint()`` or as entry points in the
        given group/name/project are included.
        """
        if project:
            project = project.lower()

        for name, ob in _implementations.get(group, ()):
            if impl and name!=impl: continue
            yield ob

        for ep in pkg_resources.iter_entry_points(group, impl):
            yield ep.load()
        
















