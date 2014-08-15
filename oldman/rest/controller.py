from rdflib import Graph
from .crud import HashLessCRUDer
from oldman.vocabulary import HTTP_POST

class HTTPController(object):
    """
    HTTP.

    TODO: check declared methods (only GET and HEAD are implicit).
    """

    DEFAULT_CONFIG = {'allow_put_new_type_existing_resource': False,
                      'allow_put_remove_type_existing_resource': False,
                      'allow_put_new_resource': True
                      }

    def __init__(self, manager, post_operations=None, config={}):
        self._manager = manager

        # For operations except POST
        self._cruder = HashLessCRUDer(manager)

        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)
        self._post_operations = post_operations if post_operations is not None else {}

    def get(self, hashless_iri, content_type, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        return self._cruder.get(hashless_iri, content_type)

    def head(self, hashless_iri, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        #TODO: consider a more efficient implementation
        self._cruder.get(hashless_iri, None)

    def post(self, hashless_iri, content_type, payload, **kwargs):
        """
            TODO: categorize the resource to decide what to do.

            Support declaration and implementaion are required.

        """
        # Must be its ID (we do not consider resources with hash IRIs)
        resource = self._manager.get(id=hashless_iri)
        if resource is None:
            #TODO: better exception
            raise Exception("No such resource")

        operation = resource.get_operation(HTTP_POST)
        if operation is not None:

            graph = Graph()
            if content_type in _JSON_TYPES:
                resource = self._manager.get(hashless_iri=hashless_iri)
                graph.parse(data=document_content, format="json-ld", publicID=hashless_iri,
                        context=resource.context)
            else:
                graph.parse(data=document_content, format=content_type, publicID=hashless_iri)


            #TODO: add arguments
            return operation(resource, graph=graph, content_type=content_type)

        #TODO: find an appriopriate exception. If error code is 405, alternatives must be given.
        raise Exception("POST method is not supported")

    def put(self, hashless_iri, content_type, payload, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        return self._cruder.update(self, hashless_iri, payload, content_type,
                                   allow_new_type=False, allow_type_removal=False,
                                   allow_put_new_resource=True)

    def delete(self, hashless_iri, **kwargs):
        """
            TODO: describe.

            No declaration required.
        """
        self._cruder.delete(hashless_iri)

    def options(self, hashless_iri, **kwargs):
        raise NotImplementedError("TODO: implement it")

    def patch(self, hashless_iri, content_type, payload, **kwargs):
        raise NotImplementedError("TODO: implement it")