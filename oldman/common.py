from urlparse import urlparse

DATATYPE_PROPERTY = "datatype"
OBJECT_PROPERTY = "object"

TEMPORARY_BNODE_PREFIX = u"http://localhost/.well-known/genid/tmp/"


def is_blank_node(iri):
    """Tests if `id` is a locally skolemized IRI.

    External skolemized blank nodes are not considered as blank nodes.

    :param iri: IRI of the resource.
    :return: `True` if is a blank node.
    """
    id_result = urlparse(iri)
    return (u"/.well-known/genid/" in id_result.path) and (id_result.hostname == u"localhost")


def is_temporary_blank_node(iri):
    return TEMPORARY_BNODE_PREFIX in iri