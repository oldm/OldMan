from uuid import uuid4

from rdflib import URIRef, RDF, RDFS

from oldman.core.vocabulary import OLDM_CORRESPONDING_CLASS


class HydraSchemaAdapter(object):
    """Updates some Hydra patterns in the schema graph:

          - hydra:Link: create a hydra:Class, subclass of the link range that support the same operations

    """

    def update_schema_graph(self, graph):
        graph = graph.skolemize()

        graph = self._update_links(graph)

        return graph

    @staticmethod
    def _update_links(graph):
        links = list(graph.subjects(RDF.type, URIRef(u"http://www.w3.org/ns/hydra/core#Link")))

        for link_property in links:
            new_class_iri = URIRef(u"http://localhost/.well-known/genid/link_class/%s" % uuid4())
            graph.add((new_class_iri, RDF.type, URIRef(u"http://www.w3.org/ns/hydra/core#Class")))
            graph.add((link_property, URIRef(OLDM_CORRESPONDING_CLASS), new_class_iri))

            # Ranges --> upper classes
            ranges = list(graph.objects(link_property, RDFS.range))
            for range in ranges:
                graph.add((new_class_iri, RDFS.subClassOf, range))

            # supported Operations
            supported_operation_property = URIRef(u"http://www.w3.org/ns/hydra/core#supportedOperation")
            operations = list(graph.objects(link_property, supported_operation_property))
            for operation in operations:
                graph.add((new_class_iri, supported_operation_property, operation))

        return graph


