# -*- coding: utf-8 -*-

from unittest import TestCase
from default_model import *


class UpdateDeleteTest(TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_out_of_band_update(self):
        jason_iri = URIRef(u"https://example.com/jason#me")
        data_graph.add((jason_iri, URIRef(FOAF + "name"), Literal("Jason")))
        data_graph.add((jason_iri, URIRef(BIO + "olb"), Literal("Jason was a warrior", lang="en")))

        # LocalPerson and Person types are missing
        with self.assertRaises(OMClassInstanceError):
            lp_model.get(id=str(jason_iri))
        # Cleans the cache
        data_store.resource_cache.remove_resource_from_id(jason_iri)

        for class_iri in lp_model.ancestry_iris:
            data_graph.add((jason_iri, RDF.type, URIRef(class_iri)))

        # Mboxes is still missing
        jason = lp_model.get(id=str(jason_iri))
        self.assertFalse(jason.is_valid())

        mboxes = {"jason@example.com", "jason@example.org"}
        data_graph.parse(data=json.dumps({"@id": jason_iri,
                                          "@type": ["LocalPerson", "Person"],
                                          # Required
                                          "mboxes": list(mboxes)}),
                         context=context, format="json-ld")

        # Clear the cache (out-of-band update)
        data_store.resource_cache.remove_resource(jason)
        jason = lp_model.get(id=jason_iri)
        self.assertEquals(jason.mboxes, mboxes)
        self.assertTrue(jason.is_valid())

    def test_delete_bob(self):
        req_name = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
        req_type = """ASK {?x a <%s> }""" % (MY_VOC + "LocalPerson")
        self.assertFalse(bool(data_graph.query(req_name)))
        self.assertFalse(bool(data_graph.query(req_type)))
        bob = create_bob()
        self.assertTrue(bool(data_graph.query(req_name)))
        self.assertTrue(bool(data_graph.query(req_type)))

        bob.delete()
        self.assertFalse(bool(data_graph.query(req_name)))
        self.assertFalse(bool(data_graph.query(req_type)))

    def test_delete_rsa_but_no_alice(self):
        ask_alice = """ASK {?x foaf:name "%s"^^xsd:string }""" % alice_name
        self.assertFalse(bool(data_graph.query(ask_modulus)))
        self.assertFalse(bool(data_graph.query(ask_alice)))

        bob = create_bob()
        alice = create_alice()
        rsa_key = create_rsa_key()
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

        bob = create_bob()
        rsa_key = create_rsa_key()
        bob.keys = {rsa_key}
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_modulus)))

        bob.keys = None
        bob.save()
        self.assertFalse(bool(data_graph.query(ask_modulus)))

    def test_gpg_key_removal(self):
        bob = create_bob()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = create_gpg_key()
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        bob.gpg_key = None
        bob.save()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

    def test_delete_gpg(self):
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

        bob = create_bob()
        gpg_key = create_gpg_key()
        self.assertEquals(gpg_key.fingerprint, gpg_fingerprint)
        bob.gpg_key = gpg_key
        bob.save()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        bob.delete()
        # Blank node is deleted
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

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

    def test_basic_bob_full_update(self):
        bob = create_bob()
        bob_dict = bob.to_dict()
        boby_name = "Boby"
        bob_dict["name"] = boby_name
        bob.full_update(bob_dict)
        self.assertEquals(bob.name, boby_name)

        bob_dict.pop("short_bio_en")
        bob.full_update(bob_dict)
        self.assertEquals(bob.short_bio_en, None)

    def test_bob_gpg_update(self):
        bob = create_bob()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = create_gpg_key()
        bob.save()
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
        bob = create_bob()
        alice = create_alice()
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
        bob = create_bob()
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

    def test_alice_json_update_types(self):
        alice = create_alice()
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
        alice = create_alice()
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

        # If any cache
        data_store.resource_cache.remove_resource(alice)
        alice = lp_model.get(id=alice_iri)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris + additional_types))

        # Remove these new types
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.full_update_from_graph(g1)
        alice.full_update_from_graph(g1, allow_type_removal=True)
        # If any cache
        data_store.resource_cache.remove_resource(alice)
        alice = lp_model.get(id=alice_iri)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris))

    def test_add_list_by_dict_update(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()

        # Not saved
        alice.children = [bob, john]
        children_iris = [bob.id, john.id]
        self.assertEquals([c.id for c in alice.children], children_iris)
        alice_dict = dict(alice.to_dict())
        alice.children = None
        self.assertEquals(alice.children, None)

        alice.full_update(alice_dict)
        self.assertEquals([c.id for c in alice.children], children_iris)

    def test_add_list_by_graph_update(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()

        # Not saved
        alice.children = [bob, john]
        children_iris = [bob.id, john.id]
        self.assertEquals([c.id for c in alice.children], children_iris)

        alice_graph = Graph().parse(data=alice.to_rdf(rdf_format="nt"), format="nt")
        alice.children = None
        self.assertEquals(alice.children, None)

        alice.full_update_from_graph(alice_graph)
        self.assertEquals([c.id for c in alice.children], children_iris)
