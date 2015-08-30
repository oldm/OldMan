"""
    OldMan
    ~~~~~~

    Object Linked Data Mapper (OLDM)
"""

from rdflib.plugin import register, Parser, Serializer

from .storage.store.sparql import SparqlStore
from .storage.store.http import HttpStore
from .core.utils.sparql import parse_graph_safely

from oldman.client.rest.controller import HTTPController
from oldman.client.mediation.default import DefaultUserMediator

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')


def create_user_mediator(data_stores, schema_graph=None, attr_extractor=None, oper_extractor=None,
                         mediator_class=DefaultUserMediator):
    if schema_graph is None:
        raise NotImplementedError("schema_graph extraction from the data stores in not yet supported. "
                                  "Please provide it.")

    """TODO: describe """
    return mediator_class(data_stores, schema_graph=schema_graph, attr_extractor=attr_extractor,
                          oper_extractor=oper_extractor)


