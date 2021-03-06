import logging
from oldman.exception import OMReservedAttributeNameError, OMAttributeAccessError


class Model(object):
    """A :class:`~oldman.model.Model` object represents a RDFS class on the Python side.

    TODO: update this documentation

    It gathers :class:`~oldman.attribute.OMAttribute` objects and Python methods
    which are made available to :class:`~oldman.resource.Resource` objects that are
    instances of its RDFS class.

    It also creates and retrieves :class:`~oldman.resource.Resource` objects that are
    instances of its RDFS class. It manages an :class:`~oldman.iri.IriGenerator` object.


    .. admonition:: Model creation

        :class:`~oldman.model.Model` objects are normally created by a
        :class:`~oldman.resource.manager.ResourceManager` object. Please use the
        :func:`oldman.resource.manager.ResourceManager.create_model` method for creating new
        :class:`~oldman.model.Model` objects.


    :param manager: :class:`~oldman.resource.manager.ResourceManager` object
                    that has created this model.
    :param name: Model name. Usually corresponds to a JSON-LD term or to a class IRI.
    :param class_iri: IRI of the RDFS class represented by this :class:`~oldman.model.Model` object.
    :param ancestry_iris: ancestry of the attribute `class_iri`.
                          Each instance of `class_iri` is also instance of these classes.
    :param context: An IRI, a `list` or a `dict` that describes the JSON-LD context.
                    See `<http://www.w3.org/TR/json-ld/#the-context>`_ for more details.
    :param om_attributes: `dict` of :class:`~oldman.attribute.OMAttribute` objects. Keys are their names.
    :param id_generator: :class:`~oldman.iri.IriGenerator` object that generates IRIs from new
                         :class:`~oldman.resource.Resource` objects.
    :param methods: `dict` of Python functions that takes as first argument a
                    :class:`~oldman.resource.Resource` object. Keys are the method names.
                    Defaults to `{}`.
    :param operations: TODO: describe.
    :param local_context: TODO: describe.
    """

    def __init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                 id_generator, operations=None, local_context=None):
        reserved_names = ["id", "hashless_iri", "_types", "types"]
        for field in reserved_names:
            if field in om_attributes:
                raise OMReservedAttributeNameError("%s is reserved" % field)
        self._name = name
        self._context = clean_context(context)
        self._local_context = local_context if local_context is not None else self._context
        self._class_iri = class_iri
        self._om_attributes = om_attributes
        self._id_generator = id_generator
        self._class_types = ancestry_iris
        self._operations = operations if operations is not None else {}
        self._operation_by_name = {op.name: op for op in operations.values()
                                   if op.name is not None}

        self._has_reversed_attributes = True in [a.reversed for a in self._om_attributes.values()]
        self._logger = logging.getLogger(__name__)

    @property
    def name(self):
        """Name attribute."""
        return self._name

    @property
    def class_iri(self):
        """IRI of the class IRI the model refers to."""
        return self._class_iri

    @property
    def ancestry_iris(self):
        """IRIs of the ancestry of the attribute `class_iri`."""
        return list(self._class_types)

    @property
    def methods(self):
        """Models does not support methods by default."""
        return {}

    @property
    def om_attributes(self):
        """ `dict` of :class:`~oldman.attribute.OMAttribute` objects. Keys are their names."""
        return dict(self._om_attributes)

    @property
    def context(self):
        """An IRI, a `list` or a `dict` that describes the JSON-LD context.
        See `<http://www.w3.org/TR/json-ld/#the-context>`_ for more details.

        Official context that will be included in the representation.
        """
        return self._context

    @property
    def local_context(self):
        """ Context available locally (but not to external consumer).
        TODO: describe further
        """
        return self._local_context

    @property
    def has_reversed_attributes(self):
        """Is `True` if one of its attributes is reversed."""
        return self._has_reversed_attributes

    def get_operation(self, http_method):
        """TODO: describe"""
        return self._operations.get(http_method)

    def get_operation_by_name(self, name):
        """TODO: describe"""
        return self._operation_by_name.get(name)

    def is_subclass_of(self, model):
        """Returns `True` if its RDFS class is a sub-class *(rdfs:subClassOf)*
        of the RDFS class of another model.

        :param model: :class:`~oldman.model.Model` object to compare with.
        :return: `True` if is a sub-class of the other model, `False` otherwise.
        """
        if self == model:
            return True
        if not isinstance(model, Model):
            return False
        return model.class_iri in self.ancestry_iris

    def access_attribute(self, name):
        """Gets an :class:`~oldman.attribute.OMAttribute` object.

        Used by the :class:`~oldman.resource.Resource` class but an end-user
        should not need to call it.

        :param name: Name of the attribute.
        :return: The corresponding :class:`~oldman.attribute.OMAttribute` object.
        """
        try:
            return self._om_attributes[name]
        except KeyError:
            raise OMAttributeAccessError("%s has no supported attribute %s" % (self, name))

    def generate_iri(self, **kwargs):
        """Generates a new IRI.

        Used by the :class:`~oldman.resource.Resource` class but an end-user
        should not need to call it.

        :return: A new IRI.
        """
        return self._id_generator.generate(**kwargs)

    def reset_counter(self):
        """Resets the counter of the IRI generator.

        Please use it only for test purposes.
        """
        if hasattr(self._id_generator, "reset_counter"):
            self._id_generator.reset_counter()


