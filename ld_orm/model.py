from exceptions import Exception
from copy import deepcopy
from six import add_metaclass
from .attribute import DataAttribute
from .manager import InstanceManager
from rdflib import URIRef, Literal, Graph
import json


class MissingClassAttributeError(Exception):
    """
        Attributes "storage_graph", "class_uri" and "context" are compulsory.
    """
    pass


class ReservedAttributeError(Exception):
    pass


class ModelBase(type):
    """
        Metaclass for all models
    """
    def __new__(mcs, name, bases, attributes):
        if name != "Model":
            required_fields = ["class_uri", "storage_graph", "context"]
            for field in required_fields:
                if field not in attributes:
                    raise MissingClassAttributeError("%s is required for class %s" % (field, name))
            attributes["context"] = mcs.clean_context(attributes["context"])

            # Should type be reserved?
            # TODO: merge it with class_uri ?
            reserved_attributes = ["id", "type"]
            for field in reserved_attributes:
                if field in attributes:
                    raise ReservedAttributeError("%s is reserved" % field)

        # Descriptors
        attributes["_attributes"] = {k: v for k, v in attributes.iteritems()
                                     if isinstance(v, DataAttribute)}

        cls = type.__new__(mcs, name, bases, attributes)

        if name != "Model":
            #TODO: log a message if "objects" was already allocated (data attribute)
            #A la Django
            cls.objects = InstanceManager(cls)

        return cls

    @classmethod
    def clean_context(mcs, context):
        """
            TODO: - make sure context is structured like this:
                {"@context": ...}
                 - make sure "id": "@id" and "type": "@type" are in
        """
        return context


@add_metaclass(ModelBase)
class Model(object):
    """
        TODO: support ids
    """

    def __init__(self, **kwargs):
        """
            Does not save (like Django)
        """
        for k,v in kwargs.iteritems():
            setattr(self, k, v)
        if "id" not in kwargs:
            self.id = self.id_generator.generate(self)

    @classmethod
    def from_graph(cls, id, subgraph):
        """
            Loads a new instance from a subgraph
        """
        instance = cls(id=id)
        uri = URIRef(id)
        for attr_name, attr in instance._attributes.iteritems():
            property_uri = URIRef(attr.supported_property.property_uri)

            results = subgraph.objects(uri, property_uri)
            f = lambda x: str(x) if isinstance(r, Literal) else x
            values = [f(r) for r in results]
            #print "Results for %s: %s" %(attr_name, values)

            if len(values) == 0:
                continue
            if len(values) == 1:
                values = values[0]
            setattr(instance, attr_name, values)
        return instance

    def is_valid(self):
        for attr in self._attributes.values():
            if not attr.is_valid(self):
                return False
        return True

    def is_blank_node(self):
        """
            TODO: implement it
        """
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

        #TODO: remove former values

        #UGLY!! To be removed
        js = self.to_json()
        #print js
       # print Graph().parse(data=js, context=self.context, format="json-ld").serialize(format="turtle")
        self.storage_graph.parse(data=js, context=self.context, format="json-ld")
        #print self.storage_graph.serialize(format="trig")

    def to_json(self):
        """
            Pure JSON (not JSON-LD)
        """
        dct = self.to_dict()
        return json.dumps(dct)

    def to_dict(self):
        dct = { name: self._convert_value(getattr(self, name))
                 for name in self._attributes}
        dct["id"] = self.id
        #TODO: class URI
        dct["type"] = self.class_uri
        return dct

    def _convert_value(self, value):
        """
            TODO: improve it
        """
        if isinstance(value, list):
            return [self._convert_value(v) for v in value]
        if isinstance(value, Model):
            if value.is_blank_node():
                #TODO: what about its own context? Make sure contexts are
                # not incompatible
                return value._to_dict()
            # TODO: compare its URI if non-blank (if same document that self)
            else:
                # URI
                return value.id
        return value

    def to_jsonld(self):
        dct = deepcopy(self.context)
        dct.update(self.to_dict())
        return json.dumps(dct)
