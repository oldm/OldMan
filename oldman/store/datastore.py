import logging
from oldman.management.cache import ResourceCache
from oldman.common import OBJECT_PROPERTY
from oldman.resource import is_blank_node


class DataStore(object):

    def __init__(self, cache_region=None):
        self._manager = None
        self._logger = logging.getLogger(__name__)
        self._resource_cache = ResourceCache(cache_region)

    @property
    def manager(self):
        return self._manager

    @manager.setter
    def manager(self, resource_manager):
        """ Please call it
        """
        self._manager = resource_manager

    @property
    def resource_cache(self):
        """:class:`~oldman.management.cache.ResourceCache` object."""
        return self._resource_cache

    def sparql_filter(self, query):
        """ Not supported by default
        """
        #TODO: change the exception
        raise NotImplementedError()

    def save(self, resource, attributes, former_types):
        """End-users should not call it directly. Call Resource.save() instead.

        TODO: update this comment
        Makes a SPARQL DELETE-INSERT request to save the changes into the `data_graph`.

        Deletes unaffected external resources, if the test :func:`~oldman.resource.should_delete_resource`
        is passed.

        :param attributes: ordered list of :class:`~oldman.attribute.OMAttribute` objects.
        """
        self._save_resource_attributes(resource, attributes, former_types)
        # Cache
        self._resource_cache.set_resource(resource)

    def delete(self, resource, attributes, former_types):
        self._save_resource_attributes(resource, attributes, former_types)
        # Cache
        self._resource_cache.remove_resource(resource)

    def _save_resource_attributes(self, resource, attributes):
        #TODO: raise another exception by default
        raise NotImplementedError("This method should be implemented by the concrete datastore")

    def exists(self, id):
        raise NotImplementedError("This method should be implemented by the concrete datastore")

    def generate_instance_number(self, class_iri):
        """ Needed for generating incremental IRIs
        """
        raise NotImplementedError("This method should be implemented by the concrete datastore")

    def reset_instance_counter(self, class_iri):
        """ Needed for generating incremental IRIs
        """
        raise NotImplementedError("This method should be implemented by the concrete datastore")

    def check_counter(self, class_iri):
        """ Needed for generating incremental IRIs
        """
        raise NotImplementedError("This method should be implemented by the concrete datastore")

