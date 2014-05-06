from rdflib import BNode, Graph, RDF
from .exceptions import LDEditError, DifferentBaseIRIError, ForbiddenSkolemizedIRIError
from .model import is_blank_node

_JSON_TYPES = ["application/json", "json"]
_JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class CRUDController(object):
    """
        TODO: add a PATCH method
    """

    def __init__(self, registry):
        self._registry = registry

    def get(self, base_uri, content_type="text/turtle"):
        """
            HTTP GET.
            May raise an ObjectNotFoundError
        """
        obj_uri = self._registry.find_object_from_base_uri(base_uri)
        obj = self._registry.find_object(obj_uri)

        if content_type in _JSON_TYPES:
            return obj.to_json()
        elif content_type in _JSON_LD_TYPES:
            return obj.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            return obj.to_rdf(content_type)

    def delete(self, base_uri):
        for obj_iri in self._registry.find_object_iris(base_uri):
            obj = self._registry.find_object(obj_iri)
            if obj is not None:
                obj.delete()

    def put(self, base_uri, new_document, content_type):
        if content_type in _JSON_TYPES:
            raise NotImplementedError("TODO: convert to JSON-LD??")
        elif content_type in _JSON_LD_TYPES:
            raise NotImplementedError("TODO: 'reshape' the JSON-LD if necessary, decompose it into objects ")

        # Presume a RDF graph
        else:
            self._put_graph(base_uri, new_document, content_type)

    def _put_graph(self, base_uri, new_document, content_type):
        """
            Cannot create non-blank objects with a difference base_uris (security reasons)
        """
        g = Graph()
        #TODO: manage exceptions
        g.parse(data=new_document, format=content_type, publicID=base_uri)
        subjects = set(g.subjects())

        objs = []
        # Only former b-nodes
        dependent_objs = []

        # Non-skolemized blank nodes
        bnode_subjects = filter(lambda x: isinstance(x, BNode), subjects)
        other_subjects = subjects.difference(bnode_subjects)

        for bnode in bnode_subjects:
            types = {unicode(t) for t in g.objects(bnode, RDF.type)}
            model_class = self._registry.select_model_class(types)
            obj = model_class()
            alter_bnode_triples(g, bnode, obj.id)
            obj.full_update_from_graph(g, save=False)
            objs.append(obj)

            deps = {o for _, p, o in g.triples(bnode, None, None)
                    if isinstance(o, BNode)}
            if len(deps) > 0:
                dependent_objs.append(obj)

            if (not obj.is_blank_node()) and obj.base_iri != base_uri:
                raise DifferentBaseIRIError("%s is not the base IRI of %s" % (base_uri, obj.id))

        #When some Bnodes are interconnected
        for obj in dependent_objs:
            # Update again
            obj.full_update_from_graph(g, save=False)

        #Regular objects
        for obj_iri in [unicode(s) for s in other_subjects]:
            if is_blank_node(obj_iri):
                raise ForbiddenSkolemizedIRIError("Skolemized IRI like %s are not allowed when updating a resource."
                                                  % obj_iri)
            elif obj_iri.split("#")[0] != base_uri:
                raise DifferentBaseIRIError("%s is not the base IRI of %s" % (base_uri, obj_iri))

            model_class = self._registry.find_model_class(obj_iri)
            obj = model_class.objects.get(id=obj_iri)
            # If new
            if obj is None:
                obj = model_class.load_from_graph(obj_iri, g, create=True)
            else:
                obj.full_update_from_graph(g, save=False)
            objs.append(obj)

        #Check validity before saving
        for obj in objs:
            if not obj.is_valid():
                #TODO: improve the report
                raise LDEditError("Obj %s is invalid. %s" % (obj.id, obj.to_json()))

        #Should not throw some exceptions
        #TODO: improve it as a transaction
        for obj in objs:
            obj.save()

        #Delete omitted resources
        all_obj_iris = set(self._registry.find_object_iris(base_uri))
        obj_iris_to_remove = all_obj_iris.difference({obj.id for obj in objs})
        for obj_iri in obj_iris_to_remove:
            obj = self._registry.find_object(obj_iri)
            if obj is not None:
                obj.delete()

    def append(self, base_uri, new_document, content_type):
        raise NotImplementedError("TODO: implement it")


def alter_bnode_triples(graph, bnode, new_uri_ref):
    subject_triples = list(graph.triples(bnode, None, None))
    for _, p, o in subject_triples:
        graph.remove((bnode, p, o))
        graph.add((new_uri_ref, p, o))

    object_triples = list(graph.triples(None, None, bnode))
    for s, p, _ in object_triples:
        graph.remove((s, p, bnode))
        graph.add((s, p, new_uri_ref))