class ClientModel(Model):
    """TODO: describe.

    TODO: further study this specific case

     """

    @classmethod
    def copy_store_model(cls, resource_manager, store_model):
        """TODO: describe """
        return ClientModel(resource_manager, store_model.name, store_model.class_iri,
                           store_model.ancestry_iris, store_model.context, store_model.om_attributes,
                           store_model._id_generator, operations=store_model._operations,
                           local_context=store_model.local_context)

    def __init__(self, resource_manager, name, class_iri, ancestry_iris, context, om_attributes,
                 id_generator, operations=None, local_context=None):
        Model.__init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                       id_generator, operations=operations, local_context=local_context)
        self._resource_manager = resource_manager
        # {method_name: ancestor_class_iri}
        self._method_inheritance = {}
        # {method_name: method}
        self._methods = {}

    @property
    def methods(self):
        """`dict` of Python functions that takes as first argument a
        :class:`~oldman.resource.Resource` object. Keys are the method names.
        """
        return dict(self._methods)

    def declare_method(self, method, name, ancestor_class_iri):
        """TODO: describe """
        if name in self._methods:
            # Before overriding, compare the positions
            previous_ancestor_iri = self._method_inheritance[name]
            previous_ancestor_pos = self._class_types.index(previous_ancestor_iri)
            new_ancestor_pos = self._class_types.index(ancestor_class_iri)

            if new_ancestor_pos > previous_ancestor_pos:
                # Too distant, cannot override
                self._logger.warn(u"Method %s of %s is ignored by %s." % (name, ancestor_class_iri, self._class_iri))
                return

            self._logger.warn(u"Method %s of %s is overloaded for %s." % (name, ancestor_class_iri, self._class_iri))

        self._method_inheritance[name] = ancestor_class_iri
        self._methods[name] = method

    def new(self, id=None, hashless_iri=None, collection_iri=None, **kwargs):
        """Creates a new :class:`~oldman.resource.Resource` object without saving it.

        The `class_iri` attribute is added to the `types`.

        See :func:`~oldman.resource.manager.ResourceManager.new` for more details.
        """
        types, kwargs = self._update_kwargs_and_types(kwargs, include_ancestry=True)
        return self._resource_manager.new(id=id, hashless_iri=hashless_iri, collection_iri=collection_iri,
                                          types=types, **kwargs)

    def create(self, id=None, hashless_iri=None, collection_iri=None, **kwargs):
        """ Creates a new resource and saves it.

        See :func:`~oldman.model.Model.new` for more details.
        """
        return self.new(id=id, hashless_iri=hashless_iri, collection_iri=collection_iri, **kwargs).save()

    def filter(self, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `class_iri` attribute is added to the `types`.

        See :func:`oldman.resource.finder.ResourceFinder.filter` for further details."""
        types, kwargs = self._update_kwargs_and_types(kwargs)
        return self._resource_manager.filter(types=types, hashless_iri=hashless_iri, limit=limit, eager=eager,
                                             pre_cache_properties=pre_cache_properties, **kwargs)

    def get(self, id=None, hashless_iri=None, **kwargs):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `class_iri` attribute is added to the `types`.
        Also looks if reversed attributes should be considered eagerly.

        See :func:`oldman.store.datastore.DataStore.get` for further details."""
        types, kwargs = self._update_kwargs_and_types(kwargs)

        eager_with_reversed_attributes = kwargs.get("eager_with_reversed_attributes")
        if eager_with_reversed_attributes is None:
            eager_with_reversed_attributes = self._has_reversed_attributes

        return self._resource_manager.get(id=id, types=types, hashless_iri=hashless_iri,
                                          eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)

    def all(self, limit=None, eager=False):
        """Finds every :class:`~oldman.resource.Resource` object that is instance
        of its RDFS class.

        :param limit: Upper bound on the number of solutions returned (SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within one single SPARQL query.
                      Defaults to `False` (lazy).
        :return: A generator of :class:`~oldman.resource.Resource` objects.
        """
        return self.filter(types=[self._class_iri], limit=limit, eager=eager)

    def _update_kwargs_and_types(self, kwargs, include_ancestry=False):
        types = list(self._class_types) if include_ancestry else [self._class_iri]
        if "types" in kwargs:
            new_types = kwargs.pop("types")
            types += [t for t in new_types if t not in types]
        return types, kwargs


def clean_context(context):
    """Cleans the context.

    Context can be an IRI, a `list` or a `dict`.
    """
    #TODO: - make sure "id": "@id" and "types": "@type" are in
    if isinstance(context, dict) and "@context" in context.keys():
        context = context["@context"]
    return context