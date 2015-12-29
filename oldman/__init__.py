"""
    OldMan
    ~~~~~~

    Object Linked Data Mapper (OLDM)
"""

from rdflib.plugin import register, Parser, Serializer
from oldman.client.parsing.operation import HydraOperationExtractor

from .storage.store.sparql import SparqlStoreProxy
from .storage.store.http import HttpStoreProxy
from .core.utils.sparql import parse_graph_safely

from oldman.client.rest.controller import HTTPController
from oldman.client.mediation.default import DefaultMediator

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')


def create_mediator(attr_extractor=None, oper_extractor=None, mediator_class=DefaultMediator):
    """TODO: describe """
    # By default, extracts Hydra operations
    if oper_extractor is None:
        oper_extractor = HydraOperationExtractor()

    return mediator_class(oper_extractor, attr_extractor=attr_extractor)


