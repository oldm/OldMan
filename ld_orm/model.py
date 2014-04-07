from exceptions import Exception
from six import add_metaclass
from .attribute import Attribute


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            if "class_uri" not in attributes:
                raise NoClassUriError("Please give a class_uri attribute for the class %s" % name)
        # Descriptors
        attributes["_attributes"] = {k: v for k, v in attributes.iteritems() if isinstance(v, Attribute)}

        cls = type.__new__(mcs, name, bases, attributes)
        return cls



@add_metaclass(ModelBase)
class Model(object):

    def __init__(self, **kwargs):
        for k,v in kwargs.iteritems():
            setattr(self, k, v)
        if len(kwargs) > 0:
            self.save()

    def is_valid(self):
        for attr in self._attributes.values():
            if not attr.is_valid(self):
                return False
        return True

    def save(self):
        """
            TODO:
                - Warns if there is some non-descriptor ("Attribute") attributes (will not be saved)
                - Saves descriptor attributes
        """
        for attr in self._attributes.values():
            # May raise an RequiredAttributeError
            attr.check_validity(self)

        #TODO: Warns

        #TODO: remove former values and store new ones


