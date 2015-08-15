import logging
from uuid import uuid4
from oldman.resource.store import StoreResource

from oldman.store.cache import ResourceCache
from oldman.exception import UnsupportedDataStorageFeatureException, OMAttributeAccessError, OMUniquenessError
from oldman.exception import OMObjectNotFoundError, OMClassInstanceError


DEFAULT_MODEL_PREFIX = "Default_"


class Store(object):
    """A :class:`~oldman.store.store.Store` object manages CRUD operations on
    :class:`~oldman.resource.store.StoreResource` objects.

    In the future, non-CRUD operations may also be supported.

    Manages the cache (:class:`~oldman.resource.cache.ResourceCache` object) of
    :class:`~oldman.resource.store.StoreResource` object.

    :param model_manager: TODO: describe!!!
    :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                         This object must already be configured.
                         Defaults to `None` (no cache).
                         See :class:`~oldman.store.cache.ResourceCache` for further details.
    :param accept_iri_generation_configuration: If False, the IRI generator cannot be configured
                         by the user: it is imposed by the data store. Default to `False`.
    """
    _stores = {}

    def __init__(self, model_manager, cache_region=None, accept_iri_generation_configuration=True,
                 support_sparql=False):
        self._model_manager = model_manager
        self._logger = logging.getLogger(__name__)
        self._resource_cache = ResourceCache(cache_region)
        self._name = str(uuid4())
        self._stores[self._name] = self
        self._accept_iri_generation_configuration = accept_iri_generation_configuration
        self._support_sparql=support_sparql

        if not self._model_manager.has_default_model():
            self._model_manager.create_model(DEFAULT_MODEL_PREFIX + self._name, {u"@context": {}}, self, untyped=True,
                                             iri_prefix=u"http://localhost/.well-known/genid/%s/" % self._name,
                                             is_default=True)

    @property
    def model_manager(self):
        """The :class:`~oldman.model.manager.ModelManager` object.

        TODO: update

        Necessary for creating new :class:`~oldman.resource.store.StoreResource` objects
        and accessing to :class:`~oldman.model.Model` objects.
        """
        return self._model_manager

    @property
    def resource_cache(self):
        """:class:`~oldman.resource.cache.ResourceCache` object."""
        return self._resource_cache

    @classmethod
    def get_store(cls, name):
        """Gets a :class:`~oldman.store.datastore.DataStore` object by its name.

        :param name: store name.
        :return: A :class:`~oldman.resource.manager.ModelManager` object.
        """
        return cls._stores.get(name)

    @property
    def name(self):
        """Randomly generated name. Useful for serializing resources."""
        return self._name

    def support_sparql_filtering(self):
        """Returns `True` if the datastore supports SPARQL queries (no update).

        Note that in such a case, the :func:`~oldman.store.datastore.DataStore.sparql_filter` method is expected
        to be implemented.
        """
        return self._support_sparql

    def get(self, store_session, iri, types=None, eager_with_reversed_attributes=True):
        """Gets the :class:`~oldman.resource.Resource` object having the given IRI.

        The `kwargs` dict can contains regular attribute key-values.

        When `types` are given, they are then checked. An :exc:`~oldman.exception.OMClassInstanceError`
        is raised if the resource is not instance of these classes.

        :param iri: IRI of the resource. Defaults to `None`.
        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :return: A :class:`~oldman.resource.store.StoreResource` object or `None` if no resource has been found.
        """

        if iri is None:
            raise ValueError("iri is required")

        types = set(types) if types is not None else set()

        resource = self._get_by_iri(iri, store_session)
        if not types.issubset(resource.types):
            missing_types = types.difference(resource.types)
            raise OMClassInstanceError(u"%s found, but is not instance of %s" % (iri, missing_types))
        return resource

    def first(self, store_session, types=None, hashless_iri=None, eager_with_reversed_attributes=True,
              pre_cache_properties=None, **kwargs):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `kwargs` dict can contains regular attribute key-values.

        TODO: UPDATE THE COMMENT!

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :param eager_with_reversed_attributes: Allow to Look eagerly for reversed RDF properties.
               May cause some overhead for some :class:`~oldman.resource.Resource` objects
               that do not have reversed attributes. Defaults to `True`.
        :param pre_cache_properties: List of RDF ObjectProperties to pre-cache eagerly.
                      Their values (:class:`~oldman.resource.Resource` objects) are loaded and
                      added to the cache. Defaults to `[]`. If given, `eager` must be `True`.
                      Disabled if there is no cache.
        :return: A :class:`~oldman.resource.Resource` object or `None` if no resource has been found.
        """
        eager = pre_cache_properties is not None and len(pre_cache_properties) > 0

        if hashless_iri is None and types is None and len(kwargs) == 0:
            return self._get_first_resource_found(store_session)

        elif hashless_iri is not None:
            resources = self.filter(store_session, types=types, hashless_iri=hashless_iri, eager=eager,
                                    pre_cache_properties=pre_cache_properties, **kwargs)
            return self._select_resource_from_hashless_iri(hashless_iri, list(resources))

        else:
            # First found
            resources = self.filter(store_session, types=types, hashless_iri=hashless_iri, limit=1, eager=eager,
                                    pre_cache_properties=pre_cache_properties, **kwargs)
            for resource in resources:
                return resource

        return None

    def filter(self, store_session, types=None, hashless_iri=None, limit=None, eager=True, pre_cache_properties=None,
               **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `kwargs` dict can contains:

           1. regular attribute key-values ;
           2. the special attribute `iri`. If given, :func:`~oldman.store.datastore.DataStore.get` is called.

        TODO: UPDATE THE COMMENT!

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :param limit: Upper bound on the number of solutions returned (e.g. SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within the minimum number of queries
                      (e.g. one single SPARQL query). Defaults to `True`.
        :param pre_cache_properties: List of RDF ObjectProperties to pre-cache eagerly.
                      Their values (:class:`~oldman.resource.Resource` objects) are loaded and
                      added to the cache. Defaults to `[]`. If given, `eager` must be `True`.
                      Disabled if there is no cache.
        :return: A generator (if lazy) or a list (if eager) of :class:`~oldman.resource.Resource` objects.
        """
        if not eager and pre_cache_properties is not None:
            raise AttributeError(u"Eager properties are incompatible with lazyness. Please set eager to True.")

        iri = kwargs.pop("iri") if "iri" in kwargs else None
        type_iris = types if types is not None else []
        if iri is not None:
            return self.get(store_session, iri, types=types)

        if len(type_iris) == 0 and len(kwargs) > 0:
            raise OMAttributeAccessError(u"No type given in filter() so attributes %s are ambiguous."
                                         % kwargs.keys())

        return self._filter(store_session, type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs)

    def sparql_filter(self, store_session, query):
        """Finds the :class:`~oldman.resource.Resource` objects matching a given query.

        Raises an :class:`~oldman.exception.UnsupportedDataStorageFeatureException` exception
        if the SPARQL protocol is not supported by the concrete data_store.

        :param query: SPARQL SELECT query where the first variable assigned
                      corresponds to the IRIs of the resources that will be returned.
        :return: A generator of :class:`~oldman.resource.Resource` objects.
"""
        raise UnsupportedDataStorageFeatureException("This datastore %s does not support the SPARQL protocol."
                                                     % self.__class__.__name__)

    def flush(self, resources_to_update, resources_to_delete, is_end_user):
        """
        TODO: explain
        :param new_resources:
        :param resources_to_update:
        :param resources_to_delete:
        :return:
        """
        for resource in resources_to_update:
            # Uniqueness test
            if resource.is_new and self.exists(resource.id):
                raise OMUniquenessError("Object %s already exist" % resource.id)
            resource.check_validity(is_end_user=is_end_user)

        remaining_resources, deleted_resources = self._flush(resources_to_update, resources_to_delete)
        for resource in remaining_resources:
            self._resource_cache.set_resource(resource)
        for resource in deleted_resources:
            self._resource_cache.remove_resource(resource)
        return remaining_resources, deleted_resources

    def exists(self, resource_iri):
        """ Tests if the IRI of the resource is present in the data_store.

        May raise an :class:`~oldman.exception.UnsupportedDataStorageFeatureException` exception.

        :param resource_iri: IRI of the :class:`~oldman.resource.Resource` object.
        :return: `True` if exists.
        """
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot test the existence of an IRI."
                                                     % self.__class__.__name__)

    def generate_instance_number(self, class_iri):
        """ Generates a new incremented number for a given RDFS class IRI.

        May raise an :class:`~oldman.exception.UnsupportedDataStorageFeatureException` exception.

        :param class_iri: RDFS class IRI.
        :return: Incremented number.
        """
        raise UnsupportedDataStorageFeatureException("This datastore %s does not generate instance numbers."
                                                     % self.__class__.__name__)

    def reset_instance_counter(self, class_iri):
        """ Reset the counter related to a given RDFS class.

        For test purposes **only**.

        :param class_iri: RDFS class IRI.
        """
        raise UnsupportedDataStorageFeatureException("This datastore %s does not manage instance counters."
                                                     % self.__class__.__name__)

    def check_and_repair_counter(self, class_iri):
        """ Checks the counter of a given RDFS class and repairs (inits) it if needed.

        :param class_iri: RDFS class IRI.
        """
        raise UnsupportedDataStorageFeatureException("This datastore %s does not manage instance counters."
                                                     % self.__class__.__name__)

    def create_model(self, class_name_or_iri, context_iri_or_payload, iri_generator=None, iri_prefix=None,
                     iri_fragment=None, incremental_iri=False, context_file_path=None):
        """TODO: comment. Convenience function """
        if not self._accept_iri_generation_configuration:
            if iri_generator or iri_prefix or iri_fragment or incremental_iri:
                # TODO: find a better exception
                raise Exception("The generator is imposed by the store, it cannot be configured by the user.")
            else:
                iri_generator = self._create_iri_generator(class_name_or_iri)

        self._model_manager.create_model(class_name_or_iri, context_iri_or_payload, self, iri_generator=iri_generator,
                                         iri_prefix=iri_prefix, iri_fragment=iri_fragment,
                                         incremental_iri=incremental_iri,
                                         context_file_path=context_file_path)

    def _get_first_resource_found(self, store_session):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot get a resource at random."
                                                     % self.__class__.__name__)

    def _get_by_iri(self, id, store_session):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot get a resource from its IRI."
                                                     % self.__class__.__name__)

    def _filter(self, store_session, type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs):
        raise UnsupportedDataStorageFeatureException("This datastore %s does not support filtering queries."
                                                     % self.__class__.__name__)

    def _flush(self, resources_to_update, resources_to_delete):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot update resources (read-only)."
                                                     % self.__class__.__name__)

    def _new_resource_object(self, id, resource_graph, session):

        resource = StoreResource.load_from_graph(self._model_manager, self, session, id, resource_graph, is_new=False)
        self.resource_cache.set_resource(resource)
        return resource

    def _select_resource_from_hashless_iri(self, hashless_iri, resources):
        if len(resources) == 0:
            raise OMObjectNotFoundError(u"No resource with hash-less iri %s" % hashless_iri)
        elif len(resources) > 1:
            for r in resources:
                if r.id.iri == hashless_iri:
                    return r
            # TODO: avoid such arbitrary selection
            self._logger.warn(u"Multiple resources have the same base_uri: %s\n. "
                              u"The first one is selected." % resources)
        return resources[0]

    def _create_iri_generator(self, class_name_or_iri):
        raise UnsupportedDataStorageFeatureException("This datastore %s does not create IRI generators."
                                                     % self.__class__.__name__)
