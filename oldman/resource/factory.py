from oldman.resource.client import ClientResource


class ClientResourceFactory(object):

    def new_resource(self, iri=None, hashless_iri=None, collection_iri=None, types=None,iri_fragment=None,
                     is_new=True, **kwargs):
        """TODO: describe """
        raise NotImplementedError("Should be implemented by a concrete implementation.")


class DefaultClientResourceFactory(ClientResourceFactory):

    def __init__(self, model_manager, session):
        self._model_manager = model_manager
        self._session = session

    def new_resource(self, iri=None, hashless_iri=None, collection_iri=None, types=None, iri_fragment=None,
                     is_new=True, **kwargs):
        return ClientResource(self._model_manager, self._session, iri=iri, types=types, hashless_iri=hashless_iri,
                              collection_iri=collection_iri, is_new=is_new, **kwargs)
