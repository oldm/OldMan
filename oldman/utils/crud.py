from rdflib import RDF, URIRef, BNode

from oldman.exception import OMDifferentHashlessIRIError, OMForbiddenSkolemizedIRIError, OMClassInstanceError, OMInternalError
from oldman.resource.resource import Resource, is_blank_node


def extract_subjects(graph):
    subjects = set(graph.subjects())

    # Non-skolemized blank nodes
    bnode_subjects = filter(lambda x: isinstance(x, BNode), subjects)
    other_subjects = subjects.difference(bnode_subjects)

    return bnode_subjects, other_subjects


def create_blank_nodes(manager, graph, bnode_subjects, hashless_iri=None, collection_iri=None):
    """TODO: comment """
    resources = []
    # Only former b-nodes
    dependent_resources = []

    _check_iris(hashless_iri, collection_iri)

    for bnode in bnode_subjects:
        types = {unicode(t) for t in graph.objects(bnode, RDF.type)}
        resource = manager.new(hashless_iri=hashless_iri, collection_iri=collection_iri, types=types)
        _alter_bnode_triples(graph, bnode, URIRef(resource.id))
        resource.update_from_graph(graph, save=False)
        resources.append(resource)

        deps = {o for _, p, o in graph.triples((bnode, None, None))
                if isinstance(o, BNode)}
        if len(deps) > 0:
            dependent_resources.append(resource)

        if (hashless_iri is not None) and (not resource.is_blank_node()) and resource.hashless_iri != hashless_iri:
            raise OMDifferentHashlessIRIError(u"%s is not the hash-less IRI of %s" % (hashless_iri, resource.id))

    #When some Bnodes are interconnected
    for resource in dependent_resources:
        # Update again
        resource.update_from_graph(graph, save=False)

    return resources


def create_regular_resources(manager, graph, subjects, hashless_iri=None, collection_iri=None):
    """"TODO: comment """

    resources = []
    resources_to_update = []

    for iri in [unicode(s) for s in subjects]:
        if is_blank_node(iri):
            raise OMForbiddenSkolemizedIRIError(u"Skolemized IRI like %s are not allowed when updating a resource."
                                                % iri)
        elif (hashless_iri is not None) and iri.split("#")[0] != hashless_iri:
            raise OMDifferentHashlessIRIError(u"%s is not the hash-less IRI of %s" % (hashless_iri, iri))

        try:
            resource = manager.get(id=iri)
            resources_to_update.append(resource)

        except OMClassInstanceError:
            # New resource
            # TODO: what about IRI generation?
            resource = Resource.load_from_graph(manager, iri, graph, is_new=True)

        resources.append(resource)
    return resources, resources_to_update


def _alter_bnode_triples(graph, bnode, new_iri_ref):
    subject_triples = list(graph.triples((bnode, None, None)))
    for _, p, o in subject_triples:
        graph.remove((bnode, p, o))
        graph.add((new_iri_ref, p, o))

    object_triples = list(graph.triples((None, None, bnode)))
    for s, p, _ in object_triples:
        graph.remove((s, p, bnode))
        graph.add((s, p, new_iri_ref))


def _check_iris(hashless_iri, collection_iri):
    if hashless_iri is not None and collection_iri is not None:
        raise OMInternalError("Only one of the variables hashless_iri and collection_iri must be given")
    elif hashless_iri is None and collection_iri is None:
        raise OMInternalError("One (and only one) of the variables hashless_iri and collection_iri must be given")