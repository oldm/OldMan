"""
    OldMan: Python OLDM
"""

from rdflib.plugin import register, Parser, Serializer
from .dataset import create_dataset
from .utils.sparql import parse_graph_safely

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')


