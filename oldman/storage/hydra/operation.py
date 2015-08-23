from rdflib import URIRef, Graph

from oldman.core.vocabulary import HYDRA_MEMBER_IRI
from oldman.core.utils.crud import extract_subjects, create_regular_resources, create_blank_nodes
from oldman.core.exception import OMBadRequestException

def append_to_hydra_collection(collection_resource, new_resources=None, graph=None, **kwargs):
    """TODO: improve the mechanism of operation """

    if new_resources is not None and graph is not None:
        # TODO: throw the right exception
        raise Exception("Cannot add new_resources and graphs in the same time")
    elif new_resources is not None:
        return _append_resources_to_hydra_collection(collection_resource, new_resources)
    else:
        return _append_to_hydra_coll_from_graph(collection_resource, graph)


def _append_to_hydra_coll_from_graph(collection_resource, graph):
    collection_iri = collection_resource.id

    # Extracts and classifies subjects
    bnode_subjects, other_subjects = extract_subjects(graph)

    # Blank nodes (may obtain a regular IRI)
    new_resources = create_blank_nodes(collection_resource.session, graph, bnode_subjects,
                                       collection_iri=collection_iri)

    # Objects with an existing IRI
    # TODO: ask if it should be accepted
    reg_resources, _ = create_regular_resources(collection_resource.session, graph, other_subjects,
                                                collection_iri=collection_iri)
    new_resources += reg_resources

    _append_resources_to_hydra_collection(collection_resource, new_resources)


def _append_resources_to_hydra_collection(collection_resource, new_resources):
    # Check that they are valid
    for new_resource in new_resources:
        if not new_resource.is_valid():
            # TODO: find a better exception
            raise OMBadRequestException("One resource is not valid")

    collection_graph = Graph().parse(data=collection_resource.to_rdf(rdf_format="nt"), format="nt")
    collection_resource.session.flush()
    for new_resource in new_resources:
        collection_graph.add((URIRef(collection_resource.id.iri), URIRef(HYDRA_MEMBER_IRI), URIRef(new_resource.id.iri)))
    collection_resource.update_from_graph(collection_graph)


def append_to_hydra_paged_collection(collection, graph=None, new_resources=None, **kwargs):
    raise NotImplementedError("TODO: implement me!")
