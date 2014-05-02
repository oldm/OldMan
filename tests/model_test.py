# -*- coding: utf-8 -*-

from unittest import TestCase
from rdflib import ConjunctiveGraph, Graph, URIRef, Literal, RDF
import json
from ld_orm import default_model_factory
from ld_orm.attribute import LDAttributeTypeCheckError, RequiredPropertyError
from ld_orm.exceptions import ClassInstanceError, LDAttributeAccessError, LDUniquenessError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

FOAF = "http://xmlns.com/foaf/0.1/"
BIO = "http://purl.org/vocab/bio/0.1/"
REL = "http://purl.org/vocab/relationship/"
CERT = "http://www.w3.org/ns/auth/cert#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"

my_voc_prefix = "http://example.com/vocab#"
local_person_def = {
    "@context": [
        {
            "myvoc": my_voc_prefix,
            "foaf": FOAF,
            "bio": BIO,
            "rel": REL,
            "cert": CERT
        },
        "http://www.w3.org/ns/hydra/core"
    ],
    "@id": "myvoc:LocalPerson",
    "@type": "hydra:Class",
    "subClassOf": "foaf:Person",
    "supportedProperty": [
        {
            "property": "foaf:name",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "foaf:mbox",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "foaf:weblog",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "bio:olb",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "foaf:knows",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "rel:parentOf",
            "required": False,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "cert:key",
            "required": False,
            "readonly": False,
            "writeonly": False
        }
    ]
}
schema_graph.parse(data=json.dumps(local_person_def), format="json-ld")

local_rsa_key_def = {
    "@context": [
        {
            "myvoc": my_voc_prefix,
            "rdfs": RDFS,
            "cert": CERT
        },
        "http://www.w3.org/ns/hydra/core"
    ],
    "@id": "myvoc:LocalRSAPublicKey",
    "@type": "hydra:Class",
    "subClassOf": "cert:RSAPublicKey",
    "supportedProperty": [
        {
            "property": "cert:exponent",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "cert:modulus",
            "required": True,
            "readonly": False,
            "writeonly": False
        },
        {
            "property": "rdfs:label",
            "required": False,
            "readonly": False,
            "writeonly": False
        }
    ]
}
schema_graph.parse(data=json.dumps(local_rsa_key_def), format="json-ld")

context = {
    "@context": {
        "myvoc": my_voc_prefix,
        "rdfs": RDFS,
        "foaf": "http://xmlns.com/foaf/0.1/",
        "bio": "http://purl.org/vocab/bio/0.1/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "rel": "http://purl.org/vocab/relationship/",
        "cert": CERT,
        "id": "@id",
        "type": "@type",
        "LocalPerson": "myvoc:LocalPerson",
        "Person": "foaf:Person",
        "LocalRSAPublicKey": "myvoc:LocalRSAPublicKey",
        "RSAPublicKey": "cert:RSAPublicKey",
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
            "@type": "xsd:string",
            "@language": "fr"
        },
        "short_bio_en": {
            "@id": "bio:olb",
            "@type": "xsd:string",
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
        }
    }
}


model_generator = default_model_factory(schema_graph, default_graph)
# Model class is generated here!
LocalPerson = model_generator.generate("LocalPerson", context,
                                       data_graph, uri_prefix="http://localhost/persons/",
                                       uri_fragment="me")
LocalRSAPublicKey = model_generator.generate("LocalRSAPublicKey", context, data_graph)

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


class ModelTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        LocalPerson.objects.clear_cache()
        LocalRSAPublicKey.objects.clear_cache()

    def create_bob(self):
        return LocalPerson.objects.create(name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                          short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)

    def create_alice(self):
        return LocalPerson.objects.create(name=alice_name, mboxes={alice_mail}, short_bio_en=alice_bio_en)

    def create_john(self):
        return LocalPerson.objects.create(name=john_name, mboxes={john_mail}, short_bio_en=john_bio_en)

    def create_rsa_key(self):
        return LocalRSAPublicKey.objects.create(exponent=key_exponent, modulus=key_modulus,
                                                label=key_label)

    def test_bio_requirement(self):
        bob = LocalPerson()
        bob.name = bob_name
        bob.blog = bob_blog
        bob.mboxes = {bob_email1}

        self.assertFalse(bob.is_valid())
        self.assertRaises(RequiredPropertyError, bob.save)

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
        retrieved_types = {str(r) for r, in data_graph.query(type_request,
                                                             initBindings={'x': URIRef(bob.id)})}
        self.assertEquals(set(expected_types), retrieved_types)

    def test_bob_in_triplestore(self):
        request = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
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
        LocalPerson.objects.clear_cache()
        bob = LocalPerson.objects.get(id=bob_uri)

        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)

    def test_string_validation(self):
        bob = self.create_bob()
        with self.assertRaises(LDAttributeTypeCheckError):
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

    def test_dict_attributes(self):
        bob = self.create_bob()
        # Because of descriptors, these attributes should not appear in __dict__ except id and _is_blank_node
        self.assertEquals(vars(bob).keys(), ["_id", "_is_blank_node"])

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
        bob = LocalPerson()
        bob.name = bob_name
        bob.short_bio_en = bob_bio_en

        # List assignment instead of a set
        with self.assertRaises(LDAttributeTypeCheckError):
            bob.mboxes = [bob_email1, bob_email2]

    def test_reset(self):
        bob = self.create_bob()
        bob.short_bio_en = None
        bob.save()
        bob_uri = bob.id
        del bob
        LocalPerson.objects.clear_cache()
        bob = LocalPerson.objects.get(id=bob_uri)

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
        LocalPerson.objects.clear_cache()
        bob = LocalPerson.objects.get(id=bob_id)
        self.assertEquals(bob.short_bio_en, None)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

        bob_bio_en_2 = "Test-driven developer."
        bob.short_bio_en = bob_bio_en_2
        bob.save()
        bob.short_bio_en = "You should not retrieve this string (again)"

        LocalPerson.objects.clear_cache()
        bob = LocalPerson.objects.get(id=bob_id)
        self.assertEquals(bob.short_bio_en, bob_bio_en_2)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

    def test_rsa_key(self):
        rsa_key = self.create_rsa_key()
        rsa_skolemized_iri = rsa_key.id
        del rsa_key
        LocalRSAPublicKey.objects.clear_cache()

        rsa_key = LocalRSAPublicKey.objects.get(id=rsa_skolemized_iri)
        self.assertEquals(rsa_key.exponent, key_exponent)
        self.assertEquals(rsa_key.modulus, key_modulus)
        self.assertEquals(rsa_key.label, key_label)
        with self.assertRaises(LDAttributeTypeCheckError):
            rsa_key.exponent = "String not a int"
        with self.assertRaises(LDAttributeTypeCheckError):
            rsa_key.modulus = "not an hexa value"
        # Values should already be encoded in hexadecimal strings
        with self.assertRaises(LDAttributeTypeCheckError):
            rsa_key.modulus = 235
        rsa_key.modulus = format(235, "x")
        with self.assertRaises(RequiredPropertyError):
            LocalRSAPublicKey.objects.create(exponent=key_exponent)

    def test_filter_two_bobs(self):
        #Bob 1
        self.create_bob()

        bob2_mail = "bob2@example.org"
        bob2_bio_en = "I am a double."
        # Bob 2
        LocalPerson.objects.create(name=bob_name, mboxes={bob2_mail}, short_bio_en=bob2_bio_en)

        bobs = list(LocalPerson.objects.filter(name=bob_name))
        self.assertEquals(len(bobs), 2)
        self.assertEquals(bobs[0].name, bobs[1].name)
        self.assertEquals(bobs[0].name, bob_name)
        self.assertNotEquals(bobs[0].mboxes, bobs[1].mboxes)

        bobs2 = set(LocalPerson.objects.filter(name=bob_name,
                                               # mboxes is NOT REQUIRED to be exhaustive
                                               mboxes={bob_email2}))
        self.assertEquals(len(bobs2), 1)
        bobs3 = set(LocalPerson.objects.filter(name=bob_name,
                                               mboxes={bob_email1, bob_email2}))
        self.assertEquals(bobs2, bobs3)

        # Nothing
        bobs4 = list(LocalPerson.objects.filter(name=bob_name,
                                                mboxes={bob_email1, bob_email2, bob2_mail}))
        self.assertEquals(len(bobs4), 0)

    def test_wrong_filter(self):
        with self.assertRaises(LDAttributeAccessError):
            LocalPerson.objects.filter(undeclared_attr="not in datastore")

    def test_set_validation(self):
        with self.assertRaises(LDAttributeTypeCheckError):
            # Mboxes should be a set
            LocalPerson.objects.create(name="Lola", mboxes="lola@example.org",
                                       short_bio_en="Will not exist.")
        with self.assertRaises(LDAttributeTypeCheckError):
            # Mboxes should be a set not a list
            LocalPerson.objects.create(name="Lola", mboxes=["lola@example.org"],
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
        LocalPerson.objects.clear_cache()
        bob = LocalPerson.objects.get(id=bob_uri)
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
        LocalPerson.objects.clear_cache()

        bob = LocalPerson.objects.get(id=bob_uri)
        self.assertEquals(bob.id, bob_uri)
        self.assertEquals(bob.name, bob_name)
        self.assertEquals(bob_children_uris, [c.id for c in bob.children])

    def test_set_assignment_instead_of_list(self):
        bob = self.create_bob()
        alice = self.create_alice()
        john = self.create_john()

        #Set assignment instead of a list
        with self.assertRaises(LDAttributeTypeCheckError):
            bob.children = {alice.id, john.id}

    def test_children_list(self):
        bob = self.create_bob()
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
        #print data_graph.serialize(format="turtle")
        # No guarantee about the order
        self.assertEquals(set(children_found), set([c.id for c in bob_children]))

    def test_bob_json(self):
        bob = self.create_bob()
        bob_json = json.loads(bob.to_json())
        self.assertEquals(bob_json["name"], bob_name)
        self.assertEquals(bob_json["blog"], bob_blog)
        self.assertEquals(set(bob_json["mboxes"]), bob_emails)
        self.assertEquals(bob_json["short_bio_en"], bob_bio_en)
        self.assertEquals(bob_json["short_bio_fr"], bob_bio_fr)

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
        alice = LocalPerson()
        self.assertFalse(alice.is_blank_node())

        raoul = LocalPerson(id="http://localhost/.well-known/genid/2387335")
        self.assertTrue(raoul.is_blank_node())

    def test_same_document(self):
        bob = self.create_bob()
        alice = self.create_alice()
        self.assertFalse(bob.in_same_document(alice))

        partial_uri = u"http://localhost/persons"
        bob_uri = partial_uri + "#bob"
        bob = LocalPerson.objects.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = partial_uri + "#alice"
        alice = LocalPerson.objects.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
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
        bob = LocalPerson.objects.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = friendship_uri + "#alice"
        alice = LocalPerson.objects.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
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
        bob = LocalPerson.objects.create(id=bob_uri, name=bob_name, blog=bob_blog, mboxes=bob_emails,
                                         short_bio_en=bob_bio_en, short_bio_fr=bob_bio_fr)
        alice_uri = friendship_uri + "#alice"
        alice = LocalPerson.objects.create(id=alice_uri, name=alice_name, mboxes={alice_mail},
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
        LocalPerson.objects.clear_cache()
        LocalRSAPublicKey.objects.clear_cache()

        bob = LocalPerson.objects.get(id=bob_iri)
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

        # LocalPerson type is missing
        with self.assertRaises(ClassInstanceError):
            LocalPerson.objects.get(id=str(jason_uri))

        data_graph.add((jason_uri, RDF["type"], URIRef(LocalPerson.class_uri)))

        # Mboxes is still missing
        jason = LocalPerson.objects.get(id=str(jason_uri))
        self.assertFalse(jason.is_valid())

        mboxes = {"jason@example.com", "jason@example.org"}
        data_graph.parse(data=json.dumps({"@id": jason_uri,
                                          "@type": ["LocalPerson", "Person"],
                                          # Required
                                          "mboxes": list(mboxes)}),
                         context=context,
                         format="json-ld")

        # Clear the cache (out-of-band update)
        LocalPerson.objects.clear_cache()
        jason = LocalPerson.objects.get(id=jason_uri)
        self.assertEquals(jason.mboxes, mboxes)
        self.assertTrue(jason.is_valid())

    def test_iri_uniqueness(self):
        bob = self.create_bob()
        bob_iri = bob.id

        with self.assertRaises(LDUniquenessError):
            LocalPerson(id=bob_iri, name=bob_name, mboxes=bob_emails, short_bio_en=u"Will not exist")

        with self.assertRaises(LDUniquenessError):
            LocalPerson.objects.create(id=bob_iri, name=bob_name, mboxes = bob_emails,
                                       short_bio_en=u"Will not exist")

        with self.assertRaises(LDUniquenessError):
            LocalPerson(id=bob_iri, name=bob_name, mboxes=bob_emails,
                        short_bio_en=u"Will not exist", create=True)

        # Forces the creation (by claiming your are not)
        # Dangerous!
        short_bio_en = u"Is forced to exist"
        bob2 = LocalPerson(id=bob_iri, name=bob_name, mboxes=bob_emails,
                           short_bio_en=short_bio_en, create=False)
        self.assertEquals(bob2.short_bio_en, short_bio_en)