from rdflib import BNode, Graph, RDF, URIRef
from oldman.exception import OMDifferentBaseIRIError, OMForbiddenSkolemizedIRIError, OMClassInstanceError
from oldman.resource import Resource, is_blank_node

_JSON_TYPES = ["application/json", "json"]
_JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class CRUDController(object):
    """
        TODO: add a PATCH method

        Generic (does not support the Collection pattern so there is no append method)
    """

    def __init__(self, manager):
        self._manager = manager

    def get(self, base_iri, content_type="text/turtle"):
        """
            HTTP GET.
            May raise an ObjectNotFoundError
        """
        resource = self._manager.get(base_iri=base_iri)

        if content_type in _JSON_TYPES:
            return resource.to_json()
        elif content_type in _JSON_LD_TYPES:
            return resource.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            return resource.to_rdf(content_type)

    def delete(self, base_iri):
        for resource in self._manager.filter(base_iri=base_iri):
            if resource is not None:
                resource.delete()

    def update(self, base_iri, new_document, content_type, allow_new_type=False, allow_type_removal=False):
        """
            A little bit more than an usual HTTP PUT: is able to give to some blank nodes of this representation.
        """
        graph = Graph()
        #TODO: manage parsing exceptions
        if content_type in _JSON_TYPES:
            resource = self._manager.get(base_iri=base_iri)
            graph.parse(data=new_document, format="json-ld", publicID=base_iri,
                        context=resource.context)
        #RDF graph
        else:
            graph.parse(data=new_document, format=content_type, publicID=base_iri)
        self._update_graph(base_iri, graph, allow_new_type, allow_type_removal)

    def _update_graph(self, base_iri, graph, allow_new_type, allow_type_removal):
        """
            Cannot create non-blank objects with a difference base_uris (security reasons)
        """
        subjects = set(graph.subjects())

        # Non-skolemized blank nodes
        bnode_subjects = filter(lambda x: isinstance(x, BNode), subjects)
        other_subjects = subjects.difference(bnode_subjects)

        #Blank nodes (may obtain a regular IRI)
        resources = self._create_anonymous_objects(base_iri, graph, bnode_subjects, allow_new_type, allow_type_removal)

        #Objects with an existing IRI
        resources += self._create_regular_resources(base_iri, graph, other_subjects, allow_new_type, allow_type_removal)

        #Check validity before saving
        #May raise a LDEditError
        for r in resources:
            r.check_validity()

        #TODO: improve it as a transaction (really necessary?)
        for r in resources:
            r.save()

        #Delete omitted resources
        all_resource_iris = {r.id for r in self._manager.filter(base_iri=base_iri)}
        resource_iris_to_remove = all_resource_iris.difference({r.id for r in resources})
        for iri in resource_iris_to_remove:
            # Cheap because already in the resource cache
            r = self._manager.get(id=iri)
            if r is not None:
                r.delete()

    def _create_anonymous_objects(self, base_iri, graph, bnode_subjects, allow_new_type, allow_type_removal):
        resources = []
        # Only former b-nodes
        dependent_objs = []

        for bnode in bnode_subjects:
            types = {unicode(t) for t in graph.objects(bnode, RDF.type)}
            resource = self._manager.new(base_iri=base_iri, types=types)
            alter_bnode_triples(graph, bnode, URIRef(resource.id))
            resource.full_update_from_graph(graph, save=False, allow_new_type=allow_new_type,
                                            allow_type_removal=allow_type_removal)
            resources.append(resource)

            deps = {o for _, p, o in graph.triples((bnode, None, None))
                    if isinstance(o, BNode)}
            if len(deps) > 0:
                dependent_objs.append(resource)

            if (not resource.is_blank_node()) and resource.base_iri != base_iri:
                raise OMDifferentBaseIRIError(u"%s is not the base IRI of %s" % (base_iri, resource.id))

        #When some Bnodes are interconnected
        for resource in dependent_objs:
            # Update again
            resource.full_update_from_graph(graph, save=False)

        return resources

    def _create_regular_resources(self, base_iri, graph, other_subjects, allow_new_type, allow_type_removal):
        resources = []
        for iri in [unicode(s) for s in other_subjects]:
            if is_blank_node(iri):
                raise OMForbiddenSkolemizedIRIError(u"Skolemized IRI like %s are not allowed when updating a resource."
                                                    % iri)
            elif iri.split("#")[0] != base_iri:
                raise OMDifferentBaseIRIError(u"%s is not the base IRI of %s" % (base_iri, iri))

            try:
                resource = self._manager.get(id=iri)
                resource.full_update_from_graph(graph, save=False, allow_new_type=allow_new_type,
                                                allow_type_removal=allow_type_removal)
            except OMClassInstanceError:
                # New object
                resource = Resource.load_from_graph(self._manager, iri, graph, is_new=True)

            resources.append(resource)
        return resources


def alter_bnode_triples(graph, bnode, new_uri_ref):
    subject_triples = list(graph.triples((bnode, None, None)))
    for _, p, o in subject_triples:
        graph.remove((bnode, p, o))
        graph.add((new_uri_ref, p, o))

    object_triples = list(graph.triples((None, None, bnode)))
    for s, p, _ in object_triples:
        graph.remove((s, p, bnode))
        graph.add((s, p, new_uri_ref))


def extract_types(object_iri, graph):
    return {t.toPython() for t in graph.objects(URIRef(object_iri), RDF.type)}