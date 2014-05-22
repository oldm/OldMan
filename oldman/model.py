from .exception import OMReservedAttributeNameError, OMAttributeAccessError


class Model(object):

    def __init__(self, name, class_iri, om_attributes, context, id_generator, class_types,
                 manager, methods=None):
        reserved_names = ["id", "base_iri", "_types", "types"]
        for field in reserved_names:
            if field in om_attributes:
                raise OMReservedAttributeNameError("%s is reserved" % field)
        self._name = name
        self._context = clean_context(context)
        self._class_iri = class_iri
        self._om_attributes = om_attributes
        self._id_generator = id_generator
        self._class_types = class_types
        self._manager = manager
        self._methods = methods if methods else {}

    @property
    def name(self):
        return self._name

    @property
    def class_iri(self):
        return self._class_iri

    @property
    def ancestry_iris(self):
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
        return model.class_iri in self.ancestry_iris

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
        kwargs = self._update_kwargs_types(kwargs)
        return self._manager.new(**kwargs)

    def create(self, **kwargs):
        """
            Creates a new resource and saves it
        """
        return self.new(**kwargs).save()

    def filter(self, **kwargs):
        kwargs = self._update_kwargs_types(kwargs)
        return self._manager.filter(**kwargs)

    def get(self, **kwargs):
        kwargs = self._update_kwargs_types(kwargs)
        return self._manager.get(**kwargs)

    def all(self):
        return self.filter(types=[self._class_iri])

    def _update_kwargs_types(self, kwargs):
        types = list(self._class_types)
        if "types" in kwargs:
            new_types = kwargs.pop("types")
            types += [t for t in new_types if t not in types]
        kwargs["types"] = types
        return kwargs


def clean_context(context):
    """
        Context can be an IRI, a list or a dict
        TODO: - make sure "id": "@id" and "type": "@type" are in
    """
    if isinstance(context, dict) and "@context" in context.keys():
        context = context["@context"]
    return context