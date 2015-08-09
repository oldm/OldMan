from logging import getLogger
from oldman.resource.client import ClientResource
from oldman.session.session import Session


class DefaultSession(Session):
    """TODO: find a better name """

    def __init__(self, session_mediator):
        self._logger = getLogger(__name__)

        self._mediator = session_mediator

        #TODO: consider using an external cache, like for store resources.
        self._updated_iris = {}

        # Naive
        self._resources = set()

    def new(self, iri=None, types=None, hashless_iri=None, collection_iri=None, **kwargs):
        """
            TODO: point this comment to the definition.
        """
        if (types is None or len(types) == 0) and len(kwargs) == 0:
            name = iri if iri is not None else ""
            self._logger.info(u"""New resource %s has no type nor attribute.
            As such, nothing is stored in the data graph.""" % name)

        resource = ClientResource(self._mediator.model_manager, self, iri=iri, types=types, hashless_iri=hashless_iri,
                                  collection_iri=collection_iri, **kwargs)
        self._resources.add(resource)
        return resource

    def get(self, iri=None, types=None, hashless_iri=None, eager_with_reversed_attributes=True, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.get`."""
        #TODO: consider parallelism
        store_resources = [store.get(iri=iri, types=types, hashless_iri=hashless_iri,
                                     eager_with_reversed_attributes=eager_with_reversed_attributes, **kwargs)
                           for store in self._mediator.store_selector.select_stores(iri=iri, types=types,
                                                                                    hashless_iri=hashless_iri,
                                                                                    **kwargs)]
        returned_store_resources = filter(lambda x: x, store_resources)
        resources = self._mediator.conversion_manager.convert_store_to_client_resources(returned_store_resources,
                                                                                        self._mediator.model_manager,
                                                                                        self)
        resource_count = len(resources)
        if resource_count == 1:
            resource = resources[0]
            self._resources.add(resource)
            return resource

        elif resource_count == 0:
            return None
        #TODO: find a better exception and explain better
        #TODO: see if relevant
        raise Exception("Non unique object")

    def filter(self, types=None, hashless_iri=None, limit=None, eager=False, pre_cache_properties=None, **kwargs):
        """See :func:`oldman.store.datastore.DataStore.filter`."""
        #TODO: support again generator. Find a way to aggregate them.
        store_resources = [r for store in self._mediator.store_selector.select_stores(types=types,
                                                                                      hashless_iri=hashless_iri,
                                                                                      pre_cache_properties=pre_cache_properties,
                                                                                      **kwargs)
                           for r in store.filter(types=types, hashless_iri=hashless_iri, limit=limit, eager=eager,
                                                 pre_cache_properties=pre_cache_properties, **kwargs)]
        client_resources = self._mediator.conversion_manager.convert_store_to_client_resources(store_resources,
                                                                                               self._mediator.model_manager,
                                                                                               self)
        self._resources.update(client_resources)
        return client_resources

    def sparql_filter(self, query):
        """See :func:`oldman.store.datastore.DataStore.sparql_filter`."""
        #TODO: support again generator. Find a way to aggregate them.
        store_resources = [r for store in self._mediator.store_selector.select_sparql_stores(query)
                           for r in store.sparql_filter(query)]
        client_resources = self._mediator.conversion_manager.convert_store_to_client_resources(store_resources,
                                                                                               self._mediator.model_manager,
                                                                                               self)
        self._resources.update(client_resources)
        return client_resources

    def commit(self, is_end_user=True):
        """TODO: describe.

           TODO: re-implement it, very naive
         """
        for resource in self._resources:
            self._save_resource(resource, is_end_user)

    def close(self):
        """TODO: implement it """
        pass

    def _save_resource(self, client_resource, is_end_user):
        """TODO: refactor"""
        store = self._mediator.store_selector.select_store(client_resource, types=client_resource.types)
        store_resource = self._mediator.conversion_manager.convert_client_to_store_resource(client_resource, store)
        store_resource.save(is_end_user)
        previous_id = client_resource.id
        new_id = store_resource.id

        # Keeps track of the temporary IRI replacement
        # TODO: remove this!
        if previous_id != new_id:
            self._updated_iris[previous_id] = new_id
        client_resource.receive_id(new_id)

    def _delete_resource(self, client_resource):
        """TODO: refactor"""
        store = self._mediator.store_selector.select_store(client_resource, types=client_resource.types)
        store_resource = self._mediator.conversion_manager.convert_client_to_store_resource(client_resource, store)
        store_resource.delete()

    def get_updated_iri(self, tmp_iri):
        """TODO: remove it """
        return self._updated_iris.get(tmp_iri, tmp_iri)
