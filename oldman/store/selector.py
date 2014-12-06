

class DataStoreSelector:
    """TODO: continue"""

    def __init__(self, data_stores):
        if (data_stores is None) or (isinstance(data_stores, (list, set)) and len(data_stores) == 0):
            #TODO: find a better type of exception
            raise Exception("At least one data store must be given.")

        self._data_stores = list(data_stores) if isinstance(data_stores, (list, set)) else [data_stores]
        #TODO: remove
        if len(self._data_stores) > 1:
            raise NotImplementedError("Multiple data stores are not yet supported.")

    @property
    def data_stores(self):
        return self._data_stores

    def select_stores(self, id=None, **kwargs):
        #TODO: implement seriously
        return self._data_stores

    def select_store(self, **kwargs):
        """TODO: what is the correct behavior when multiple stores are returned? """
        return self.select_stores(**kwargs)[0]

    def select_sparql_stores(self, query):
        #TODO: look at the query for filtering
        return filter(lambda s: s.support_sparql_filtering(), self._data_stores)
