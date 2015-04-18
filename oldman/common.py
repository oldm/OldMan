from urlparse import urlparse

DATATYPE_PROPERTY = "datatype"
OBJECT_PROPERTY = "object"

def is_blank_node(iri):
    """Tests if `id` is a locally skolemized IRI.

    External skolemized blank nodes are not considered as blank nodes.

    :param iri: IRI of the resource.
    :return: `True` if is a blank node.
    """
    id_result = urlparse(iri)
    return (u"/.well-known/genid/" in id_result.path) and (id_result.hostname == u"localhost")
