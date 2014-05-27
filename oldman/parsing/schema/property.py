from rdflib import Namespace, URIRef
from oldman.property import OMProperty


class OMPropertyExtractor(object):
    """
        Supported Property Extractor
    """

    def update(self, properties, class_iri, type_iris, graph, manager):
        """
            Updates metadata on RDF properties: {property_uri: Property.23}

            Returns updated properties
        """
        raise NotImplementedError()


class HydraPropertyExtractor(OMPropertyExtractor):
    """
        Extracts supported properties from Hydra RDF descriptions

        http://www.markus-lanthaler.com/hydra/spec/latest/core/

        Currently supported:
           - hydra:required
           - hydra:readOnly
           - hydra:writeOnly

        TODO: support
           - rdfs:range
    """

    extract_hydra_properties = u"""
        SELECT ?p ?required ?readOnly ?writeOnly
        WHERE {
            ?class_uri hydra:supportedProperty ?sp.
            ?sp hydra:property ?p.
            OPTIONAL {
                ?sp hydra:required ?required
            } .
            OPTIONAL {
                ?sp hydra:readonly ?readOnly
            } .
            OPTIONAL {
                ?sp hydra:writeonly ?writeOnly
            }
        }
    """
    ns = {u'hydra': Namespace(u"http://www.w3.org/ns/hydra/core#")}

    def update(self, properties, class_iri, type_iris, graph, manager):
        """
            TODO: Support rdfs:range (optional)
        """
        prop_params = {}

        for type_uri in type_iris:
            results = graph.query(self.extract_hydra_properties, initNs=self.ns,
                                  initBindings={u'class_uri': URIRef(type_uri)})
            for property_uri, is_req, ro, wo in results:
                prop_uri = property_uri.toPython()
                # Booleans are false by default
                is_required, read_only, write_only = prop_params.get(prop_uri, (False, False, False))

                # Updates these booleans
                is_required = is_required or (is_req is not None and bool(is_req.toPython()))
                read_only = read_only or (ro is not None and bool(ro.toPython()))
                write_only = write_only or (wo is not None and bool(wo.toPython()))
                prop_params[prop_uri] = (is_required, read_only, write_only)

        for property_uri, (is_required, read_only, write_only) in prop_params.iteritems():
            if not property_uri in properties:
                properties[property_uri] = OMProperty(manager, property_uri, class_iri, is_required=is_required,
                                                      read_only=read_only, write_only=write_only)
        return properties
