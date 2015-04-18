from logging import getLogger

from rdflib.plugin import PluginException
import requests
from rdflib import Graph
from oldman.model.manager.store import StoreModelManager

from oldman.store.store import Store
from oldman.rest.crud import JSON_TYPES


class HttpStore(Store):
    """
        Read only. No search feature.
    """

    def __init__(self, schema_graph=None, cache_region=None, session=None):
        Store.__init__(self, StoreModelManager(schema_graph=schema_graph), cache_region)
        self._session = session if session is not None else requests.session()
        self._logger = getLogger(__name__)

    @property
    def session(self):
        return self._session

    def _get_by_iri(self, iri):
        r = self._session.get(iri, headers=dict(Accept='text/turtle;q=1.0, '
                                                      'application/rdf+xml;q=1.0, '
                                                      'application/ld+json;q=.0.8, '
                                                      'application/json;q=0.1'))
        if r.status_code != 200:
            self._logger.warn("Resource %s not retrieved (Status code: %d)." % (iri, r.status_code))
            return None

        hashless_iri = iri.split('#')[0]
        content_type = r.headers.get('content-type')

        if content_type is None:
            self._logger.warn("No content-type returned for the resource %s." % iri)
            return None
        elif content_type in JSON_TYPES:
            ctx_header = r.links.get("http://www.w3.org/ns/json-ld#context")
            if ctx_header is None:
                self._logger.warn("No context header given with the JSON representation of %s." % iri)
                return None

            ctx_url = ctx_header["url"]
            resource_graph = Graph().parse(data=r.content, context=ctx_url, publicID=hashless_iri,
                                           format=content_type)
        else:
            try:
                resource_graph = Graph().parse(data=r.content, publicID=hashless_iri,
                                               format=content_type)
            except PluginException:
                self._logger.warn("Content-type %s is not supported. Impossible to get %s." % (content_type, iri))
                return None

        return self._new_resource_object(iri, resource_graph)