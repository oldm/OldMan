from rdflib import Graph
from .crud import HashLessCRUDer, JSON_TYPES
from oldman.vocabulary import HTTP_POST
from oldman.exception import OMResourceNotFoundException, OMForbiddenOperationException, OMRequiredAuthenticationException
from oldman.exception import OMMethodNotAllowedException, BadRequestException


class HTTPController(object):
    """
    HTTP.

    TODO: check declared methods (only GET and HEAD are implicit).
    """

    DEFAULT_CONFIG = {'allow_put_new_type_existing_resource': False,
                      'allow_put_remove_type_existing_resource': False,
                      'allow_put_new_resource': True
                      }

    def __init__(self, manager, config={}):
        self._manager = manager

        # For operations except POST
        self._cruder = HashLessCRUDer(manager)

        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)

    def get(self, hashless_iri, content_type=None, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        if content_type is None:
            raise BadRequestException("Content type is required")

        return self._cruder.get(hashless_iri, content_type)

    def head(self, hashless_iri, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        #TODO: consider a more efficient implementation
        self._cruder.get(hashless_iri, None)

    def post(self, hashless_iri, content_type=None, payload=None, **kwargs):
        """
            TODO: categorize the resource to decide what to do.

            Support declaration and implementaion are required.

        """
        if content_type is None:
            raise BadRequestException("Content type is required.")
        #if payload is None:
        #    raise BadRequestException("No payload given.")

        # Must be its ID (we do not consider resources with hash IRIs)
        resource = self._manager.get(id=hashless_iri)
        if resource is None:
            raise OMResourceNotFoundException()

        operation = resource.get_operation(HTTP_POST)
        if operation is not None:

            graph = Graph()
            if content_type in JSON_TYPES:
                resource = self._manager.get(hashless_iri=hashless_iri)
                graph.parse(data=payload, format="json-ld", publicID=hashless_iri,
                            context=resource.context)
            else:
                graph.parse(data=payload, format=content_type, publicID=hashless_iri)

            #TODO: add arguments
            return operation(resource, graph=graph, content_type=content_type)

        #TODO: When error code is 405, alternatives must be given.
        raise OMMethodNotAllowedException()

    def put(self, hashless_iri, content_type=None, payload=None, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        if content_type is None:
            raise BadRequestException("Content type is required.")
        if payload is None:
            raise BadRequestException("No payload given.")
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
        """ TODO: implement it """
        raise NotImplementedError("")

    def patch(self, hashless_iri, content_type=None, payload=None, **kwargs):
        """ TODO: implement it  """
        if content_type is None:
            raise BadRequestException("Content type is required.")
        if payload is None:
            raise BadRequestException("No payload given.")
        raise NotImplementedError("PATCH is not yet supported.")