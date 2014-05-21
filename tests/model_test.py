# -*- coding: utf-8 -*-

from unittest import TestCase
from os import path
import json

from rdflib import ConjunctiveGraph, Graph, URIRef, Literal, RDF, XSD
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from rdflib.namespace import FOAF

from oldman import create_resource_manager, parse_graph_safely
from oldman.attribute import OMAttributeTypeCheckError, OMRequiredPropertyError
from oldman.exception import OMClassInstanceError, OMAttributeAccessError, OMUniquenessError
from oldman.exception import OMWrongResourceError, OMObjectNotFoundError, OMHashIriError, OMEditError
from oldman.exception import OMDifferentBaseIRIError, OMForbiddenSkolemizedIRIError, OMUnauthorizedTypeChangeError
from oldman.rest.crud import CRUDController


#default_graph = ConjunctiveGraph(SPARQLUpdateStore(queryEndpoint="http://localhost:3030/test/query",
#                                                   update_endpoint="http://localhost:3030/test/update"))
default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))


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
            "wot": WOT
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
            "property": "cert:key"
        },
        {
            "property": "wot:hasKey"
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
        "children": {
            "@id": "rel:parentOf",
            "@type": "@id",
            "@container": "@list"
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

default_graph.namespace_manager.bind("foaf", FOAF)
default_graph.namespace_manager.bind("wot", WOT)
default_graph.namespace_manager.bind("rel", REL)
default_graph.namespace_manager.bind("cert", CERT)

manager = create_resource_manager(schema_graph, data_graph)
# Model classes are generated here!
lp_model = manager.create_model("LocalPerson", context, iri_prefix="http://localhost/persons/",
                               iri_fragment="me")
rsa_model = manager.create_model("LocalRSAPublicKey", context)
gpg_model = manager.create_model("LocalGPGPublicKey", context)

crud_controller = CRUDController(manager)

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


class ModelTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        default_graph.update("CLEAR GRAPH <%s>" % data_graph.identifier)
        manager.clear_resource_cache()

    def create_bob(self):
        return lp_model.create(name=bob_name, blog=bob_blog, mboxes=bob_emails,
                               short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)

    def create_alice(self):
        return lp_model.create(name=alice_name, mboxes={alice_mail}, short_bio_en=alice_bio_en)

    def create_john(self):
        return lp_model.create(name=john_name, mboxes={john_mail}, short_bio_en=john_bio_en)

    def create_rsa_key(self):
        return rsa_model.create(exponent=key_exponent, modulus=key_modulus, label=key_label)

    def create_gpg_key(self):
        return gpg_model.create(fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)

    def test_bio_requirement(self):
        bob = lp_model.new()
        bob.name = bob_name
        bob.blog = bob_blog
        bob.mboxes = {bob_email1}

        self.assertFalse(bob.is_valid())
        self.assertRaises(OMRequiredPropertyError, bob.save)

        # Bio is required
        bob.short_bio_en = bob_bio_en
        self.assertTrue(bob.is_valid())
        bob.save()

    def test_person_types(self):
        bob = self.create_bob()
        expected_types = ["http://example.com/vocab#LocalPerson",
                          "http://xmlns.com/foaf/0.1/Person"]
        self.assertEquals(bob.types, expected_types)

        # Check the triplestore
        type_request = """SELECT ?t WHERE {?x a ?t }"""
        retrieved_types = {str(r) for r, in data_graph.query(type_request, initBindings={'x': URIRef(bob.id)})}
        self.assertEquals(set(expected_types), retrieved_types)

    def test_bob_in_triplestore(self):
        request = """ASK { ?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertFalse(bool(data_graph.query(request)))
        self.create_bob()
        self.assertTrue(bool(data_graph.query(request)))

    def test_bob_attributes(self):
        bob = self.create_bob()
        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)

    def test_bob_loading(self):
        bob = self.create_bob()
        bob_uri = bob.id

        # Not saved
        bob.name = "You should not retrieve this string"

        del bob
        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_uri)

        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)

    def test_string_validation(self):
        bob = self.create_bob()
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.name = 2

    def test_not_saved(self):
        bob = self.create_bob()
        new_name = "Fake Bob"
        bob.name = new_name
        # Not saved
        self.assertFalse(bool(data_graph.query("""ASK {?x foaf:name "%s"^^xsd:string }""" % new_name)))

    def test_objects_access(self):
        """ Object manager is only accessible at the class level """
        bob = self.create_bob()
        self.assertRaises(AttributeError, getattr, bob, "objects")

    def test_multiple_mboxes(self):
        bob = self.create_bob()
        email3 = "bob-fake@bob.example.org"
        bob.mboxes = {bob_email2, email3}
        bob.save()

        mbox_query = """ASK {?x foaf:mbox "%s"^^xsd:string }"""
        self.assertTrue(bool(data_graph.query(mbox_query % bob_email2)))
        self.assertTrue(bool(data_graph.query(mbox_query % email3)))
        # Has been removed
        self.assertFalse(bool(data_graph.query(mbox_query % bob_email1)))

    def test_list_assignment_instead_of_set(self):
        bob = lp_model.new()
        bob.name = bob_name
        bob.short_bio_en = bob_bio_en

        # List assignment instead of a set
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.mboxes = [bob_email1, bob_email2]

    def test_reset(self):
        bob = self.create_bob()
        bob.short_bio_en = None
        bob.save()
        bob_uri = bob.id
        del bob
        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_uri)

        self.assertEquals(bob.short_bio_en, None)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

    def test_reset_and_requirement(self):
        bob = self.create_bob()
        bob.short_bio_en = None
        self.assertTrue(bob.is_valid())
        bob.short_bio_fr = None
        self.assertFalse(bob.is_valid())

    def test_language(self):
        bob = self.create_bob()
        bob.short_bio_en = None
        bob.save()
        bob_id = bob.id

        # To make sure this object won't be retrieved in the cache
        forbidden_string = "You should not retrieve this string"
        bob.short_bio_en = forbidden_string
        self.assertEquals(bob.short_bio_en, forbidden_string)

        del bob
        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_id)
        self.assertEquals(bob.short_bio_en, None)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

        bob_bio_en_2 = "Test-driven developer."
        bob.short_bio_en = bob_bio_en_2
        bob.save()
        bob.short_bio_en = "You should not retrieve this string (again)"

        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_id)
        self.assertEquals(bob.short_bio_en, bob_bio_en_2)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

    def test_rsa_key(self):
        rsa_key = self.create_rsa_key()
        rsa_skolemized_iri = rsa_key.id
        del rsa_key
        manager.clear_resource_cache()

        rsa_key = rsa_model.get(id=rsa_skolemized_iri)
        self.assertEquals(rsa_key.exponent, key_exponent)
        self.assertEquals(rsa_key.modulus, key_modulus)
        self.assertEquals(rsa_key.label, key_label)
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key.exponent = "String not a int"
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key.modulus = "not an hexa value"
        # Values should already be encoded in hexadecimal strings
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key.modulus = 235
        rsa_key.modulus = format(235, "x")
        with self.assertRaises(OMRequiredPropertyError):
            rsa_model.create(exponent=key_exponent)

    def test_filter_two_bobs(self):
        #Bob 1
        self.create_bob()

        bob2_mail = "bob2@example.org"
        bob2_bio_en = "I am a double."
        # Bob 2
        lp_model.create(name=bob_name, mboxes={bob2_mail}, short_bio_en=bob2_bio_en)

        bobs = list(lp_model.filter(name=bob_name))
        self.assertEquals(len(bobs), 2)
        self.assertEquals(bobs[0].name, bobs[1].name)
        self.assertEquals(bobs[0].name, bob_name)
        self.assertNotEquals(bobs[0].mboxes, bobs[1].mboxes)

        bobs2 = set(lp_model.filter(name=bob_name,
                                               # mboxes is NOT REQUIRED to be exhaustive
                                               mboxes={bob_email2}))
        self.assertEquals(len(bobs2), 1)
        bobs3 = set(lp_model.filter(name=bob_name,
                                               mboxes={bob_email1, bob_email2}))
        self.assertEquals(bobs2, bobs3)

        # Nothing
        bobs4 = list(lp_model.filter(name=bob_name,
                                                mboxes={bob_email1, bob_email2, bob2_mail}))
        self.assertEquals(len(bobs4), 0)

    def test_wrong_filter(self):
        with self.assertRaises(OMAttributeAccessError):
            lp_model.filter(undeclared_attr="not in datastore")

    def test_set_validation(self):
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set
            lp_model.create(name="Lola", mboxes="lola@example.org",
                                       short_bio_en="Will not exist.")
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set not a list
            lp_model.create(name="Lola", mboxes=["lola@example.org"],
                                       short_bio_en="Will not exist.")

    def test_children_object_assignment(self):
        bob = self.create_bob()
        alice = self.create_alice()
        john = self.create_john()

        # Children
        bob_children = [alice, john]
        bob_children_ids = [c.id for c in bob_children]
        bob.children = bob_children
        bob_uri = bob.id
        bob.save()

        # Force reload from the triplestore
        del bob
        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_uri)
        self.assertEquals(bob_children_ids, [c.id for c in bob.children])

    def test_children_uri_assignment(self):
        bob = self.create_bob()
        alice = self.create_alice()
        john = self.create_john()

        bob_uri = bob.id
        bob_children_uris = [alice.id, john.id]
        bob.children = bob_children_uris
        bob.save()

        # Force reload from the triplestore
        del bob
        manager.clear_resource_cache()

        bob = lp_model.get(id=bob_uri)
        self.assertEquals(bob.id, bob_uri)
        self.assertEquals(bob.name, bob_name)
        self.assertEquals(bob_children_uris, [c.id for c in bob.children])

    def test_set_assignment_instead_of_list(self):
        bob = self.create_bob()
        alice = self.create_alice()
        john = self.create_john()

        #Set assignment instead of a list
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.children = {alice.id, john.id}

    def test_children_list(self):
        bob = self.create_bob()
        bob_iri = bob.id
        alice = self.create_alice()
        john = self.create_john()

        # Children
        bob_children = [alice, john]
        bob.children = bob_children
        bob.save()

        children_request = """SELECT ?child
                              WHERE
                              { <%s> rel:parentOf ?children.
                                ?children rdf:rest*/rdf:first ?child
                              } """ % bob.id
        children_found = [str(r) for r, in data_graph.query(children_request)]
        #print default_graph.serialize(format="turtle")
        # No guarantee about the order
        self.assertEquals(set(children_found), set([c.id for c in bob_children]))

        bob_children_iris = [c.id for c in bob_children]
        del bob
        manager.clear_resource_cache()
        bob = manager.get(id=bob_iri)
        self.assertEquals([c.id for c in bob.children], bob_children_iris)

    def test_bob_json(self):
        bob = self.create_bob()
        bob_json = json.loads(bob.to_json())
        self.assertEquals(bob_json["name"], bob_name)
        self.assertEquals(bob_json["blog"], bob_blog)
        self.assertEquals(set(bob_json["mboxes"]), bob_emails)
        self.assertEquals(bob_json["short_bio_en"], bob_bio_en)
        self.assertEquals(bob_json["short_bio_fr"], bob_bio_fr)
        self.assertEquals(bob_json["types"], lp_model.ancestry_iris)

    def test_bob_jsonld(self):
        bob = self.create_bob()
        bob_jsonld = json.loads(bob.to_jsonld())
        self.assertEquals(bob_jsonld["name"], bob_name)
        self.assertEquals(bob_jsonld["blog"], bob_blog)
        self.assertEquals(set(bob_jsonld["mboxes"]), bob_emails)
        self.assertEquals(bob_jsonld["short_bio_en"], bob_bio_en)
        self.assertEquals(bob_jsonld["short_bio_fr"], bob_bio_fr)
        self.assertTrue("@context" in bob_jsonld)
        self.assertEquals(bob_jsonld["@context"], context["@context"])
        self.assertEquals(bob_jsonld["types"], lp_model.ancestry_iris)

    def test_rsa_jsonld(self):
        rsa_key = self.create_rsa_key()
        key_jsonld = json.loads(rsa_key.to_jsonld())
        self.assertEquals(key_jsonld["modulus"], key_modulus)
        self.assertEquals(key_jsonld["exponent"], key_exponent)
        self.assertEquals(key_jsonld["label"], key_label)
        # Blank node so IRI must not appear
        self.assertFalse("id" in key_jsonld)

    def test_rdf(self):
        bob = self.create_bob()
        bob_uri = URIRef(bob.id)
        g = Graph()
        g.parse(data=bob.to_rdf("turtle"), format="turtle")
        self.assertEquals(g.value(bob_uri, URIRef(FOAF + "name")).toPython(), bob_name)
        self.assertEquals(g.value(bob_uri, URIRef(FOAF + "weblog")).toPython(), bob_blog)
        self.assertEquals({mbox.toPython() for mbox in g.objects(bob_uri, URIRef(FOAF + "mbox"))},
                          bob_emails)
        self.assertEquals({bio.toPython() for bio in g.objects(bob_uri, URIRef(BIO + "olb"))},
                          {bob_bio_en, bob_bio_fr})

    def test_is_blank_node(self):
        bob = self.create_bob()
        self.assertFalse(bob.is_blank_node())
        alice = lp_model.new()
        self.assertFalse(alice.is_blank_node())

        raoul = lp_model.new(id="http://localhost/.well-known/genid/2387335")
        self.assertTrue(raoul.is_blank_node())

    def test_same_document(self):
        bob = self.create_bob()
        alice = self.create_alice()
        self.assertFalse(bob.in_same_document(alice))

        partial_uri = u"http://localhost/persons"
        bob_uri = partial_uri + "#bob"
        bob = lp_model.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = partial_uri + "#alice"
        alice = lp_model.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
                                           short_bio_en=alice_bio_en)
        self.assertTrue(bob.in_same_document(alice))

    def test_children_jsonld(self):
        bob = self.create_bob()
        alice = self.create_alice()
        john = self.create_john()
        bob_children = [alice, john]
        bob.children = bob_children
        bob.save()

        bob_jsonld = json.loads(bob.to_jsonld())
        self.assertEquals(bob_jsonld["name"], bob_name)
        self.assertEquals(bob_jsonld["blog"], bob_blog)
        self.assertEquals(set(bob_jsonld["mboxes"]), bob_emails)
        self.assertEquals(bob_jsonld["short_bio_en"], bob_bio_en)
        self.assertEquals(bob_jsonld["short_bio_fr"], bob_bio_fr)
        self.assertEquals(bob_jsonld["@context"], context["@context"])
        self.assertEquals(bob_jsonld["children"], [c.id for c in bob_children])

    def test_friendship_jsonld(self):
        friendship_uri = u"http://localhost/friendship"
        bob_uri = friendship_uri + "#bob"
        bob = lp_model.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = friendship_uri + "#alice"
        alice = lp_model.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
                                           short_bio_en=alice_bio_en)
        bob_friends = {alice}
        bob.friends = bob_friends
        bob.save()
        alice_friends = {bob}
        alice.friends = alice_friends
        alice.save()

        bob_jsonld = json.loads(bob.to_jsonld())
        self.assertEquals([c["id"] for c in bob_jsonld["friends"]],
                          [c.id for c in bob_friends])
        self.assertEquals(["@context" in c for c in bob_jsonld["friends"]],
                          [False])
        self.assertEquals(bob_jsonld["friends"][0]["friends"][0], bob_uri)

    def test_friendship_rdf(self):
        friendship_uri = u"http://localhost/friendship"
        bob_uri = friendship_uri + "#bob"
        bob = lp_model.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = friendship_uri + "#alice"
        alice = lp_model.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
                                           short_bio_en=alice_bio_en)
        bob_friends = {alice}
        bob.friends = bob_friends
        bob.save()
        alice_friends = {bob}
        alice.friends = alice_friends
        alice.save()

        g = Graph()
        g.parse(data=bob.to_rdf("turtle"), format="turtle")
        self.assertEquals(g.value(URIRef(bob_uri), URIRef(FOAF + "knows")).toPython(), alice_uri)
        self.assertEquals(g.value(URIRef(bob_uri), URIRef(FOAF + "name")).toPython(), bob_name)
        self.assertEquals(g.value(URIRef(alice_uri), URIRef(FOAF + "name")).toPython(), alice_name)

    def test_bob_key_jsonld(self):
        bob = self.create_bob()
        bob_iri = bob.id
        rsa_key = self.create_rsa_key()
        bob.keys = {rsa_key}
        bob.save()
        del bob
        del rsa_key
        manager.clear_resource_cache()

        bob = lp_model.get(id=bob_iri)
        bob_jsonld = json.loads(bob.to_jsonld())
        self.assertEquals(bob_jsonld["name"], bob_name)
        self.assertEquals(bob_jsonld["short_bio_en"], bob_bio_en)

        key_jsonld = bob_jsonld["keys"][0]
        self.assertEquals(key_jsonld["modulus"], key_modulus)
        self.assertEquals(key_jsonld["exponent"], key_exponent)
        self.assertEquals(key_jsonld["label"], key_label)
        self.assertFalse("id" in key_jsonld)
        self.assertFalse("@context" in key_jsonld)

    def test_out_of_band_update(self):
        jason_uri = URIRef("https://example.com/jason#me")
        data_graph.add((jason_uri, URIRef(FOAF + "name"), Literal("Jason")))
        data_graph.add((jason_uri, URIRef(BIO + "olb"), Literal("Jason was a warrior", lang="en")))

        # LocalPerson and Person types are missing
        with self.assertRaises(OMClassInstanceError):
            lp_model.get(id=str(jason_uri))

        for class_iri in lp_model.ancestry_iris:
            data_graph.add((jason_uri, RDF.type, URIRef(class_iri)))

        # Mboxes is still missing
        manager.clear_resource_cache()
        jason = lp_model.get(id=str(jason_uri))
        self.assertFalse(jason.is_valid())

        mboxes = {"jason@example.com", "jason@example.org"}
        data_graph.parse(data=json.dumps({"@id": jason_uri,
                                          "@type": ["LocalPerson", "Person"],
                                          # Required
                                          "mboxes": list(mboxes)}),
                         context=context, format="json-ld")

        # Clear the cache (out-of-band update)
        manager.clear_resource_cache()
        jason = lp_model.get(id=jason_uri)
        self.assertEquals(jason.mboxes, mboxes)
        self.assertTrue(jason.is_valid())

    def test_iri_uniqueness(self):
        bob = self.create_bob()
        bob_iri = bob.id

        with self.assertRaises(OMUniquenessError):
            lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist")

        with self.assertRaises(OMUniquenessError):
            lp_model.create(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist")

        with self.assertRaises(OMUniquenessError):
            lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist", create=True)

        # Forces the creation (by claiming your are not)
        # Dangerous!
        short_bio_en = u"Is forced to exist"
        bob2 = lp_model.new(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=short_bio_en, is_new=False)
        self.assertEquals(bob2.short_bio_en, short_bio_en)

    def test_gpg_key(self):
        bob = self.create_bob()
        bob_id = bob.id
        bob.gpg_key = self.create_gpg_key()
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        bob.save()
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        del bob
        manager.clear_resource_cache()
        bob = lp_model.get(id=bob_id)
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

    def test_delete_bob(self):
        bob = self.create_bob()
        request = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertTrue(bool(data_graph.query(request)))

        bob.delete()
        self.assertFalse(bool(data_graph.query(request)))

    def test_delete_rsa_but_no_alice(self):
        ask_alice = """ASK {?x foaf:name "%s"^^xsd:string }""" % alice_name
        self.assertFalse(bool(data_graph.query(ask_modulus)))
        self.assertFalse(bool(data_graph.query(ask_alice)))

        bob = self.create_bob()
        alice = self.create_alice()
        rsa_key = self.create_rsa_key()
        bob.keys = {rsa_key}
        bob.children = [alice]
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_modulus)))
        self.assertTrue(bool(data_graph.query(ask_alice)))

        bob.delete()
        # Blank node is deleted
        self.assertFalse(bool(data_graph.query(ask_modulus)))
        # Alice is not (non-blank)
        self.assertTrue(bool(data_graph.query(ask_alice)))

    def test_rsa_key_removal(self):
        self.assertFalse(bool(data_graph.query(ask_modulus)))

        bob = self.create_bob()
        rsa_key = self.create_rsa_key()
        bob.keys = {rsa_key}
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_modulus)))

        bob.keys = None
        bob.save()
        self.assertFalse(bool(data_graph.query(ask_modulus)))

    def test_gpg_key_removal(self):
        bob = self.create_bob()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = self.create_gpg_key()
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        bob.gpg_key = None
        bob.save()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

    def test_delete_gpg(self):
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

        bob = self.create_bob()
        gpg_key = self.create_gpg_key()
        self.assertEquals(gpg_key.fingerprint, gpg_fingerprint)
        bob.gpg_key = gpg_key
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        bob.delete()
        # Blank node is deleted
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

    def test_basic_bob_full_update(self):
        bob = self.create_bob()
        bob_dict = bob.to_dict()
        boby_name = "Boby"
        bob_dict["name"] = boby_name
        bob.full_update(bob_dict)
        self.assertEquals(bob.name, boby_name)

        bob_dict.pop("short_bio_en")
        bob.full_update(bob_dict)
        self.assertEquals(bob.short_bio_en, None)

    def test_bob_gpg_update(self):
        bob = self.create_bob()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = self.create_gpg_key()
        bob.save()
        #self.assertTrue(bool(default_graph.query("""ASK { GRAPH ?g {?x wot:fingerprint "%s"^^xsd:hexBinary } }""" % gpg_fingerprint)))
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))
        bob_dict = bob.to_dict()

        # GPG key blank-node is included as a dict
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.full_update(bob_dict)

        # Replace the dict by an IRI
        bob_dict["gpg_key"] = bob.gpg_key.id
        bob.full_update(bob_dict)
        bob.gpg_key.fingerprint = gpg_fingerprint

        bob_dict["gpg_key"] = None
        bob.full_update(bob_dict)
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

    def test_wrong_update(self):
        bob = self.create_bob()
        alice = self.create_alice()
        with self.assertRaises(OMWrongResourceError):
            bob.full_update(alice.to_dict())

        bob_dict = bob.to_dict()
        #Missing IRI
        bob_dict.pop("id")
        with self.assertRaises(OMWrongResourceError):
            bob.full_update(bob_dict)

        bob_dict = bob.to_dict()
        bob_dict["unknown_attribute"] = "Will cause a problem"
        with self.assertRaises(OMAttributeAccessError):
            bob.full_update(bob_dict)

    def test_basic_bob_graph_update(self):
        bob = self.create_bob()
        bob_iri = URIRef(bob.id)
        foaf_name = URIRef(FOAF + "name")
        olb = URIRef(BIO + "olb")
        graph = Graph()
        graph.parse(data=bob.to_rdf("xml"), format="xml")

        #Prevent a bug with JSON-LD -> RDF serializer
        #TODO: remove these lines when the bug will be fixed
        graph.remove((bob_iri, olb, Literal(bob_bio_fr, datatype=XSD.string)))
        graph.add((bob_iri, olb, Literal(bob_bio_fr, "fr")))

        graph.remove((bob_iri, foaf_name, Literal(bob_name, datatype=XSD.string)))
        boby_name = "Boby"
        graph.add((bob_iri, foaf_name, Literal(boby_name, datatype=XSD.string)))
        bob.full_update_from_graph(graph)
        self.assertEquals(bob.name, boby_name)

        graph.remove((bob_iri, olb, Literal(bob_bio_en, "en")))
        bob.full_update_from_graph(graph)
        self.assertEquals(bob.short_bio_en, None)

    def test_bob_controller_get(self):
        bob = self.create_bob()
        bob_iri = bob.id
        bob_base_iri = bob.base_iri
        bob2 = crud_controller.get(bob_base_iri)

        self.assertEquals(bob.to_rdf("turtle"), bob2)
        self.assertEquals(bob.to_json(), crud_controller.get(bob_base_iri, "application/json"))
        self.assertEquals(bob.to_json(), crud_controller.get(bob_base_iri, "json"))
        self.assertEquals(bob.to_jsonld(), crud_controller.get(bob_base_iri, "application/ld+json"))
        self.assertEquals(bob.to_jsonld(), crud_controller.get(bob_base_iri, "json-ld"))
        self.assertEquals(bob.to_rdf("turtle"), crud_controller.get(bob_base_iri, "text/turtle"))
        self.assertEquals(bob.to_rdf("turtle"), crud_controller.get(bob_base_iri))

        with self.assertRaises(OMHashIriError):
            # Hash URI
            crud_controller.get(bob_base_iri + "#hashed")
        with self.assertRaises(OMObjectNotFoundError):
            crud_controller.get("http://nowhere/no-one", "text/turtle")

    def test_document_controller_get(self):
        bob = self.create_bob()
        bob_iri = bob.id
        doc_iri = bob_iri.split("#")[0]
        data_graph.add((URIRef(doc_iri), RDF.type, FOAF.Document))
        doc = json.loads(crud_controller.get(doc_iri, "json"))
        self.assertEquals(doc["id"], doc_iri)

        obj_iris = manager.model_registry.find_resource_iris(doc_iri)
        self.assertEquals({bob_iri, doc_iri}, obj_iris)

    def test_bob_controller_delete(self):
        ask_bob = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertFalse(bool(data_graph.query(ask_bob)))
        bob = self.create_bob()
        self.assertTrue(bool(data_graph.query(ask_bob)))
        bob_iri = bob.id
        doc_iri = bob_iri.split("#")[0]

        ask_alice = """ASK {?x foaf:name "%s"^^xsd:string }""" % alice_name
        self.assertFalse(bool(data_graph.query(ask_alice)))
        lp_model.create(id=(doc_iri + "#alice"), name=alice_name, mboxes={alice_mail},
                                   short_bio_en=alice_bio_en)
        self.assertTrue(bool(data_graph.query(ask_alice)))

        #John is the base uri (bad practise, only for test convenience)
        ask_john = """ASK {?x foaf:name "%s"^^xsd:string }""" % john_name
        self.assertFalse(bool(data_graph.query(ask_john)))
        lp_model.create(id=doc_iri, name=john_name, mboxes={john_mail},
                                   short_bio_en=john_bio_en)
        self.assertTrue(bool(data_graph.query(ask_john)))

        crud_controller.delete(doc_iri)
        self.assertFalse(bool(data_graph.query(ask_bob)))
        self.assertFalse(bool(data_graph.query(ask_alice)))
        self.assertFalse(bool(data_graph.query(ask_john)))

    def test_controller_put_implicit_removal(self):
        """
            Please mind that putting two resources that have the same base IRI
            and letting them alone is a BAD practise.

            For test ONLY!
        """
        ask_bob = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertFalse(bool(data_graph.query(ask_bob)))
        bob = self.create_bob()
        self.assertTrue(bool(data_graph.query(ask_bob)))
        bob_iri = bob.id
        doc_iri = bob_iri.split("#")[0]

        ask_alice = """ASK {?x foaf:name "%s"^^xsd:string }""" % alice_name
        self.assertFalse(bool(data_graph.query(ask_alice)))
        lp_model.create(id=(doc_iri + "#alice"), name=alice_name, mboxes={alice_mail},
                                   short_bio_en=alice_bio_en)
        self.assertTrue(bool(data_graph.query(ask_alice)))

        g = Graph()
        bob_rdf = bob.to_rdf("turtle")
        g.parse(data=bob_rdf, format="turtle")
        #No Alice
        crud_controller.update(doc_iri, g.serialize(format="turtle"), "turtle")

        self.assertTrue(bool(data_graph.query(ask_bob)))
        # Should disappear because not in graph
        self.assertFalse(bool(data_graph.query(ask_alice)))

    def test_controller_put_change_name(self):
        bob = self.create_bob()
        doc_iri = bob.base_iri
        alice = lp_model.create(id=(doc_iri + "#alice"), name=alice_name, mboxes={alice_mail},
                                short_bio_en=alice_bio_en)
        alice_ref = URIRef(alice.id)
        bob_ref = URIRef(bob.id)
        new_alice_name = alice_name + " A."
        new_bob_name = bob_name + " B."

        g1 = Graph()
        g1.parse(data=data_graph.serialize())
        g1.remove((alice_ref, FOAF.name, Literal(alice_name, datatype=XSD.string)))
        g1.add((alice_ref, FOAF.name, Literal(new_alice_name, datatype=XSD.string)))
        g1.remove((bob_ref, FOAF.name, Literal(bob_name, datatype=XSD.string)))
        g1.add((bob_ref, FOAF.name, Literal(new_bob_name, datatype=XSD.string)))

        crud_controller.update(doc_iri, g1.serialize(format="turtle"), "turtle")
        self.assertEquals({unicode(o) for o in data_graph.objects(alice_ref, FOAF.name)}, {new_alice_name})
        self.assertEquals({unicode(o) for o in data_graph.objects(bob_ref, FOAF.name)}, {new_bob_name})

        g2 = Graph()
        g2.parse(data=data_graph.serialize())
        g2.remove((alice_ref, FOAF.name, Literal(new_alice_name, datatype=XSD.string)))
        # Alice name is required
        with self.assertRaises(OMEditError):
            crud_controller.update(doc_iri, g2.serialize(format="turtle"), "turtle")

    def test_controller_put_json(self):
        alice = self.create_alice()
        alice_iri = alice.id
        alice_base_iri = alice.base_iri
        alice_ref = URIRef(alice_iri)

        new_alice_name = "New alice"
        alice.name = new_alice_name
        js_dump = alice.to_json()
        new_new_alice_name = "New new alice"
        alice.name = new_new_alice_name
        jsld_dump = alice.to_jsonld()

        del alice
        manager.clear_resource_cache()
        self.assertEquals(unicode(data_graph.value(alice_ref, FOAF.name)), alice_name)

        crud_controller.update(alice_base_iri, jsld_dump, "application/ld+json")
        self.assertEquals(unicode(data_graph.value(alice_ref, FOAF.name)), new_new_alice_name)

        crud_controller.update(alice_base_iri, js_dump, "application/json")
        self.assertEquals(unicode(data_graph.value(alice_ref, FOAF.name)), new_alice_name)



    def test_controller_put_scope(self):
        alice = self.create_alice()
        alice_ref = URIRef(alice.id)
        bob = self.create_bob()
        bob_base_iri = bob.base_iri

        bob_graph = Graph().parse(data=bob.to_rdf("xml"), format="xml")
        # No problem
        crud_controller.update(bob_base_iri, bob_graph.serialize(format="turtle"), "turtle")

        new_alice_name = alice_name + " A."
        bob_graph.add((alice_ref, FOAF.name, Literal(new_alice_name, datatype=XSD.string)))
        with self.assertRaises(OMDifferentBaseIRIError):
            crud_controller.update(bob_base_iri, bob_graph.serialize(format="xml"), "xml")

    def test_controller_put_skolemized_iris(self):
        alice = self.create_alice()
        alice.gpg_key = self.create_gpg_key()
        alice.save()
        gpg_skolem_ref = URIRef(alice.gpg_key.id)
        self.assertTrue(alice.gpg_key.is_blank_node())

        bob = self.create_bob()
        bob_graph = Graph().parse(data=bob.to_rdf("xml"), format="xml")
        crud_controller.update(bob.base_iri, bob_graph.serialize(format="turtle"), "turtle")

        wot_fingerprint = URIRef(WOT + "fingerprint")
        bob_graph.add((gpg_skolem_ref, wot_fingerprint, Literal("DEADBEEF", datatype=XSD.hexBinary)))
        with self.assertRaises(OMForbiddenSkolemizedIRIError):
            crud_controller.update(bob.base_iri, bob_graph.serialize(format="turtle"), "turtle")

        # No modification
        self.assertEquals({unicode(r) for r in data_graph.objects(gpg_skolem_ref, wot_fingerprint)},
                          {gpg_fingerprint})

    def test_bob_additional_types(self):
        additional_types = [prof_type]
        bob = lp_model.new(name=bob_name, blog=bob_blog, mboxes=bob_emails, short_bio_en=bob_bio_en,
                           short_bio_fr=bob_bio_fr, types=additional_types)
        bob.save()
        self.assertEquals(set(bob.types), set(lp_model.ancestry_iris + additional_types))
        self.assertTrue(prof_type not in lp_model.ancestry_iris)

        additional_types += [researcher_type]
        bob.add_type(researcher_type)
        self.assertEquals(set(bob.types), set(lp_model.ancestry_iris + additional_types))
        self.assertTrue(researcher_type not in lp_model.ancestry_iris)

    def test_alice_json_update_types(self):
        alice = self.create_alice()
        dct = alice.to_dict()

        # New types
        additional_types = [prof_type, researcher_type]
        dct["types"] += additional_types
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.full_update(dct)
        alice.full_update(dct, allow_new_type=True)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris + additional_types))
        alice.full_update(dct)
        self.assertEquals(len(alice.types), len(set(alice.types)))

        # Removal of these additional types
        dct = alice.to_dict()
        dct["types"] = lp_model.ancestry_iris
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.full_update(dct)
        alice.full_update(dct, allow_type_removal=True)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris))

    def test_alice_rdf_update_types(self):
        alice = self.create_alice()
        alice_ref = URIRef(alice.id)
        alice_iri = alice.id

        g1 = Graph().parse(data=alice.to_rdf("turtle"), format="turtle")

        # New types
        g2 = Graph().parse(data=g1.serialize())
        additional_types = [prof_type, researcher_type]
        for t in additional_types:
            g2.add((alice_ref, RDF.type, URIRef(t)))

        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.full_update_from_graph(g2)
        alice.full_update_from_graph(g2, allow_new_type=True)

        del alice
        manager.clear_resource_cache()
        alice = lp_model.get(id=alice_iri)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris + additional_types))

        # Remove these new types
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.full_update_from_graph(g1)
        alice.full_update_from_graph(g1, allow_type_removal=True)
        del alice
        manager.clear_resource_cache()
        alice = lp_model.get(id=alice_iri)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris))

    def test_model_all(self):
        alice = self.create_alice()
        bob = self.create_bob()
        john = self.create_john()

        ids = {alice.id, bob.id, john.id}
        self.assertEquals({r.id for r in lp_model.all()}, ids)

    def test_sparql_filter(self):
        alice = self.create_alice()
        bob = self.create_bob()
        john = self.create_john()
        ids = {alice.id, bob.id, john.id}

        r1 = "SELECT ?s WHERE { ?s a foaf:Person }"
        self.assertEquals({r.id for r in manager.sparql_filter(r1)}, ids)

        r2 = """SELECT ?s WHERE {
            ?s a foaf:Person ;
               foaf:name "%s"^^xsd:string .
        }""" % alice_name
        self.assertEquals({r.id for r in manager.sparql_filter(r2)}, {alice.id})

        r3 = """SELECT ?name ?s WHERE {
            ?s foaf:name ?name .
        }"""
        # The names are used as IRIs (legal)
        self.assertEquals({r.id for r in manager.sparql_filter(r3)}, {alice_name, bob_name, john_name})

    def test_no_filter_get(self):
        self.assertEquals(manager.get(), None)
        alice = self.create_alice()
        # Unique object
        self.assertEquals(manager.get().id, alice.id)

    def test_empty_filter(self):
        """
            No filtering arguments -> all()
        """
        self.assertEquals(list(manager.filter()), [])
        alice = self.create_alice()
        # Unique object
        self.assertEquals(list(manager.filter())[0].id, alice.id)

        bob = self.create_bob()
        self.assertEquals({r.id for r in manager.filter()}, {alice.id, bob.id})
