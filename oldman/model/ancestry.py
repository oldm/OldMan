from rdflib import URIRef
from oldman.exception import OMInternalError


class ClassAncestry(object):
    """Ancestry of a given RDFS class.

    :param child_class_iri: IRI of the child RDFS class.
    :param schema_graph: :class:`rdflib.Graph` object contains all the schema triples.
    """
    def __init__(self, child_class_iri, schema_graph):
        self._child_class_iri = child_class_iri
        if child_class_iri is None:
            self._ancestry_dict = {}
            self._bottom_up_list = []
        else:
            self._ancestry_dict = _extract_ancestry(child_class_iri, schema_graph)
            self._bottom_up_list = _extract_types_from_bottom(child_class_iri, self._ancestry_dict)

    @property
    def child(self):
        """Child of the ancestry."""
        return self._child_class_iri

    @property
    def bottom_up(self):
        """Ancestry list starting from the child."""
        return self._bottom_up_list

    @property
    def top_down(self):
        """Reverse of the `bottom_up` attribute."""
        chrono = list(self._bottom_up_list)
        chrono.reverse()
        return chrono

    def parents(self, class_iri):
        """Finds the parents of a given class in the ancestry.

        :param class_iri: IRI of the RDFS class.
        :return: List of class IRIs
        """
        return [parent for parent, _ in self._ancestry_dict.get(class_iri, [])]


def _extract_ancestry(class_iri, schema_graph):
    """
        Useful because class_iri is often a local specialization
        of a well-known class
    """
    ancestry_dict = {}
    request = u"""
    SELECT ?class ?parent ?priority WHERE {
        ?child_class rdfs:subClassOf* ?class.
        ?class rdfs:subClassOf ?parent.
        OPTIONAL {
            ?class <urn:oldman:model:ordering:hasPriority> ?p .
            ?p <urn:oldman:model:ordering:class> ?parent ;
               <urn:oldman:model:ordering:priority> ?priority .
        }.
        FILTER NOT EXISTS { ?class rdfs:subClassOf ?other .
                            ?other rdfs:subClassOf+ ?parent . }
    } ORDER BY DESC(?priority)
    """
    results = schema_graph.query(request, initBindings={'child_class': URIRef(class_iri)})
    for c, parent, pr in results:
        priority = pr.toPython() if pr is not None else None
        cls_iri = unicode(c)
        parent_iri = unicode(parent)
        if cls_iri in ancestry_dict:
            ancestry_dict[cls_iri].append((parent_iri, priority))
        else:
            ancestry_dict[cls_iri] = [(parent_iri, priority)]
    return ancestry_dict


def _extract_types_from_bottom(child_class_iri, ancestry_dict, ignored_types=None):
    """
        ignored_types is only for recursive call.
    """
    ignored_types = list(ignored_types) if ignored_types else []
    if child_class_iri in ignored_types:
        raise OMInternalError("%s should not be in %s" %(child_class_iri, ignored_types))

    anti_chrono = [child_class_iri]
    for class_iri in anti_chrono:
        prioritized_parents = ancestry_dict.get(class_iri, [])

        # Prioritizes if there are different priorities
        prioritize = (len({priority for _, priority in prioritized_parents}) > 1)
        if prioritize:
            for parent, _ in prioritized_parents:
                if (parent not in ignored_types) and (parent not in anti_chrono):
                    # Hybrid recursive style
                    anti_chrono += _extract_types_from_bottom(parent, ancestry_dict, anti_chrono)
        else:
            anti_chrono += [parent for parent, _ in prioritized_parents if parent not in ignored_types
                            and parent not in anti_chrono]
    return anti_chrono