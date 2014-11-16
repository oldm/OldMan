from rdflib import Namespace, URIRef

from oldman.model.property import OMProperty


class OMPropertyExtractor(object):
    """An :class:`~oldman.parsing.schema.property.OMPropertyExtractor` object generates
    and updates :class:`~oldman.property.OMProperty` objects from the schema RDF graph.

    This class is generic and must derived for supporting various RDF vocabularies.
    """

    def update(self, om_properties, class_iri, type_iris, schema_graph):
        """Generates new :class:`~oldman.property.OMProperty` objects or updates them
        from the schema graph.

        :param om_properties: `dict` of :class:`~oldman.property.OMProperty` objects indexed
                              by their IRIs and their reverse status.
        :param class_iri: IRI of RDFS class of the future :class:`~oldman.model.Model` object.
        :param type_iris: Ancestry of the RDFS class.
        :param schema_graph: :class:`rdflib.graph.Graph` object.
        :return: Updated `dict` :class:`~oldman.property.OMProperty` objects.
        """
        raise NotImplementedError()


class HydraPropertyExtractor(OMPropertyExtractor):
    """:class:`~oldman.parsing.schema.property.OMPropertyExtractor` objects
    that support the `Hydra vocabulary <http://www.markus-lanthaler.com/hydra/spec/latest/core/>`_.

    Currently, this class supports:
        - `hydra:required <http://www.markus-lanthaler.com/hydra/spec/latest/core/#hydra:required>`_ ;
        - `hydra:readonly <http://www.markus-lanthaler.com/hydra/spec/latest/core/#hydra:readonly>`_;
        - `hydra:writeonly <http://www.markus-lanthaler.com/hydra/spec/latest/core/#hydra:writeonly>`_ .
    """

    _extract_hydra_properties = u"""
        SELECT ?p ?required ?readonly ?writeonly ?reversed
        WHERE {
            ?class_iri hydra:supportedProperty ?sp.
            ?sp hydra:property ?p.
            OPTIONAL {
                ?sp hydra:required ?required
            } .
            OPTIONAL {
                ?sp hydra:readonly ?readonly
            } .
            OPTIONAL {
                ?sp hydra:writeonly ?writeonly
            } .
            OPTIONAL {
                ?sp hydra:reversed ?reversed
            } .
        }
    """
    _ns = {u'hydra': Namespace(u"http://www.w3.org/ns/hydra/core#")}

    def update(self, om_properties, class_iri, type_iris, schema_graph):
        """See :func:`oldman.parsing.schema.property.OMPropertyExtractor.update`."""
        prop_params = {}

        for type_uri in type_iris:
            results = schema_graph.query(self._extract_hydra_properties, initNs=self._ns,
                                         initBindings={u'class_iri': URIRef(type_uri)})
            for property_iri, is_req, ro, wo, rev in results:
                reversed = bool(rev)
                prop_uri = property_iri.toPython()
                # Booleans are false by default
                is_required, read_only, write_only = prop_params.get((prop_uri, reversed), (False, False, False))

                # Updates these booleans
                is_required = is_required or (is_req is not None and bool(is_req.toPython()))
                read_only = read_only or (ro is not None and bool(ro.toPython()))
                write_only = write_only or (wo is not None and bool(wo.toPython()))
                prop_params[(prop_uri, reversed)] = (is_required, read_only, write_only)

        for (property_iri, reversed), (is_required, read_only, write_only) in prop_params.iteritems():
            if not (property_iri, reversed) in om_properties:
                om_property = OMProperty(property_iri, class_iri, is_required=is_required,
                                         read_only=read_only, write_only=write_only, reversed=reversed)
                om_properties[(property_iri, reversed)] = om_property
        return om_properties