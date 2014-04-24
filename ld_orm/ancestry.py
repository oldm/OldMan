from rdflib import URIRef
from rdflib.plugins.sparql import prepareQuery


ANCESTRY_REQUEST = prepareQuery("""
                                SELECT ?class ?parent WHERE {
                                    ?child_class rdfs:subClassOf* ?class.
                                    ?class rdfs:subClassOf ?parent.
                                    FILTER NOT EXISTS { ?class rdfs:subClassOf ?other .
                                                        ?other rdfs:subClassOf+ ?parent . }
                                }""")


def extract_ancestry(class_uri, schema_graph):
    """
        Useful because class_uri is often a local specialization
        of a well-known class
    """
    ancestry = {}
    results = schema_graph.query(ANCESTRY_REQUEST,
                                 initBindings={'child_class': URIRef(class_uri)})
    for c, parent in results:
        cls_uri = unicode(c)
        parent_uri = unicode(parent)
        if cls_uri in ancestry:
            ancestry[cls_uri].add(parent_uri)
        else:
            ancestry[cls_uri] = {parent_uri}
    return ancestry


def extract_types_from_bottom(child_class_uri, ancestry_dict):
    antichrono = [child_class_uri]
    for class_uri in antichrono:
        parents = ancestry_dict.get(class_uri, [])
        antichrono += [p for p in parents if p not in antichrono]
    return antichrono


class Ancestry(object):
    def __init__(self, child_class_uri, schema_graph):
        self._child_class_uri = child_class_uri
        if child_class_uri is None:
            self._ancestry_dict = {}
            self._bottom_up_list = []
        else:
            self._ancestry_dict = extract_ancestry(child_class_uri, schema_graph)
            self._bottom_up_list = extract_types_from_bottom(child_class_uri, self._ancestry_dict)

    @property
    def child(self):
        return self._child_class_uri

    @property
    def bottom_up(self):
        """
            Starting from the child
        """
        return self._bottom_up_list

    @property
    def top_down(self):
        chrono = list(self._bottom_up_list)
        chrono.reverse()
        return chrono

    def parents(self, class_uri):
        return self._ancestry.get(class_uri)