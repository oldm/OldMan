from rdflib import Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from ld_orm.property import LDProperty


class LDPropertyExtractor(object):
    """
        Supported Property Extractor
    """

    def update(self, properties, type_uris, graph):
        """
            Updates metadata on RDF properties: {property_uri: Property.23}

            Returns updated properties
        """
        raise NotImplementedError()


class HydraPropertyExtractor(LDPropertyExtractor):
    """
        Extracts supported properties from Hydra RDF descriptions

        http://www.markus-lanthaler.com/hydra/spec/latest/core/

        Currently supported:
           - hydra:required

        TODO: support
           - hydra:readOnly
           - hydra:writeOnly
           - rdfs:range
    """

    # TODO: make hydra:required optional
    EXTRACT_HYDRA_PROPERTIES = prepareQuery(
        u"""
        SELECT ?p ?required
        WHERE {
            ?class_uri hydra:supportedProperty ?sp.
            ?sp hydra:property ?p;
                hydra:required ?required.
        }
    """, initNs={u'hydra': Namespace(u"http://www.w3.org/ns/hydra/core#")})

    def update(self, properties, class_uri, type_uris, graph):
        """
            TODO: support read-only and write-only
            TODO: Support rdfs:range (optional)
        """
        prop_results = {}
        for type_uri in type_uris:
            results = graph.query(self.EXTRACT_HYDRA_PROPERTIES, initBindings={u'class_uri': URIRef(type_uri)})
            for property_uri, is_req in results:
                prop_uri = property_uri.toPython()
                is_required = bool(is_req.toPython() or prop_results.get(prop_uri))
                prop_results[prop_uri] = is_required

        for property_uri, is_required in prop_results.iteritems():
            if not property_uri in properties:
                properties[property_uri] = LDProperty(property_uri, class_uri, is_required)
        return properties
