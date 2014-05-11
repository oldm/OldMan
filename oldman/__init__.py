"""
    OldMan: Python OLDM
"""

from rdflib.plugin import register, Parser, Serializer
from .factory import default_model_factory

register('json-ld', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')
register('json-ld', Serializer, 'rdflib_jsonld.serializer', 'JsonLDSerializer')
register('application/ld+json', Parser, 'rdflib_jsonld.parser', 'JsonLDParser')


