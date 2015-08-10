# -*- coding: utf-8 -*-

from unittest import TestCase
from rdflib import URIRef, Literal, RDF, XSD
from default_model import *
from oldman.exception import OMClassInstanceError, OMAttributeTypeCheckError, OMWrongResourceError, \
    OMAttributeAccessError, OMUnauthorizedTypeChangeError


class UpdateDeleteTest(TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_out_of_band_update(self):
        jason_iri = URIRef(u"https://example.com/jason#me")
        data_graph.add((jason_iri, URIRef(FOAF + "name"), Literal("Jason")))
        data_graph.add((jason_iri, URIRef(BIO + "olb"), Literal("Jason was a warrior", lang="en")))

        session1 = user_mediator.create_session()
        # LocalPerson and Person types are missing (required if we use MODEL.get(...) instead of session.get(...) )
        with self.assertRaises(OMClassInstanceError):
            lp_model.get(session1, iri=str(jason_iri))
        # But the object is available...
        session1.get(iri=str(jason_iri))
        # Cleans the cache
        data_store.resource_cache.remove_resource_from_iri(jason_iri)
        session1.close()

        for class_iri in lp_model.ancestry_iris:
            data_graph.add((jason_iri, RDF.type, URIRef(class_iri)))

        # Mboxes is still missing
        session2 = user_mediator.create_session()
        jason = lp_model.get(session2, iri=str(jason_iri))
        self.assertFalse(jason.is_valid())

        mboxes = {"jason@example.com", "jason@example.org"}
        data_graph.parse(data=json.dumps({"@id": jason_iri,
                                          "@type": ["LocalPerson", "Person"],
                                          # Required
                                          "mboxes": list(mboxes)}),
                         context=context, format="json-ld")

        # Clear the cache (out-of-band update)
        data_store.resource_cache.remove_resource(jason)
        session2.close()

        session3 = user_mediator.create_session()
        jason2 = session3.get(iri=jason_iri)
        self.assertEquals(jason2.mboxes, mboxes)
        self.assertTrue(jason2.is_valid())
        session3.close()

    def test_delete_bob(self):
        req_name = """ASK {?x foaf:name "%s"^^xsd:string }""" % bob_name
        req_type = """ASK {?x a <%s> }""" % (MY_VOC + "LocalPerson")
        self.assertFalse(bool(data_graph.query(req_name)))
        self.assertFalse(bool(data_graph.query(req_type)))
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        self.assertTrue(bool(data_graph.query(req_name)))
        self.assertTrue(bool(data_graph.query(req_type)))

        session1.delete(bob)
        session1.commit()
        self.assertFalse(bool(data_graph.query(req_name)))
        self.assertFalse(bool(data_graph.query(req_type)))
        session1.close()

    def test_delete_rsa_but_no_alice(self):
        ask_alice = """ASK {?x foaf:name "%s"^^xsd:string }""" % alice_name
        self.assertFalse(bool(data_graph.query(ask_modulus)))
        self.assertFalse(bool(data_graph.query(ask_alice)))

        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        alice = create_alice(session1)
        rsa_key = new_rsa_key(session1)
        bob.keys = {rsa_key}
        bob.children = [alice]
        session1.commit()
        self.assertTrue(bool(data_graph.query(ask_modulus)))
        self.assertTrue(bool(data_graph.query(ask_alice)))

        session1.delete(bob)
        session1.commit()
        session1.close()
        # Blank node is deleted
        self.assertFalse(bool(data_graph.query(ask_modulus)))
        # Alice is not (non-blank)
        self.assertTrue(bool(data_graph.query(ask_alice)))

    def test_rsa_key_removal(self):
        self.assertFalse(bool(data_graph.query(ask_modulus)))

        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        rsa_key = new_rsa_key(session1)
        bob.keys = {rsa_key}
        session1.commit()
        self.assertTrue(bool(data_graph.query(ask_modulus)))

        bob.keys = None
        session1.commit()
        session1.close()
        self.assertFalse(bool(data_graph.query(ask_modulus)))

    def test_gpg_key_removal(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = new_gpg_key(session1)
        session1.commit()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        bob.gpg_key = None
        session1.commit()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        session1.close()

    def test_delete_gpg(self):
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        gpg_key = new_gpg_key(session1)
        self.assertEquals(gpg_key.fingerprint, gpg_fingerprint)
        bob.gpg_key = gpg_key
        session1.commit()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))

        session1.delete(bob)
        session1.commit()
        session1.close()
        # Blank node is deleted
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))

    def test_bob_additional_types(self):
        additional_types = [prof_type]
        session1 = user_mediator.create_session()
        bob = lp_model.new(session1, name=bob_name, blog=bob_blog, mboxes=bob_emails, short_bio_en=bob_bio_en,
                           short_bio_fr=bob_bio_fr, types=additional_types)
        session1.commit()
        self.assertEquals(set(bob.types), set(lp_model.ancestry_iris + additional_types))
        self.assertTrue(prof_type not in lp_model.ancestry_iris)

        additional_types += [researcher_type]
        bob.add_type(researcher_type)
        self.assertEquals(set(bob.types), set(lp_model.ancestry_iris + additional_types))
        self.assertTrue(researcher_type not in lp_model.ancestry_iris)

    def test_basic_bob_full_update(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        bob_dict = bob.to_dict()
        boby_name = "Boby"
        bob_dict["name"] = boby_name
        bob.update(bob_dict)
        self.assertEquals(bob.name, boby_name)

        bob_dict.pop("short_bio_en")
        bob.update(bob_dict)
        self.assertEquals(bob.short_bio_en, None)
        session1.close()

    def test_bob_gpg_update(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        bob.gpg_key = new_gpg_key(session1)
        session1.commit()
        self.assertTrue(bool(data_graph.query(ask_fingerprint)))
        bob_dict = bob.to_dict()

        # GPG key blank-node is included as a dict
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.update(bob_dict)

        # Replace the dict by an IRI
        bob_dict["gpg_key"] = bob.gpg_key.id.iri
        bob.update(bob_dict)
        bob.gpg_key.fingerprint = gpg_fingerprint

        bob_dict["gpg_key"] = None
        bob.update(bob_dict)
        session1.commit()
        self.assertFalse(bool(data_graph.query(ask_fingerprint)))
        session1.close()

    def test_wrong_update(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        alice = create_alice(session1)
        with self.assertRaises(OMWrongResourceError):
            bob.update(alice.to_dict())

        bob_dict = bob.to_dict()
        #Missing IRI
        bob_dict.pop("id")
        with self.assertRaises(OMWrongResourceError):
            bob.update(bob_dict)

        bob_dict = bob.to_dict()
        bob_dict["unknown_attribute"] = "Will cause a problem"
        with self.assertRaises(OMAttributeAccessError):
            bob.update(bob_dict)
        session1.close()

    def test_basic_bob_graph_update(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        bob_iri = URIRef(bob.id.iri)
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
        bob.update_from_graph(graph)
        self.assertEquals(bob.name, boby_name)

        graph.remove((bob_iri, olb, Literal(bob_bio_en, "en")))
        bob.update_from_graph(graph)
        self.assertEquals(bob.short_bio_en, None)
        session1.close()

    def test_alice_json_update_types(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        dct = alice.to_dict()

        # New types
        additional_types = [prof_type, researcher_type]
        dct["types"] += additional_types
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.update(dct)
        alice.update(dct, allow_new_type=True)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris + additional_types))
        alice.update(dct)
        self.assertEquals(len(alice.types), len(set(alice.types)))

        # Removal of these additional types
        dct = alice.to_dict()
        dct["types"] = lp_model.ancestry_iris
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.update(dct)
        alice.update(dct, allow_type_removal=True)
        self.assertEquals(set(alice.types), set(lp_model.ancestry_iris))
        session1.close()

    def test_alice_rdf_update_types(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        alice_ref = URIRef(alice.id.iri)
        alice_iri = alice.id.iri

        g1 = Graph().parse(data=alice.to_rdf("turtle"), format="turtle")

        # New types
        g2 = Graph().parse(data=g1.serialize())
        additional_types = [prof_type, researcher_type]
        for t in additional_types:
            g2.add((alice_ref, RDF.type, URIRef(t)))

        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice.update_from_graph(g2)
        alice.update_from_graph(g2, allow_new_type=True)
        session1.commit()

        # If any cache
        data_store.resource_cache.remove_resource(alice)
        session1.close()

        session2 = user_mediator.create_session()
        alice2 = lp_model.get(session2, iri=alice_iri)
        self.assertEquals(set(alice2.types), set(lp_model.ancestry_iris + additional_types))

        # Remove these new types
        with self.assertRaises(OMUnauthorizedTypeChangeError):
            alice2.update_from_graph(g1)
        alice2.update_from_graph(g1, allow_type_removal=True)
        # If any cache
        data_store.resource_cache.remove_resource(alice)
        session2.close()

        session3 = user_mediator.create_session()
        alice3 = lp_model.get(session3, iri=alice_iri)
        self.assertEquals(set(alice3.types), set(lp_model.ancestry_iris))
        session3.close()

    def test_add_list_by_dict_update(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)

        # Not saved
        alice.children = [bob, john]
        children_iris = [bob.id.iri, john.id.iri]
        self.assertEquals([c.id.iri for c in alice.children], children_iris)
        alice_dict = dict(alice.to_dict())
        alice.children = None
        self.assertEquals(alice.children, None)

        alice.update(alice_dict)
        self.assertEquals([c.id.iri for c in alice.children], children_iris)
        session1.close()

    def test_add_list_by_graph_update(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)

        # Not saved
        alice.children = [bob, john]
        children_iris = [bob.id.iri, john.id.iri]
        self.assertEquals([c.id.iri for c in alice.children], children_iris)

        alice_graph = Graph().parse(data=alice.to_rdf(rdf_format="nt"), format="nt")
        alice.children = None
        self.assertEquals(alice.children, None)

        alice.update_from_graph(alice_graph)
        self.assertEquals([c.id.iri for c in alice.children], children_iris)
        session1.close()
