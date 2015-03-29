

class StoreSelector:
    """TODO: continue"""

    def __init__(self, stores):
        if (stores is None) or (isinstance(stores, (list, set)) and len(stores) == 0):
            #TODO: find a better type of exception
            raise Exception("At least one data store must be given.")

        self._stores = list(stores) if isinstance(stores, (list, set)) else [stores]
        #TODO: remove
        if len(self._stores) > 1:
            raise NotImplementedError("Multiple data stores are not yet supported.")

    @property
    def stores(self):
        return self._stores

    def select_stores(self, id=None, **kwargs):
        #TODO: implement seriously
        return self._stores

    def select_store(self, **kwargs):
        """TODO: what is the correct behavior when multiple stores are returned? """
        return self.select_stores(**kwargs)[0]

    def select_sparql_stores(self, query):
        #TODO: look at the query for filtering
        return filter(lambda s: s.support_sparql_filtering(), self._stores)
