from logging import getLogger
from oldman.resource.factory import DefaultClientResourceFactory
from oldman.session.tracker import BasicResourceTracker
from oldman.session.session import Session


class DefaultSession(Session):
    """TODO: find a better name """

    def __init__(self, model_manager, store_proxy):
        self._logger = getLogger(__name__)

        self._model_manager = model_manager
        self._store_proxy = store_proxy

        self._tracker = BasicResourceTracker()
        self._resource_factory = DefaultClientResourceFactory(model_manager, self)

        # TODO: remove it
        self._updated_iris = {}

    def new(self, iri=None, types=None, hashless_iri=None, collection_iri=None, **kwargs):
        """
            TODO: explain
        """
        if (types is None or len(types) == 0) and len(kwargs) == 0:
            name = iri if iri is not None else ""
            self._logger.info(u"""New resource %s has no type nor attribute.
            As such, nothing is stored in the data graph.""" % name)

        resource = self._resource_factory.new_resource(iri=iri, types=types, hashless_iri=hashless_iri,
                                                       collection_iri=collection_iri, **kwargs)
        self._tracker.add(resource)
        return resource

    def get(self, iri, types=None, eager_with_reversed_attributes=True):
        """See :func:`oldman.store.datastore.DataStore.get`."""
        if iri is None:
            raise ValueError("iri is required")

        # Looks first to the local resources
        local_resource = self._tracker.find(iri)
        if local_resource is not None:
            return local_resource

        # If not found locally, queries the stores
        resource = self._store_proxy.get(self._tracker, self._resource_factory, iri, types=types)
        if resource is not None:
            self._tracker.add(resource)
        return resource

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        client_resources = self._store_proxy.filter(self._tracker, self._resource_factory, types=types,
                                                    hashless_iri=hashless_iri, limit=limit, eager=eager,
                                                    pre_cache_properties=pre_cache_properties, **kwargs)
        self._tracker.add_all(client_resources)
        return client_resources

    def first(self, types=None, hashless_iri=None, eager_with_reversed_attributes=True,
              pre_cache_properties=None, **kwargs):
        client_resource = self._store_proxy.first(self._tracker, self._resource_factory, types=types,
                                                  hashless_iri=hashless_iri, pre_cache_properties=pre_cache_properties,
                                                  eager_with_reversed_attributes=eager_with_reversed_attributes,
                                                  **kwargs)
        if client_resource is not None:
            self._tracker.add(client_resource)
        return client_resource

    def sparql_filter(self, query):
        """See :func:`oldman.store.store.Store.sparql_filter`."""
        client_resources = self._store_proxy.sparql_filter(self._tracker, self._resource_factory, query)
        self._tracker.add_all(client_resources)
        return client_resources

    def delete(self, client_resource):
        """TODO: describe.

            Wait for the next flush() to remove the resource
            from the store.
        """
        self._tracker.mark_to_delete(client_resource)

    def flush(self, is_end_user=True):
        """TODO: describe.

           TODO: re-implement it, very naive
         """
        new_resources = self._store_proxy.flush(self._resource_factory, self._tracker.modified_resources,
                                                self._tracker.resources_to_delete, is_end_user)
        self._tracker.add_all(new_resources)
        self._tracker.forget_resources_to_delete()

    def close(self):
        """TODO: implement it """
        pass

    def receive_reference(self, reference, object_resource=None, object_iri=None):
        """ Not for end-users!"""
        self._tracker.receive_reference(reference, object_resource=object_resource, object_iri=object_iri)

    def receive_reference_removal_notification(self, reference):
        """ Not for end-users!"""
        self._tracker.receive_reference_removal_notification(reference)

    def get_updated_iri(self, tmp_iri):
        """TODO: remove it """
        return self._updated_iris.get(tmp_iri, tmp_iri)
