from rdflib import Graph
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore


def parse_graph_safely(graph, *args, **kwargs):
    """Skolemizes the input source if the graph uses a
    :class:`rdflib.plugins.stores.sparqlstore.SPARQLUpdateStore` object.

    :param graph: :class:`rdflib.graph.Graph` object.
    :param args: Argument `list` to transmit to :func:`rdflib.graph.Graph.parse`.
    :param kwargs: Argument `dict` to transmit to :func:`rdflib.graph.Graph.parse`.
    :return: The updated :class:`rdflib.graph.Graph` object.
    """
    if isinstance(graph.store, SPARQLUpdateStore):
        g = Graph().parse(*args, **kwargs).skolemize()
        graph.parse(data=g.serialize(format="nt"), format="nt")
    else:
        graph = graph.parse(*args, **kwargs).skolemize()
    return graph


def build_query_part(verb_and_vars, subject_term, lines):
    """Builds a SPARQL query.

    :param verb_and_vars: SPARQL verb and variables.
    :param subject_term: Common subject term.
    :param lines: Lines to insert into the WHERE block.
    :return: A SPARQL query.
    """
    if len(lines) == 0:
        return ""
    query_part = u'%s { \n%s } \n' % (verb_and_vars, lines)
    #{0} -> subject_term
    # format() does not work because other special symbols
    return query_part.replace(u"{0}", subject_term)


def build_update_query_part(verb, subject, lines):
    """Builds a SPARQL Update query.

    :param verb: SPARQL verb.
    :param subject: Common subject term.
    :param lines: Lines to insert into the WHERE block.
    :return: A SPARQL Update query.
    """
    return build_query_part(verb, u"<%s>" % subject, lines)