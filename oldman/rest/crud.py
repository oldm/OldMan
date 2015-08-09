from rdflib import BNode, Graph
from rdflib.plugin import PluginException
from oldman.utils.crud import create_blank_nodes, create_regular_resources
from oldman.utils.crud import extract_subjects
from oldman.exception import OMBadRequestException, OMNotAcceptableException

JSON_TYPES = ["application/json", "json"]
JSON_LD_TYPES = ["application/ld+json", "json-ld"]


class HashLessCRUDer(object):
    """A :class:`~oldman.rest.crud.HashlessCRUDer` object helps you to manipulate
    your :class:`~oldman.resource.Resource` objects in a RESTful-like manner.

    Please note that REST/HTTP only manipulates hash-less IRIs.
    A hash IRI is the combination of a hash-less IRI (fragment-less IRI) and a fragment.
    Multiple hashed IRIs may have the same hash-less IRI and only differ by
    their fragment values.
    This is a concern for each type of HTTP operation.

    This class is generic and does not support the Collection pattern
    (there is no append method).

    :param manager: :class:`~oldman.resource.manager.ResourceManager` object.

    Possible improvements:

        - Add a PATCH method.
    """

    def __init__(self, user_mediator):
        self._user_mediator = user_mediator

    def get(self, hashless_iri, content_type="text/turtle"):
        """Gets the main :class:`~oldman.resource.Resource` object having its hash-less IRI.

        When multiple  :class:`~oldman.resource.Resource` objects have this hash-less IRI,
        one of them has to be selected.
        If one has no fragment value, it is selected.
        Otherwise, this selection is currently arbitrary.

        TODO: stop selecting the resources and returns the graph containing these resources.

        Raises an :class:`~oldman.exception.ObjectNotFoundError` exception if no resource is found.

        :param hashless_iri: hash-less of the resource.
        :param content_type: Content type of its representation.
        :return: The representation of selected :class:`~oldman.resource.Resource` object and its content type
        """
        session = self._user_mediator.create_session()
        #TODO: stop this practice
        resource = session.get(hashless_iri=hashless_iri)

        if content_type in JSON_TYPES:
            payload = resource.to_json()
        elif content_type in JSON_LD_TYPES:
            payload = resource.to_jsonld()
        # Try as a RDF mime-type (may not be supported)
        else:
            try:
                payload = resource.to_rdf(content_type)
            except PluginException:
                raise OMNotAcceptableException()
            finally:
                session.close()
        return payload, content_type

    def delete(self, hashless_iri):
        """Deletes every :class:`~oldman.resource.Resource` object having this hash-less IRI.

        :param hashless_iri: Hash-less IRI.
        """
        session = self._user_mediator.create_session()
        for resource in session.filter(hashless_iri=hashless_iri):
            if resource is not None:
                session.delete(resource)
        session.close()

    def update(self, hashless_iri, document_content, content_type, allow_new_type=False, allow_type_removal=False):
        """Updates every :class:`~oldman.resource.Resource` object having this hash-less IRI.

        Raises an :class:`~oldman.exception.OMDifferentBaseIRIError` exception
        if tries to create of modify non-blank :class:`~oldman.resource.Resource` objects
        that have a different hash-less IRI.
        This restriction is motivated by security concerns.

        Accepts JSON, JSON-LD and RDF formats supported by RDFlib.

        :param hashless_iri: Document IRI.
        :param document_content: Payload.
        :param content_type: Content type of the payload.
        :param allow_new_type: If `True`, new types can be added. Defaults to `False`. See
                               :func:`oldman.resource.Resource.full_update` for explanations about the
                               security concerns.
        :param allow_type_removal: If `True`, new types can be removed. Same security concerns than above.
                                   Defaults to `False`.
        """
        graph = Graph()
        session = self._user_mediator.create_session()
        #TODO: manage parsing exceptions
        if content_type in JSON_TYPES:
            resource = session.get(hashless_iri=hashless_iri)
            graph.parse(data=document_content, format="json-ld", publicID=hashless_iri,
                        context=resource.context)
        #RDF graph
        #TODO: capture unknown type
        else:
            graph.parse(data=document_content, format=content_type, publicID=hashless_iri)
        self._update_graph(hashless_iri, graph, allow_new_type, allow_type_removal)

    def _update_graph(self, hashless_iri, graph, allow_new_type, allow_type_removal):

        session = self._user_mediator.create_session()

        # Extracts and classifies subjects
        bnode_subjects, other_subjects = extract_subjects(graph)

        #Blank nodes (may obtain a regular IRI)
        resources = create_blank_nodes(session, graph, bnode_subjects, hashless_iri=hashless_iri)

        #Objects with an existing IRI
        reg_resources, resources_to_update = create_regular_resources(session, graph, other_subjects,
                                                                      hashless_iri=hashless_iri)
        resources += reg_resources

        # Subset of regular resources to update
        for resource in resources_to_update:
            resource.update_from_graph(graph, allow_new_type=allow_new_type,
                                       allow_type_removal=allow_type_removal)

        #Check validity before saving
        for r in resources:
            if not r.is_valid():
                raise OMBadRequestException()

        session.commit()

        #Delete omitted resources
        all_resource_iris = {r.id.iri for r in session.filter(hashless_iri=hashless_iri)}
        resource_iris_to_remove = all_resource_iris.difference({r.id.iri for r in resources})
        for iri in resource_iris_to_remove:
            # Cheap because already in the resource cache
            r = session.get(iri=iri)
            if r is not None:
                session.delete(r)
        session.commit()