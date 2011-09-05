============================================================
Creating Extensible Applications and Frameworks With Plugins
============================================================

The ``peak.util.plugins`` module provides some simple utilities to make it
easy to create pluggable applications:

* ``Hook`` objects let you easily register and invoke or access extensions that
  have been manually registered or automatically discovered via setuptools
  entry points.

* ``Extensible`` objects can automatically find, load, and activate associated
  add-ons or modifier hooks.  This is most useful in conjunction with ``AddOn``
  classes (from the `AddOns`_ package), but can be used with any callables.

* The ``PluginManager`` service manages plugin eggs, and can be subclassed or
  replaced to support alternative means of locating hook implementations.
  (That is, in addition to or in replacement of setuptools.)

These utilities work well together but can also be used independently.  For
example, you can use ``Extensible`` objects without using ``Hook`` or
``PluginManager``, and you can use ``PluginManager`` without ``Hook`` or
``Extensible``.  (Using ``Hook`` objects, however, does require a
``PluginManager``.)


.. _AddOns: http://pypi.python.org/pypi/AddOns/

.. contents:: **Table of Contents**


Using Hooks
===========

A hook is a place in an application where plugins can add functionality, by
registering implementations of the hook.  For example, a hook can be used to
notify plugins of some application event, or to request plugins' participation
in some process.  Hooks can also just be used to register and find objects
that provide some application-specific interface.

