from logging import getLogger
from oldman.resource.factory import DefaultClientResourceFactory
from oldman.session.tracker import BasicSessionResourceTracker
from oldman.session.session import Session


class DefaultSession(Session):
    """TODO: find a better name """

    def __init__(self, model_manager, store_proxy):
        self._logger = getLogger(__name__)

        self._model_manager = model_manager
        self._store_proxy = store_proxy

        self._tracker = BasicSessionResourceTracker()
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

    def get(self, iri=None, types=None, hashless_iri=None, eager_with_reversed_attributes=True, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.get`."""
        # Looks first to the local resources
        # TODO: extend it to other criteria than iri?
        if iri is not None:
            local_resource = self._tracker.find(iri)
            if local_resource is not None:
                return local_resource

        # If not found locally, queries the stores
        resource = self._store_proxy.get(self._resource_factory, iri=iri, types=types, hashless_iri=hashless_iri,
                                         eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)
        if resource is not None:
            self._tracker.add(resource)
        return resource

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.filter`."""
        client_resources = self._store_proxy.filter(self._resource_factory, types=types, hashless_iri=hashless_iri,
                                                    pre_cache_properties=pre_cache_properties, **kwargs)
        self._tracker.add_all(client_resources)
        return client_resources

    def sparql_filter(self, query):
        """See :func:`oldman.store.datastore.DataStore.sparql_filter`."""
        client_resources = self._store_proxy.sparql_filter(self._resource_factory, query)
        self._tracker.add_all(client_resources)
        return client_resources

    def delete(self, client_resource):
        """TODO: describe.

            Wait for the next commit() to remove the resource
            from the store.
        """
        self._tracker.mark_to_delete(client_resource)

    def commit(self, is_end_user=True):
        """TODO: describe.

           TODO: re-implement it, very naive
         """
        new_resources = self._store_proxy.submit(self._resource_factory, self._tracker.modified_resources,
                                                 self._tracker.resources_to_delete, is_end_user)
        self._tracker.add_all(new_resources)
        self._tracker.forget_resources_to_delete()

    def close(self):
        """TODO: implement it """
        pass

    def get_updated_iri(self, tmp_iri):
        """TODO: remove it """
        return self._updated_iris.get(tmp_iri, tmp_iri)
