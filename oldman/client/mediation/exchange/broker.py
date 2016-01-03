class Broker(object):
    """
    Low-level

    TODO: find a better name """

    def get(self, client_tracker, resource_factory, iri, types=None, eager_with_reversed_attributes=True):
        """TODO: explain

            :return a ClientResource
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def filter(self, resource_tracker, resource_factory, types=None, hashless_iri=None, limit=None, eager=False,
               pre_cache_properties=None, **kwargs):
        """TODO: explain

            :return list of ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def first(self, resource_finder, resource_factory, types=None, hashless_iri=None, pre_cache_properties=None,
              eager_with_reversed_attributes=True, **kwargs):
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def sparql_filter(self, resource_finder, resource_factory, query):
        """TODO: explain

            :return list of ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

    def flush(self, resource_factory, client_resources_to_update, client_resources_to_delete, is_end_user):
        """TODO: explain

            :return list of the updated ClientResource ?
        """
        raise NotImplementedError("Should be implemented by a concrete implementation.")

