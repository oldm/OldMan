from .manager import InstanceManager
from .resource import Resource
from .exception import OMReservedAttributeNameError
from .exception import OMAttributeAccessError


class Model(object):

    def __init__(self, name, class_iri, om_attributes, context, id_generator, class_types, dataset,
                 methods=None):
        reserved_names = ["id", "base_iri", "_types", "types"]
        for field in reserved_names:
            if field in om_attributes:
                raise OMReservedAttributeNameError("%s is reserved" % field)

        self._context = clean_context(context)
        self._class_iri = class_iri
        self._om_attributes = om_attributes
        self._id_generator = id_generator
        self._class_types = class_types
        self._dataset = dataset
        self._methods = methods if methods else {}

        registry = dataset.model_registry
        registry.register(self, name)
        #TODO: remove it
        self.objects = InstanceManager(self, self._dataset)

    @property
    def class_iri(self):
        return self._class_iri

    @property
    def class_types(self):
        return list(self._class_types)

    @property
    def om_attributes(self):
        return dict(self._om_attributes)

    @property
    def methods(self):
        return dict(self._methods)

    @property
    def context(self):
        return self._context

    def is_subclass_of(self, model):
        """
            rdfs:subClassOf test
        """
        if self == model:
            return True
        if not isinstance(model, Model):
            return False
        return model.class_iri in self.class_types

    def access_attribute(self, name):
        try:
            return self._om_attributes[name]
        except KeyError:
            raise OMAttributeAccessError("%s has no supported attribute %s" % (self, name))

    def generate_iri(self, **kwargs):
        return self._id_generator.generate(**kwargs)

    def reset_counter(self):
        """
            To be called after clearing the storage graph.
            For unittest purposes.
        """
        if hasattr(self._id_generator, "reset_counter"):
            self._id_generator.reset_counter()

    def new(self, **kwargs):
        types = list(self._class_types)
        if "types" in kwargs:
            #TODO: clarify the ordering
            new_types = kwargs.pop("types")
            types += [t for t in new_types if t not in types]

        return Resource(self._dataset, types=types, **kwargs)

def clean_context(context):
    """
        Context can be an IRI, a list or a dict
        TODO: - make sure "id": "@id" and "type": "@type" are in
    """
    if isinstance(context, dict) and "@context" in context.keys():
        context = context["@context"]
    return context