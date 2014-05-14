from rdflib import BNode, Graph, RDF, URIRef
from oldman.exception import OMDifferentBaseIRIError, OMForbiddenSkolemizedIRIError, OMClassInstanceError
from oldman.resource import Resource, is_blank_node
from oldman.registry import extract_types

_JSON_TYPES = ["application/json", "json"]
_JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class CRUDController(object):
    """
        TODO: add a PATCH method

        Generic (does not support the Collection pattern so there is no append method)
    """

    def __init__(self, dataset):
        self._dataset = dataset
        self._registry = dataset.registry

    def get(self, base_uri, content_type="text/turtle"):
        """
            HTTP GET.
            May raise an ObjectNotFoundError
        """
        obj_uri = self._registry.find_object_from_base_uri(base_uri)
        obj = self._registry.get_object(obj_uri)

        if content_type in _JSON_TYPES:
            return obj.to_json()
        elif content_type in _JSON_LD_TYPES:
            return obj.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            return obj.to_rdf(content_type)

    def delete(self, base_uri):
        for obj_iri in self._registry.find_object_iris(base_uri):
            obj = self._registry.get_object(obj_iri)
            if obj is not None:
                obj.delete()

    def update(self, base_uri, new_document, content_type):
        """
            A little bit more than an usual HTTP PUT: is able to give to some blank nodes of this representation.
        """
        graph = Graph()
        #TODO: manage parsing exceptions
        if content_type in _JSON_TYPES:
            obj_iri = self._registry.find_object_from_base_uri(base_uri)
            obj = self._registry.get_object(obj_iri)
            graph.parse(data=new_document, format="json-ld", publicID=base_uri,
                        context=obj.context)
        #RDF graph
        else:
            graph.parse(data=new_document, format=content_type, publicID=base_uri)
        self._update_graph(base_uri, graph)

    def _update_graph(self, base_iri, graph):
        """
            Cannot create non-blank objects with a difference base_uris (security reasons)
        """
        subjects = set(graph.subjects())

        # Non-skolemized blank nodes
        bnode_subjects = filter(lambda x: isinstance(x, BNode), subjects)
        other_subjects = subjects.difference(bnode_subjects)

        #Blank nodes (may obtain a regular IRI)
        objs = self._create_anonymous_objects(base_iri, graph, bnode_subjects)

        #Objects with an existing IRI
        objs += self._create_regular_objects(base_iri, graph, other_subjects)

        #Check validity before saving
        #May raise a LDEditError
        for obj in objs:
            obj.check_validity()

        #TODO: improve it as a transaction (really necessary?)
        for obj in objs:
            obj.save()

        #Delete omitted resources
        all_obj_iris = set(self._registry.find_object_iris(base_iri))
        obj_iris_to_remove = all_obj_iris.difference({obj.id for obj in objs})
        for obj_iri in obj_iris_to_remove:
            obj = self._registry.get_object(obj_iri)
            if obj is not None:
                obj.delete()

    def _create_anonymous_objects(self, base_iri, graph, bnode_subjects):
        objs = []
        # Only former b-nodes
        dependent_objs = []

        for bnode in bnode_subjects:
            types = {unicode(t) for t in graph.objects(bnode, RDF.type)}
            model = self._registry.select_model(self._registry.get_models(types))
            obj = model.new(base_iri=base_iri)
            alter_bnode_triples(graph, bnode, URIRef(obj.id))
            obj.full_update_from_graph(graph, save=False)
            objs.append(obj)

            deps = {o for _, p, o in graph.triples((bnode, None, None))
                    if isinstance(o, BNode)}
            if len(deps) > 0:
                dependent_objs.append(obj)

            if (not obj.is_blank_node()) and obj.base_iri != base_iri:
                raise OMDifferentBaseIRIError("%s is not the base IRI of %s" % (base_iri, obj.id))

        #When some Bnodes are interconnected
        for obj in dependent_objs:
            # Update again
            obj.full_update_from_graph(graph, save=False)

        return objs

    def _create_regular_objects(self, base_iri, graph, other_subjects):
        objs = []
        for obj_iri in [unicode(s) for s in other_subjects]:
            if is_blank_node(obj_iri):
                raise OMForbiddenSkolemizedIRIError("Skolemized IRI like %s are not allowed when updating a resource."
                                                  % obj_iri)
            elif obj_iri.split("#")[0] != base_iri:
                raise OMDifferentBaseIRIError("%s is not the base IRI of %s" % (base_iri, obj_iri))

            types = extract_types(obj_iri, graph)
            model = self._registry.select_model(self._registry.get_models(types))
            try:
                obj = model.objects.get(id=obj_iri)
                obj.full_update_from_graph(graph, save=False)
            except OMClassInstanceError:
                # New object
                obj = Resource.load_from_graph(self._dataset, obj_iri, graph, is_new=True)

            objs.append(obj)
        return objs


def alter_bnode_triples(graph, bnode, new_uri_ref):
    subject_triples = list(graph.triples((bnode, None, None)))
    for _, p, o in subject_triples:
        graph.remove((bnode, p, o))
        graph.add((new_uri_ref, p, o))

    object_triples = list(graph.triples((None, None, bnode)))
    for s, p, _ in object_triples:
        graph.remove((s, p, bnode))
        graph.add((s, p, new_uri_ref))
