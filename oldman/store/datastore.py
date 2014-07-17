import logging

from oldman.store.cache import ResourceCache
from oldman.exception import UnsupportedDataStorageFeatureException, OMAttributeAccessError
from oldman.exception import OMObjectNotFoundError, OMClassInstanceError
from oldman.resource import Resource


class DataStore(object):
    """A :class:`~oldman.store.datastore.DataStore` object manages CRUD operations on
    :class:`~oldman.resource.Resource` objects.

    In the future, non-CRUD operations may also be supported.

    Manages the cache (:class:`~oldman.management.cache.ResourceCache` object) of
    :class:`~oldman.resource.Resource` object.

    A :class:`~oldman.management.manager.ResourceManager` object must be assigned
    after instantiation of this object.

    :param cache_region: :class:`dogpile.cache.region.CacheRegion` object.
                         This object must already be configured.
                         Defaults to None (no cache).
                         See :class:`~oldman.store.cache.ResourceCache` for further details.
    """

    def __init__(self, cache_region=None):
        self._manager = None
        self._logger = logging.getLogger(__name__)
        self._resource_cache = ResourceCache(cache_region)

    @property
    def manager(self):
        """The :class:`~oldman.management.manager.ResourceManager` object.

        Necessary for creating new :class:`~oldman.resource.Resource` objects
        and accessing to :class:`~oldman.model.Model` objects.
        """
        return self._manager

    @manager.setter
    def manager(self, resource_manager):
        """ Must be called after instantiation. """
        self._manager = resource_manager

    @property
    def resource_cache(self):
        """:class:`~oldman.management.cache.ResourceCache` object."""
        return self._resource_cache

    def get(self, id=None, types=None, hashless_iri=None, **kwargs):
        """Gets the first :class:`~oldman.resource.Resource` object matching the given criteria.

        The `kwargs` dict can contains regular attribute key-values.

        When `id` is given, types are then checked. An :exc:`~oldman.exception.OMClassInstanceError`
        is raised if the resource is not instance of these classes.
        **Other criteria are not checked**.

        :param id: IRI of the resource. Defaults to `None`.
        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :return: A :class:`~oldman.resource.Resource` object or `None` if no resource has been found.
        """
        types = set(types) if types is not None else set()

        if id is not None:
            resource = self._get_by_id(id)
            if not types.issubset(resource.types):
                missing_types = types.difference(resource.types)
                raise OMClassInstanceError(u"%s found, but is not instance of %s" % (id, missing_types))
            if len(kwargs) > 0:
                self._logger.warn(u"get(): id given so attributes %s are just ignored" % kwargs.keys())
            return resource

        elif hashless_iri is None and len(kwargs) == 0:
            return self._get_first_resource_found()

        elif hashless_iri is not None:
            resources = self.filter(types=types, hashless_iri=hashless_iri, **kwargs)
            return self._select_resource_from_hashless_iri(hashless_iri, list(resources))

        # First found
        resources = self.filter(types=types, hashless_iri=hashless_iri, limit=1, **kwargs)
        for resource in resources:
            return resource

        return None

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """Finds the :class:`~oldman.resource.Resource` objects matching the given criteria.

        The `kwargs` dict can contains:

           1. regular attribute key-values ;
           2. the special attribute `id`. If given, :func:`~oldman.store.datastore.DataStore.get` is called.

        :param types: IRIs of the RDFS classes filtered resources must be instance of. Defaults to `None`.
        :param hashless_iri: Hash-less IRI of filtered resources. Defaults to `None`.
        :param limit: Upper bound on the number of solutions returned (e.g. SPARQL LIMIT). Positive integer.
                      Defaults to `None`.
        :param eager: If `True` loads all the Resource objects within the minimum number of queries
                      (e.g. one single SPARQL query). Defaults to `False` (lazy).
        :param pre_cache_properties: List of RDF ObjectProperties to pre-cache eagerly.
                      Their values (:class:`~oldman.resource.Resource` objects) are loaded and
                      added to the cache. Defaults to `[]`. If given, `eager` must be `True`.
                      Disabled if there is no cache.
        :return: A generator (if lazy) or a list (if eager) of :class:`~oldman.resource.Resource` objects.
        """
        if not eager and pre_cache_properties is not None:
            raise AttributeError(u"Eager properties are incompatible with lazyness. Please set eager to True.")

        id = kwargs.pop("id") if "id" in kwargs else None
        type_iris = types if types is not None else []
        if id is not None:
            return self.get(id=id, types=types, hashless_iri=hashless_iri, **kwargs)

        if len(type_iris) == 0 and len(kwargs) > 0:
            raise OMAttributeAccessError(u"No type given in filter() so attributes %s are ambiguous."
                                         % kwargs.keys())

        return self._filter(type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs)

    def sparql_filter(self, query):
        """Finds the :class:`~oldman.resource.Resource` objects matching a given query.

        Raises an :class:`~oldman.exception.UnsupportedDataStorageFeatureException` exception
        if the SPARQL protocol is not supported by the concrete data_store.

        :param query: SPARQL SELECT query where the first variable assigned
                      corresponds to the IRIs of the resources that will be returned.
        :return: A generator of :class:`~oldman.resource.Resource` objects.
"""
        raise UnsupportedDataStorageFeatureException("This datastore %s does not support the SPARQL protocol."
                                            % self.__class__.__name__)

    def save(self, resource, attributes, former_types):
        """End-users should not call it directly. Call :func:`oldman.Resource.save()` instead.

        :param resource: :class:`~oldman.resource.Resource` object.
        :param attributes: Ordered list of :class:`~oldman.attribute.OMAttribute` objects.
        :param former_types: List of RDFS class IRIs previously saved.
        """
        self._save_resource_attributes(resource, attributes, former_types)
        # Cache
        self._resource_cache.set_resource(resource)

    def delete(self, resource, attributes, former_types):
        """End-users should not call it directly. Call :func:`oldman.Resource.delete()` instead.

        :param resource: :class:`~oldman.resource.Resource` object.
        :param attributes: Ordered list of :class:`~oldman.attribute.OMAttribute` objects.
        :param former_types: List of RDFS class IRIs previously saved.
        """
        self._save_resource_attributes(resource, attributes, former_types)
        # Cache
        self._resource_cache.remove_resource(resource)

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

    def _get_first_resource_found(self):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot get a resource at random."
                                                     % self.__class__.__name__)

    def _get_by_id(self, id):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot get a resource from its IRI."
                                                     % self.__class__.__name__)

    def _filter(self, type_iris, hashless_iri, limit, eager, pre_cache_properties, **kwargs):
        raise UnsupportedDataStorageFeatureException("This datastore %s does not support filtering queries."
                                                     % self.__class__.__name__)

    def _save_resource_attributes(self, resource, attributes):
        raise UnsupportedDataStorageFeatureException("This datastore %s cannot update resources (read-only)."
                                                     % self.__class__.__name__)

    def _new_resource_object(self, id, resource_graph):
        resource = Resource.load_from_graph(self._manager, id, resource_graph, is_new=(len(resource_graph) == 0))
        self.resource_cache.set_resource(resource)
        return resource

    def _select_resource_from_hashless_iri(self, hashless_iri, resources):
        if len(resources) == 0:
            raise OMObjectNotFoundError(u"No resource with hash-less iri %s" % hashless_iri)
        elif len(resources) > 1:
            for r in resources:
                if r.id == hashless_iri:
                    return r
            # TODO: avoid such arbitrary selection
            self._logger.warn(u"Multiple resources have the same base_uri: %s\n. "
                              u"The first one is selected." % resources)
        return resources[0]