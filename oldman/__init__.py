"""
    OldMan
    ~~~~~~

    Object Linked Data Mapper (OLDM)
"""

from rdflib.plugin import register, Parser, Serializer
from rdflib import Graph
from .store.sparql import SparqlStore
from .store.http import HttpStore
from .utils.sparql import parse_graph_safely
from .rest.controller import HTTPController
from .mediation.default import DefaultUserMediator

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')


def create_user_mediator(data_stores, schema_graph=None, attr_extractor=None, oper_extractor=None,
                         declare_default_operation_functions=True, mediator_class=DefaultUserMediator):
    """TODO: describe """
    return mediator_class(data_stores, schema_graph=schema_graph, attr_extractor=attr_extractor,
                          oper_extractor=oper_extractor,
                          declare_default_operation_functions=declare_default_operation_functions)