Hooks are created using a "group name", and an optional "implementation name".
(These names correspond to setuptools "entry point group" names and "entry
point" names, respectively.)

The group name should consist of one or more Python identifiers, separated by
dots.  It does not need to be a valid package or module name, but it should be
a globally unique name.  That is, it should include an application or library
name, so that it can't clash with names in use by other apps, libraries, or
plugins.

Let's create an example hook::

    >>> from peak.util import plugins

    >>> hook1 = plugins.Hook('plugins.demo.hook1')

    >>> hook1
    Hook('plugins.demo.hook1', None)
 
    >>> list(hook1)
    []

Iterating over a hook yields any implementations that have been registered
under the hook's group name, but our example hook doesn't have anything
registered for it yet.  So let's register one, using the ``register`` method::

    >>> hook1.register('Hello world')
    >>> list(hook1)
    ['Hello world']

Note that we can pass absolutely any object to ``register()``; hooks do not
know or care what sort of objects they operate on.  There is also no duplicate
detection: if you register an object more than once, it will be listed more
than once when you iterate over the hook.

Also note that hook registration is global and permanent.  You cannot remove
a registration once it is added.  Also, registration works strictly by group
*name*, rather than by hook instance.  If two or more ``Hook`` objects share
the same group name, they will also share the implementations registered for
that name::

    >>> list(plugins.Hook('plugins.demo.hook1'))
    ['Hello world']

The way this works is that ``Hook`` objects actually delegate registration and
retrieval operations to the ``PluginManager`` service.  This allows modules to
register extensions for other modules to use, without needing the other modules
to be imported at registration time.

(See also the section below on `The PluginManager Service`_ for more
information.)


Querying and Notifying
----------------------

In addition to simply providing iteration over registered implementations,
hooks have two convenience methods for querying or notifying plugins.
Specifically, you can use ``Hook.query()`` and ``Hook.notify()`` to invoke
hooks whose implementations are functions or other callable objects.  For
example::

    >>> def echo(*args, **kw):
    ...     print "called with", args, kw

    >>> def compute(*args, **kw):
    ...     return 42, args, kw

    >>> demo = plugins.Hook('plugins.demo.hook2')
    >>> demo.register(echo)
    >>> demo.register(compute)

    >>> demo.notify()
    called with () {}

    >>> demo.notify(57, x=3)
    called with (57,) {'x': 3}

    >>> for result in demo.query(): print result
    called with () {}
    None
    (42, (), {})

    >>> for result in demo.query(99): print result
    called with (99,) {}
    None
    (42, (99,), {})

As you can see, the ``.notify()`` method does not return a value, but simply
calls each implementation of the hook with the given arguments.  ``.query()``,
however, yields the result of each call.


Named Implementations
---------------------

By default, the name of a registered implementation is not significant; most
of the time, you just want all registered implementations for a specified
group name, regardless of the individual implementations' names.  However, it
is sometimes useful to subdivide a hook's implementations using another level
of names.

For example, suppose you are writing a blogging application that processes
various input formats, and you'd like plugins to be able to register hook
implementations for specific file extensions.  You can do this by registering
implementations with an implementation name::

    >>> def rst_formatter(filename):
    ...     print "formatting",filename,"using reST"

    >>> def txt_formatter(filename):
    ...     print "formatting",filename,"as plain text"

    >>> formatters = plugins.Hook('blogtool.formatters')
    >>> formatters.register(rst_formatter, '.rst')
    >>> formatters.register(txt_formatter, '.txt')

    >>> list(formatters)
    [<function rst_formatter...>, <function txt_formatter...>]

And then retriveing them using a ``Hook`` that has both a group name and
an implementation name::

    >>> plugins.Hook('blogtool.formatters', '.rst').notify("foo.rst")
    formatting foo.rst using reST

    >>> plugins.Hook('blogtool.formatters', '.txt').notify("bar.txt")
    formatting bar.txt as plain text

The second argument to the ``Hook()`` constructor (and the ``Hook.register()``
method) is an **implementation name**.  If supplied, it must be a non-empty
ASCII string that does not start with a ``[``, contain any control characters
or ``=`` signs.  (It must also not begin or end with whitespace.)

Note, by the way, that these implementation names are not necessarily unique.
For example, multiple plugins could register a ``.rst`` formatter, and it is up
to the code using the ``Hook`` to decide how to handle that!  Also notice that
the ``blogtool.formatters`` hook above lists *all* registered formatters, no
matter what implementation name they are registered under.  It's also possible
for the same implementation to be registered under more than one name, in which
case it will be listed more than once in the overall hook, e.g.::

    >>> formatters.register(rst_formatter, '.txt')
    >>> list(formatters)
    [<function rst_formatter...>, <function txt_formatter...>,
     <function rst_formatter...>]

    >>> list(plugins.Hook('blogtool.formatters', '.txt'))
    [<function txt_formatter...>, <function rst_formatter...>]

Finally, note that hooks tied to a specific implementation name can also be
used for registration, e.g.::

    >>> foo = plugins.Hook('blogtool.formatters', '.foo')
    >>> foo
    Hook('blogtool.formatters', '.foo')

    >>> foo.register(42)
    >>> list(foo)
    [42]

    >>> list(formatters)
    [..., 42]

But you must either omit the implementation name from the ``.register()`` call
(as shown above), or else it must match the implementation name the hook was
created with::

    >>> foo.register(21, '.foo')    # ok - same name

    >>> foo.register(99, 'blue!')   # not ok!
    Traceback (most recent call last):
     ...
    ValueError: Can only register .foo implementations

   
Automatic Discovery Using Entry Points and Eggs
-----------------------------------------------

So far, we have only seen manually-registered hook implementations.  This is
fine for demonstration, but in a real application with plugins, it would be
necessary to first *find* and load the plugins' code in order to do such
registrations.

To address this issue, setuptools provides a feature called "entry points",
which can be used to include registration data in plugins' eggs.  This allows
hook implementations to be imported on demand.

To register a hook implementation for auto-discovery, the plugin's ``setup.py``
must use setuptools, and define entry points like this::

    setup(
        ...
        entry_points = """
        [blogtool.formatters]
        .rst = some.module:some_object
        .txt = other.module:other_object

        [some.other.hook]
        any old name here = whatever:SomeClass
        something without an equals sign = foo:bar
        """
    )

When the plugin is active on ``sys.path`` (i.e., it's importable), iterating
over an appropriate ``Hook`` object will automatically import the specified
object(s) and yield them.

In the example above, ``some_object`` will be imported from ``some.module``
and yielded whenever iterating over ``Hook('blogtool.formatters')`` or
``Hook('blogtool.formatters', '.rst')``.  (Note that you must always name the
implementations listed in ``setup.py``, even if the application does not look
up implementations by name!)

Through this automatic, on-demand import process, it is not necessary to find
and import the plugins in order to register hook implementations.  Instead,
merely installing the plugin is sufficient to make its hook implementations
available.  This also speeds up application startup, because implementations
are not imported until they are used.  (And performance can often be further
improved by putting less frequently-used hook implementations into separate
modules from those that are used more often.)

Of course, most applications will want to have one or more special directories
for installing and using egg plugins; you can use `the PluginManager service`_ to
locate and selectively activate the plugins found in such directories.

See also:

* `The setuptools documentation on entry points`_

* `The pkg_resources entry point API`_

.. _The setuptools documentation on entry points: http://peak.telecommunity.com/DevCenter/setuptools#dynamic-discovery-of-services-and-plugins

.. _The pkg_resources entry point API: http://peak.telecommunity.com/DevCenter/PkgResources#entry-points


Extensible Objects
==================

The ``Extensible`` mixin class is a convenient way to activate add-on hooks for
an object.  To implement an extensible object, you subclass or mix in
``Extensible``, add an ``extend_with`` attribute, and call ``load_extensions()``
at an appropriate time::

    >>> AppExtensions = plugins.Hook('my_app.App.extensions')

    >>> class App(plugins.Extensible):
    ...     extend_with = AppExtensions

    >>> def hello(app):
    ...     print "Hi, I'm extending", app
    >>> AppExtensions.register(hello)

    >>> a = App()
    >>> a.load_extensions()
    Hi, I'm extending <App object at...>

The ``extend_with`` attribute must be a one-argument callable, a sequence of
callables, or a sequence of sequences of callables (recursively).  Since
``Hook`` objects are iterable, they can be used as long as their
implementations are either one-argument callables or nested sequences thereof.

When an ``Extensible`` object's ``load_extensions()`` method is called, the
``extend_with`` sequence is recursively iterated, and all callables found are
invoked with the extensible object as the sole argument.  Here's an example
using a mixed and nested sequence of callables::

    >>> class App(plugins.Extensible):
    ...     extend_with = (AppExtensions, (hello, AppExtensions), hello)

    >>> a = App()
    >>> a.load_extensions()
    Hi, I'm extending <App object at...>
    Hi, I'm extending <App object at...>
    Hi, I'm extending <App object at...>
    Hi, I'm extending <App object at...>

The callables can be any 1-argument callable, but you will usually want them
to be ``AddOn`` classes.  Add-ons let you attach additional state and methods
to an object, in a private namespace that doesn't interfere with the object's
existing attributes and methods.  (See the `AddOns`_ package for more info.)


The PluginManager Service
=========================

TODO
  * document ``addEntryPoint()``, ``iterHooks()``

  * actually implement some plugin directory services, cached working_set and
    environment, etc.


Replacing the PluginManager
---------------------------

TODO
 * example of subclassing PluginManager and activating it using a with: block


Threading Concerns
------------------

By default, a separate ``PluginManager`` is created for each thread, and they
will share a single working set but use different environments.  This is
probably NOT what you want in a threaded environment!

This issue will be addressed in future releases, but for now you should avoid
using ``PluginManager`` configuration methods  from multiple threads.

It is, however, safe to use ``Hook`` objects from multiple threads, as this
is a read-only operation.  In principle, accessing a ``Hook`` from one thread
while configuring the ``PluginManager`` in another thread could cause a hook
to be skipped or doubled, although this is very unlikely.  It would be best
to do all of your ``PluginManager`` configuration before starting threads that
use ``Hook`` objects, at least with the current version of ``Plugins``.


Mailing List
============

Questions, discussion, and bug reports for this software should be directed to
the PEAK mailing list; see http://www.eby-sarna.com/mailman/listinfo/PEAK/
for details.


Implementation Status
=====================

While the ``PluginManager`` features are still in development (and remain
undocumented), this package is only available via SVN checkout.  However,
all documented features are tested and usable, and I don't expect any
significant changes to the APIs currently documented here.

