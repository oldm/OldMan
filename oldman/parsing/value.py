import logging
from rdflib import URIRef, Literal
from rdflib.collection import Collection
from oldman.exception import OMDataStoreError


class AttributeValueExtractorFromGraph(object):

    def __init__(self, attribute):
        self._logger = logging.getLogger(__name__)
        self._attribute = attribute
        self._language = attribute.language
        self._value_format = attribute.value_format
        self._property_uri = URIRef(attribute.om_property.iri)
        self._container = attribute.container
        try:
            self._extract_fct = AttributeValueExtractorFromGraph.extract_fcts[self._container]
        except KeyError as e:
            raise NotImplementedError("Container %s is not supported" % e)

    def extract_values(self, instance, subgraph):
        instance_uri = URIRef(instance.id)
        raw_rdf_values = list(subgraph.objects(instance_uri, self._property_uri))
        if len(raw_rdf_values) == 0:
            return None
        return self._extract_fct(self, raw_rdf_values, graph=subgraph)

    def _extract_regular_values(self, raw_rdf_values, is_set=False, **kwargs):
        values = self._filter_and_convert(raw_rdf_values)
        length = len(values)
        if length == 0:
            return None
        if not is_set and length == 1:
            return values[0]
        return set(values)

    def _extract_set_values(self, raw_rdf_values, **kwargs):
        return self._extract_regular_values(raw_rdf_values, is_set=True, **kwargs)

    def _extract_list_values(self, raw_rdf_values, graph):
        """
            Filters by language (unique way to discriminate)
        """
        if not self._language and len(raw_rdf_values) > 1:
            raise OMDataStoreError(u"Multiple list found for the property %s"
                                   % self._property_uri)
        final_list = None
        for vlist in raw_rdf_values:
            rdf_values = Collection(graph, vlist)
            values = self._filter_and_convert(rdf_values)
            if len(values) > 0:
                if final_list is not None:
                    raise OMDataStoreError(u"Same language in multiple list for the property %s"
                                           % self._property_uri)
                final_list = values
            else:
                self._logger.debug("Void list %s in graph %s"
                                   % (final_list, graph.serialize(format="turtle")))
        return final_list

    def _extract_language_map_values(self, raw_rdf_values, **kwargs):
        return {r.language: self._value_format.to_python(r) for r in raw_rdf_values}

    def _filter_and_convert(self, rdf_values):
        """
            Filters if language is specified
        """
        if self._language:
            rdf_values = [r for r in rdf_values if isinstance(r, Literal)
                          and r.language == self._language]

        return [self._value_format.to_python(r) for r in rdf_values]

    extract_fcts = {'@list': _extract_list_values,
                    '@set': _extract_set_values,
                    '@language': _extract_language_map_values,
                    #TODO: support index maps
                    None: _extract_regular_values}
