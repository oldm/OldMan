

class StoreSelector:
    """TODO: implement seriously"""

    def __init__(self):
        self._store_proxies = set([])

    def select_stores(self, id=None, **kwargs):
        #TODO: implement seriously
        return list(self._store_proxies)

    def bind_store(self, store_proxy, model):
        #TODO: implement seriously
        if len(self._store_proxies) == 0:
            self._store_proxies.add(store_proxy)
        elif store_proxy not in self._store_proxies:
            raise NotImplementedError("TODO: multiple stores are not yet supported")

    def select_store(self, client_resource, **kwargs):
        """TODO: what is the correct behavior when multiple stores are returned? """
        return self.select_stores(**kwargs)[0]

    def select_sparql_stores(self, query):
        #TODO: look at the query for filtering
        return filter(lambda s: s.support_sparql_filtering(), self._store_proxies)
