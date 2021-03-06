from os import path
import json
import logging.config

from dogpile.cache import make_region
from rdflib import Dataset, Graph
from rdflib.namespace import FOAF

from oldman import ClientResourceManager, parse_graph_safely, SPARQLDataStore
from oldman.rest.crud import HashLessCRUDer


logging.config.fileConfig(path.join(path.dirname(__file__), 'logging.ini'))



sesame_iri = "http://localhost:8080/openrdf-sesame/repositories/test"
#store = SPARQLUpdateStore(queryEndpoint=sesame_iri, update_endpoint=sesame_iri + "/statements")
#store.setCredentials("paul", "heyjude")
#store = SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                          update_endpoint="http://localhost:3030/test/update")
store = 'default'
dataset = Dataset(store)
data_graph = dataset.graph("http://localhost/data")

#schema_graph = dataset.graph("http://localhost/schema")
schema_graph = Graph()

BIO = "http://purl.org/vocab/bio/0.1/"
REL = "http://purl.org/vocab/relationship/"
CERT = "http://www.w3.org/ns/auth/cert#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
WOT = "http://xmlns.com/wot/0.1/"

MY_VOC = "http://example.com/vocab#"
local_person_def = {
    "@context": [
        {
            "myvoc": MY_VOC,
            "foaf": FOAF,
            "bio": BIO,
            "rel": REL,
            "cert": CERT,
            "wot": WOT,
            "schema": "http://schema.org/"
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "myvoc:LocalPerson",
    "@type": "hydra:Class",
    "subClassOf": "foaf:Person",
    "supportedProperty": [
        {
            "property": "foaf:name",
            "required": True
        },
        {
            "property": "foaf:mbox",
            "required": True
        },
        {
            "property": "foaf:weblog"
        },
        {
            "property": "bio:olb",
            "required": True
        },
        {
            "property": "foaf:knows"
        },
        {
            "property": "rel:parentOf"
        },
        {
            "property": "rel:parentOf",
            "hydra:reversed": True
        },
        {
            "property": "cert:key"
        },
        {
            "property": "wot:hasKey"
        },
        {
            "property": "schema:employee"
        },
        {
            "property": "schema:employee",
            "hydra:reversed": True
        }
    ]
}
parse_graph_safely(schema_graph, data=json.dumps(local_person_def), format="json-ld")

local_rsa_key_def = {
    "@context": [
        {
            "myvoc": MY_VOC,
            "rdfs": RDFS,
            "cert": CERT
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "myvoc:LocalRSAPublicKey",
    "@type": "hydra:Class",
    "subClassOf": "cert:RSAPublicKey",
    "supportedProperty": [
        {
            "property": "cert:exponent",
            "required": True
        },
        {
            "property": "cert:modulus",
            "required": True
        },
        {
            "property": "rdfs:label"
        }
    ]
}
parse_graph_safely(schema_graph, data=json.dumps(local_rsa_key_def), format="json-ld")

local_gpg_key_def = {
    "@context": [
        {
            "myvoc": MY_VOC,
            "wot": WOT
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "myvoc:LocalGPGPublicKey",
    "@type": "hydra:Class",
    "subClassOf": "wot:PubKey",
    "supportedProperty": [
        {
            "property": "wot:fingerprint",
            "required": True,
        },
        {
            "property": "wot:hex_id",
            "required": True
        }
    ]
}
parse_graph_safely(schema_graph, data=json.dumps(local_gpg_key_def), format="json-ld")
#print schema_graph.serialize(format="turtle")

context = {
    "@context": {
        "myvoc": MY_VOC,
        "rdfs": RDFS,
        "foaf": "http://xmlns.com/foaf/0.1/",
        "bio": "http://purl.org/vocab/bio/0.1/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rel": "http://purl.org/vocab/relationship/",
        "schema": "http://schema.org/",
        "cert": CERT,
        "wot": WOT,
        "id": "@id",
        "types": "@type",
        "LocalPerson": "myvoc:LocalPerson",
        "Person": "foaf:Person",
        "LocalRSAPublicKey": "myvoc:LocalRSAPublicKey",
        "LocalGPGPublicKey": "myvoc:LocalGPGPublicKey",
        "name": {
            "@id": "foaf:name",
            "@type": "xsd:string"
        },
        "mboxes": {
            "@id": "foaf:mbox",
            "@type": "xsd:string",
            "@container": "@set"
        },
        "blog": {
            "@id": "foaf:weblog",
            "@type": "@id"
        },
        "short_bio_fr": {
            "@id": "bio:olb",
            "@language": "fr"
        },
        "short_bio_en": {
            "@id": "bio:olb",
            "@language": "en"
        },
        "friends": {
            "@id": "foaf:knows",
            "@type": "@id",
            "@container": "@set"
        },
        "employee": {
            "@id": "schema:employee",
            "@type": "@id"
        },
        "employer": {
            "@reverse": "schema:employee",
            "@type": "@id"
        },
        "children": {
            "@id": "rel:parentOf",
            "@type": "@id",
            "@container": "@list"
        },
        "parents": {
            "@reverse": "rel:parentOf",
            "@type": "@id",
            "@container": "@set"
        },
        "gpg_key": {
            "@id": "wot:hasKey",
            "@type": "@id"
        },
        "keys": {
            "@id": "cert:key",
            "@type": "@id",
            "@container": "@set"
        },
        # For keys
        "modulus": {
            "@id": "cert:modulus",
            "@type": "xsd:hexBinary"
        },
        "exponent": {
            "@id": "cert:exponent",
            "@type": "xsd:integer"
        },
        "label": {
            "@id": "rdfs:label",
            "@type": "xsd:string"
        },
        # For GPG
        "fingerprint": {
            "@id": "wot:fingerprint",
            "@type": "xsd:hexBinary"
        },
        "hex_id": {
            "@id": "wot:hex_id",
            "@type": "xsd:hexBinary"
        }
    }
}

# Cache
#cache_region = None
cache_region = make_region().configure('dogpile.cache.memory_pickle')

data_store = SPARQLDataStore(data_graph, schema_graph=schema_graph, cache_region=cache_region)
# Takes the prefixes from the schema graph
data_store.extract_prefixes(schema_graph)

#lp_name_or_iri = "LocalPerson"
lp_name_or_iri = MY_VOC + "LocalPerson"
data_store.create_model(lp_name_or_iri, context, iri_prefix="http://localhost/persons/", iri_fragment="me")
data_store.create_model("LocalRSAPublicKey", context)
data_store.create_model("LocalGPGPublicKey", context)

client_manager = ClientResourceManager(data_store)
client_manager.import_store_models()

lp_model = client_manager.get_model(lp_name_or_iri)
rsa_model = client_manager.get_model("LocalRSAPublicKey")
gpg_model = client_manager.get_model("LocalGPGPublicKey")


crud_controller = HashLessCRUDer(client_manager)

bob_name = "Bob"
bob_blog = "http://blog.example.com/"
bob_email1 = "bob@localhost"
bob_email2 = "bob@example.org"
bob_emails = {bob_email1, bob_email2}
bob_bio_en = "I grow up in ... ."
bob_bio_fr = u"J'ai grandi en ... ."
alice_name = "Alice"
alice_mail = "alice@example.org"
alice_bio_en = "I am an expert on this and that"
john_name = "John"
john_mail = "john@example.com"
john_bio_en = "Supporter of Linked Data"
key_modulus = "b42dbf23ee820be938bee7298893e434f8f74d4be2bbe39408776d695168d09262da2a849962"
key_exponent = 65537
key_label = "Key 1"
gpg_fingerprint = "1aef32b079fc3cabcfc26c5e54d0e38c002640d4"
gpg_hex_id = "002640e2"

prof_type = MY_VOC + "Professor"
researcher_type = MY_VOC + "Researcher"

# xsd:hexBinary behaves strangely in Fuseki. Not supported by SPARQL? http://www.w3.org/2011/rdf-wg/wiki/XSD_Datatypes
#ask_fingerprint = """ASK { ?x wot:fingerprint "%s"^^xsd:hexBinary }""" % gpg_fingerprint
ask_fingerprint = """ASK { ?x wot:fingerprint ?y }"""
#ask_modulus = """ASK {?x cert:modulus "%s"^^xsd:hexBinary }""" % key_modulus
ask_modulus = """ASK {?x cert:modulus ?y }"""


def tear_down():
    """ Clears the data graph """
    if cache_region:
        # Memory backends of dogpile.cache do not support the invalidate method()
        iris = {unicode(r) for r in data_graph.query("SELECT DISTINCT ?s WHERE { ?s ?p ?o }")}
        for iri in iris:
            cache_region.delete(iri)
    dataset.update("CLEAR GRAPH <%s>" % data_graph.identifier)
    data_store.resource_cache.invalidate_cache()


def set_up(use_default_cache_region=True):
    if use_default_cache_region:
        data_store.resource_cache.change_cache_region(cache_region)


def create_bob():
    return lp_model.create(name=bob_name, blog=bob_blog, mboxes=bob_emails,
                           short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)


def create_alice():
    return lp_model.create(name=alice_name, mboxes={alice_mail}, short_bio_en=alice_bio_en)


def create_john(id=None):
    return lp_model.create(id=id, name=john_name, mboxes={john_mail}, short_bio_en=john_bio_en)


def create_rsa_key():
    return rsa_model.create(exponent=key_exponent, modulus=key_modulus, label=key_label)


def create_gpg_key():
    return gpg_model.create(fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)