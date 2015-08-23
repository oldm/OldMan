import logging

from oldman.core.exception import OMReservedAttributeNameError, OMAttributeAccessError


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


    :param name: Model name. Usually corresponds to a JSON-LD term or to a class IRI.
    :param class_iri: IRI of the RDFS class represented by this :class:`~oldman.model.Model` object.
    :param ancestry_iris: ancestry of the attribute `class_iri`.
                          Each instance of `class_iri` is also instance of these classes.
    :param context: An IRI, a `list` or a `dict` that describes the JSON-LD context.
                    See `<http://www.w3.org/TR/json-ld/#the-context>`_ for more details.
    :param om_attributes: `dict` of :class:`~oldman.attribute.OMAttribute` objects. Keys are their names.
    :param accept_new_blank_nodes: TODO: describe.
    :param methods: `dict` of Python functions that takes as first argument a
                    :class:`~oldman.resource.Resource` object. Keys are the method names.
                    Defaults to `{}`. TODO: remove??
    :param operations: TODO: describe.
    :param local_context: TODO: describe.
    """

    def __init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                 accept_new_blank_nodes, operations=None, local_context=None):
        reserved_names = ["id", "hashless_iri", "_types", "types"]
        for field in reserved_names:
            if field in om_attributes:
                raise OMReservedAttributeNameError("%s is reserved" % field)
        self._name = name
        self._context = clean_context(context)
        self._local_context = local_context if local_context is not None else self._context
        self._class_iri = class_iri
        self._om_attributes = om_attributes
        self._accept_new_blank_nodes = accept_new_blank_nodes
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

    @property
    def accept_new_blank_nodes(self):
        """TODO: describe. Useful for knowing if a bnode ID of a resource
         is temporary or maybe not."""
        return self._accept_new_blank_nodes

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


def clean_context(context):
    """Cleans the context.

    Context can be an IRI, a `list` or a `dict`.
    """
    #TODO: - make sure "id": "@id" and "types": "@type" are in
    if isinstance(context, dict) and "@context" in context.keys():
        context = context["@context"]
    return context