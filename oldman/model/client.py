from oldman.exception import OMClassInstanceError
from oldman.model.model import Model


class ClientModel(Model):
    """TODO: describe.

    TODO: further study this specific case.

    Contains methods for end-users (--> layer above the user mediator).

     """

    @classmethod
    def copy_store_model(cls, store_model):
        """TODO: describe """
        return ClientModel(store_model.name, store_model.class_iri, store_model.ancestry_iris,
                           store_model.context, store_model.om_attributes, operations=store_model._operations,
                           local_context=store_model.local_context,
                           accept_new_blank_nodes=store_model.accept_new_blank_nodes)

    def __init__(self, name, class_iri, ancestry_iris, context, om_attributes, operations=None,
                 local_context=None, accept_new_blank_nodes=False):
        Model.__init__(self, name, class_iri, ancestry_iris, context, om_attributes,
                       accept_new_blank_nodes, operations=operations, local_context=local_context)
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
        """TODO: describe. Not for end-users! """
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

    def new(self, session, iri=None, hashless_iri=None, collection_iri=None, **kwargs):
        """Creates a new :class:`~oldman.resource.Resource` object without saving it.

        The `class_iri` attribute is added to the `types`.

        See :func:`~oldman.mediation.mediator.ResourceManager.new` for more details.
        """
        types, kwargs = self._update_kwargs_and_types(kwargs, include_ancestry=True)
        return session.new(iri=iri, hashless_iri=hashless_iri, collection_iri=collection_iri,
                           types=types, **kwargs)

    def filter(self, session, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `class_iri` attribute is added to the `types`.

        See :func:`oldman.resource.finder.ResourceFinder.filter` for further details."""
        types, kwargs = self._update_kwargs_and_types(kwargs)
        return session.filter(types=types, hashless_iri=hashless_iri, limit=limit, eager=eager,
                              pre_cache_properties=pre_cache_properties, **kwargs)

    def get(self, session, iri, eager_with_reversed_attributes=None):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `class_iri` attribute is added to the `types`.
        Also looks if reversed attributes should be considered eagerly.

        See :func:`oldman.store.datastore.DataStore.get` for further details."""
        types, _ = self._update_kwargs_and_types({})

        if eager_with_reversed_attributes is None:
            eager_with_reversed_attributes = self._has_reversed_attributes

        return session.get(iri=iri, types=types, eager_with_reversed_attributes=eager_with_reversed_attributes)

    def first(self, session, hashless_iri=None, eager_with_reversed_attributes=True, pre_cache_properties=None,
              **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `class_iri` attribute is added to the `types`.

        See :func:`oldman.resource.finder.ResourceFinder.filter` for further details."""
        types, kwargs = self._update_kwargs_and_types(kwargs)
        return session.first(types=types, hashless_iri=hashless_iri,
                             eager_with_reversed_attributes=eager_with_reversed_attributes,
                             pre_cache_properties=pre_cache_properties, **kwargs)

    def all(self, session, limit=None, eager=False):
        """Finds every :class:`~oldman.resource.Resource` object that is instance
        of its RDFS class.

        :param limit: Upper bound on the number of solutions returned (SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within one single SPARQL query.
                      Defaults to `False` (lazy).
        :return: A generator of :class:`~oldman.resource.Resource` objects.
        """
        return self.filter(session, types=[self._class_iri], limit=limit, eager=eager)

    def _update_kwargs_and_types(self, kwargs, include_ancestry=False):
        types = list(self._class_types) if include_ancestry else [self._class_iri]
        if "types" in kwargs:
            new_types = kwargs.pop("types")
            types += [t for t in new_types if t not in types]
        return types, kwargs

