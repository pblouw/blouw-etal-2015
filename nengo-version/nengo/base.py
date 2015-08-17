import warnings

import numpy as np

from nengo.config import Config
from nengo.params import Default, is_param, Parameter
from nengo.utils.compat import with_metaclass


class NetworkMember(type):
    """A metaclass used to add instances of derived classes to networks.

    Inheriting from this class means that Network.add will be invoked after
    initializing the object, unless add_to_container=False is passed to the
    derived class constructor.
    """

    def __call__(cls, *args, **kwargs):
        """Override default __call__ behavior so that Network.add is called."""
        from nengo.network import Network
        inst = cls.__new__(cls)
        add_to_container = kwargs.pop('add_to_container', True)
        # Do the __init__ before adding in case __init__ errors out
        inst.__init__(*args, **kwargs)
        if add_to_container:
            Network.add(inst)
        inst._initialized = True  # value doesn't matter, just existance
        return inst


class NengoObject(with_metaclass(NetworkMember)):
    """A base class for Nengo objects.

    This defines some functions that the Network requires
    for correct operation. In particular, list membership
    and object comparison require each object to have a unique ID.
    """

    def __str__(self):
        if hasattr(self, 'label') and self.label is not None:
            return "%s: %s" % (self.__class__.__name__, self.label)
        else:
            return "%s: id=%d" % (self.__class__.__name__, id(self))

    def __repr__(self):
        return str(self)

    def __setattr__(self, name, val):
        if hasattr(self, '_initialized') and not hasattr(self, name):
            warnings.warn(
                "Creating new attribute '%s' on '%s'. "
                "Did you mean to change an existing attribute?" % (name, self),
                SyntaxWarning)
        if val is Default:
            val = Config.default(type(self), name)
        try:
            super(NengoObject, self).__setattr__(name, val)
        except Exception as e:
            arg0 = '' if len(e.args) == 0 else e.args[0]
            arg0 = ("Validation error when setting '%s.%s': %s"
                    % (self.__class__.__name__, name, arg0))
            e.args = (arg0,) + e.args[1:]
            raise

    @classmethod
    def param_list(cls):
        """Returns a list of parameter names that can be set."""
        return (attr for attr in dir(cls) if is_param(getattr(cls, attr)))

    @property
    def params(self):
        """Returns a list of parameter names that can be set."""
        return self.param_list()


class ObjView(object):
    """Container for a slice with respect to some object.

    This is used by the __getitem__ of Neurons, Node, and Ensemble, in order
    to pass slices of those objects to Connect. This is a notational
    convenience for creating transforms. See Connect for details.

    Does not currently support any other view-like operations.
    """

    def __init__(self, obj, key=slice(None)):
        self.obj = obj
        if isinstance(key, int):
            # single slices of the form [i] should be cast into
            # slice objects for convenience
            if key == -1:
                # special case because slice(-1, 0) gives the empty list
                key = slice(key, None)
            else:
                key = slice(key, key+1)
        self.slice = key

        # Node.size_in != size_out, so one of these can be invalid
        try:
            self.size_in = np.arange(obj.size_in)[self.slice].size
        except IndexError:
            self.size_in = None
        try:
            self.size_out = np.arange(obj.size_out)[self.slice].size
        except IndexError:
            self.size_out = None

    def __len__(self):
        return self.size_out

    @property
    def label(self):
        if isinstance(self.slice, list):
            sl_str = self.slice
        else:
            sl_start = "" if self.slice.start is None else self.slice.start
            sl_stop = "" if self.slice.stop is None else self.slice.stop
            if self.slice.step is None:
                sl_str = "%s:%s" % (sl_start, sl_stop)
            else:
                sl_str = "%s:%s:%s" % (sl_start, sl_stop, self.slice.step)
        return "%s[%s]" % (self.obj.label, sl_str)


class NengoObjectParam(Parameter):
    def __init__(self, default=None, optional=False, readonly=True,
                 nonzero_size_in=False, nonzero_size_out=False):
        assert default is None  # These can't have defaults
        self.nonzero_size_in = nonzero_size_in
        self.nonzero_size_out = nonzero_size_out
        super(NengoObjectParam, self).__init__(default, optional, readonly)

    def validate(self, instance, nengo_obj):
        from nengo.ensemble import Neurons
        if not isinstance(nengo_obj, (NengoObject, Neurons, ObjView)):
            raise ValueError("'%s' is not a Nengo object" % nengo_obj)
        if self.nonzero_size_in and nengo_obj.size_in < 1:
            raise ValueError("'%s' must have size_in > 0." % nengo_obj)
        if self.nonzero_size_out and nengo_obj.size_out < 1:
            raise ValueError("'%s' must have size_out > 0." % nengo_obj)
        super(NengoObjectParam, self).validate(instance, nengo_obj)
