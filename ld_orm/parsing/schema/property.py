from rdflib import Graph, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from ld_orm.property import LDProperty


class LDPropertyExtractor(object):
    """
        Supported Property Extractor
    """

    def update(self, properties, class_uri, graph):
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
    EXTRACT_HYDRA_PROPERTIES = prepareQuery(
        """
        SELECT ?p ?required
        WHERE {
            ?class_uri hydra:supportedProperty ?sp.
            ?sp hydra:property ?p;
                hydra:required ?required.
        }
    """, initNs={'hydra': Namespace("http://www.w3.org/ns/hydra/core#") })

    def update(self, properties, class_uri, graph):
        """
            TODO: support read-only and write-only
            TODO: Support rdfs:range (optional)
        """
        results = graph.query(self.EXTRACT_HYDRA_PROPERTIES,
                              initBindings={'class_uri': URIRef(class_uri)})

        for property_uri, is_required in results:
            property_uri = str(property_uri)

            if not property_uri in properties:
                properties[property_uri]= LDProperty(property_uri, class_uri, is_required)
        return properties
