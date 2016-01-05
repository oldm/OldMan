from logging import getLogger

from rdflib import Graph
from rdflib.plugin import PluginException, plugins
from rdflib.serializer import Serializer
from negotiator import ContentNegotiator, ContentType, AcceptParameters

from .crud import HashLessCRUDer, JSON_TYPES
from oldman.core.vocabulary import HTTP_POST
from oldman.core.exception import OMResourceNotFoundException, OMNotAcceptableException
from oldman.core.exception import OMMethodNotAllowedException, OMBadRequestException, OMObjectNotFoundError


class HTTPController(object):
    """
    HTTP.

    TODO: check declared methods (only GET and HEAD are implicit).
    """

    DEFAULT_CONFIG = {'allow_put_new_type_existing_resource': False,
                      'allow_put_remove_type_existing_resource': False,
                      'allow_put_new_resource': True
                      }

    def __init__(self, user_mediator, config={}):
        self._logger = getLogger(__name__)
        self._user_mediator = user_mediator

        # For operations except POST
        self._cruder = HashLessCRUDer(user_mediator)

        self._config = self.DEFAULT_CONFIG.copy()
        self._config.update(config)

        self._negotiator = None
        self._init_content_negotiator()

    def _init_content_negotiator(self):
        #TODO: use config instead
        default_content_type = "application/ld+json"
        default_accept_params = AcceptParameters(ContentType(default_content_type))
        # rdf types
        rdf_types = set([plugin.name for plugin in plugins(kind=Serializer) if "/" in plugin.name])

        #Blacklisted because mapped to TriX that requires a context-aware store
        blacklisted_types = ["application/xml"]

        #TODO: consider other types
        accepted_types = list(rdf_types.difference(blacklisted_types)) + ["application/json"]
        self._logger.debug("Accepted types: %s" % accepted_types)
        acceptable_params = [default_accept_params] + [AcceptParameters(ContentType(ct)) for ct in accepted_types]

        self._negotiator = ContentNegotiator(default_accept_params, acceptable_params)

    def get(self, hashless_iri, accept_header="*/*", **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        self._logger.debug("Accept header: %s" % accept_header)
        accepted_type = self._negotiator.negotiate(accept=accept_header)
        if accepted_type is None:
            raise OMNotAcceptableException()

        content_type = str(accepted_type.content_type)
        self._logger.debug("Selected content-type: %s" % content_type)

        try:
            return self._cruder.get(hashless_iri, content_type)
        except OMObjectNotFoundError:
            raise OMResourceNotFoundException()

    def head(self, hashless_iri, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        #TODO: consider a more efficient implementation
        try:
            self._cruder.get(hashless_iri, None)
        except OMObjectNotFoundError:
            raise OMResourceNotFoundException()

    def post(self, hashless_iri, content_type=None, payload=None, **kwargs):
        """
            TODO: categorize the resource to decide what to do.

            Support declaration and implementation are required.

        """
        if content_type is None:
            raise OMBadRequestException("Content type is required.")
        #if payload is None:
        #    raise BadRequestException("No payload given.")

        # Must be its ID (we do not consider resources with hash IRIs)
        session = self._user_mediator.create_session()
        resource = session.get(iri=hashless_iri)
        if resource is None:
            raise OMResourceNotFoundException()

        operation = resource.get_operation(HTTP_POST)
        if operation is not None:

            graph = Graph()
            try:
                if content_type in JSON_TYPES:
                    resource = session.first(hashless_iri=hashless_iri)
                    graph.parse(data=payload, format="json-ld", publicID=hashless_iri,
                                context=resource.context.value_to_load)
                else:
                    graph.parse(data=payload, format=content_type, publicID=hashless_iri)
            except PluginException:
                raise OMNotAcceptableException()

            #TODO: add arguments
            result = operation(resource, graph=graph, content_type=content_type)
            session.close()
            return result

        #TODO: When error code is 405, alternatives must be given.
        raise OMMethodNotAllowedException()

    def put(self, hashless_iri, content_type=None, payload=None, **kwargs):
        """
            TODO: describe.

            No support declaration required.
        """
        if content_type is None:
            raise OMBadRequestException("Content type is required.")
        if payload is None:
            raise OMBadRequestException("No payload given.")
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
            raise OMBadRequestException("Content type is required.")
        if payload is None:
            raise OMBadRequestException("No payload given.")
        raise NotImplementedError("PATCH is not yet supported.")