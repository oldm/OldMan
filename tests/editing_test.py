import unittest
from rdflib import URIRef
from default_model import *
from oldman.exception import OMAttributeTypeCheckError, OMRequiredPropertyError


class BasicEditingTest(unittest.TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_bio_requirement(self):
        session = user_mediator.create_session()
        bob = lp_model.new(session)
        bob.name = bob_name
        bob.blog = bob_blog
        bob.mboxes = {bob_email1}

        self.assertFalse(bob.is_valid())
        self.assertRaises(OMRequiredPropertyError, session.commit)

        # Bio is required
        bob.short_bio_en = bob_bio_en
        self.assertTrue(bob.is_valid())
        session.commit()
        session.close()

    def test_string_validation(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.name = 2

    def test_person_types(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        expected_types = ["http://example.com/vocab#LocalPerson",
                          "http://xmlns.com/foaf/0.1/Person"]
        self.assertEquals(bob.types, expected_types)
        session.close()

        # Check the triplestore
        type_request = """SELECT ?t WHERE {?x a ?t }"""
        retrieved_types = {str(r) for r, in data_graph.query(type_request, initBindings={'x': URIRef(bob.id.iri)})}
        self.assertEquals(set(expected_types), retrieved_types)

    def test_bob_in_triplestore(self):
        request = """ASK { ?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertFalse(bool(data_graph.query(request)))
        session = user_mediator.create_session()
        create_bob(session)
        session.close()
        self.assertTrue(bool(data_graph.query(request)))

    def test_bob_attributes(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id.iri)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)
        session.close()

    def test_bob_loading(self):
        session1 = user_mediator.create_session()
        bob1 = create_bob(session1)
        bob_uri = bob1.id.iri

        # Not saved
        bob1.name = "You should not retrieve this string"

        # If any cache
        data_store.resource_cache.remove_resource(bob1)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_uri)

        self.assertEquals(bob_name, bob2.name)
        self.assertEquals(bob_blog, bob2.blog.id.iri)
        self.assertEquals(bob_emails, bob2.mboxes)
        self.assertEquals(bob_bio_en, bob2.short_bio_en)
        self.assertEquals(bob_bio_fr, bob2.short_bio_fr)
        session2.close()

    def test_not_saved(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        new_name = "Fake Bob"
        bob.name = new_name
        # Not saved
        self.assertFalse(bool(data_graph.query("""ASK {?x foaf:name "%s"^^xsd:string }""" % new_name)))
        session.close()

    def test_multiple_mboxes(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        email3 = "bob-fake@bob.example.org"
        bob.mboxes = {bob_email2, email3}
        session.commit()
        session.close()

        mbox_query = """ASK {?x foaf:mbox "%s"^^xsd:string }"""
        self.assertTrue(bool(data_graph.query(mbox_query % bob_email2)))
        self.assertTrue(bool(data_graph.query(mbox_query % email3)))
        # Has been removed
        self.assertFalse(bool(data_graph.query(mbox_query % bob_email1)))

    def test_list_assignment_instead_of_set(self):
        session = user_mediator.create_session()
        bob = lp_model.new(session)
        bob.name = bob_name
        bob.short_bio_en = bob_bio_en

        # List assignment instead of a set
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.mboxes = [bob_email1, bob_email2]
        session.close()

    def test_reset(self):
        session1 = user_mediator.create_session()
        bob1 = create_bob(session1)
        bob1.short_bio_en = None
        session1.commit()
        bob_iri = bob1.id.iri
        # If any cache
        data_store.resource_cache.remove_resource(bob1)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_iri)

        self.assertEquals(bob2.short_bio_en, None)
        self.assertEquals(bob2.short_bio_fr, bob_bio_fr)
        session2.close()

    def test_reset_and_requirement(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        bob.short_bio_en = None
        self.assertTrue(bob.is_valid())
        bob.short_bio_fr = None
        self.assertFalse(bob.is_valid())
        session1.close()

    def test_language(self):
        session1 = user_mediator.create_session()
        bob1 = create_bob(session1)
        bob1.short_bio_en = None
        session1.commit()
        bob_iri = bob1.id.iri

        # To make sure this object won't be retrieved in the cache
        forbidden_string = "You should not retrieve this string"
        bob1.short_bio_en = forbidden_string
        self.assertEquals(bob1.short_bio_en, forbidden_string)
        # If any cache
        data_store.resource_cache.remove_resource(bob1)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_iri)
        self.assertEquals(bob2.short_bio_en, None)
        self.assertEquals(bob2.short_bio_fr, bob_bio_fr)

        bob_bio_en_2 = "Test-driven developer."
        bob2.short_bio_en = bob_bio_en_2
        session2.commit()
        bob2.short_bio_en = "You should not retrieve this string (again)"
        data_store.resource_cache.remove_resource(bob2)
        session2.close()

        session3 = user_mediator.create_session()
        bob3 = lp_model.get(session3, iri=bob_iri)
        self.assertEquals(bob3.short_bio_en, bob_bio_en_2)
        self.assertEquals(bob3.short_bio_fr, bob_bio_fr)
        session3.close()

    def test_rsa_key(self):
        session1 = user_mediator.create_session()
        rsa_key1 = new_rsa_key(session1)
        session1.commit()
        rsa_skolemized_iri = rsa_key1.id.iri
        # If any cache
        data_store.resource_cache.remove_resource(rsa_key1)
        session1.close()

        session2 = user_mediator.create_session()
        rsa_key2 = rsa_model.get(session2, iri=rsa_skolemized_iri)
        self.assertEquals(rsa_key2.exponent, key_exponent)
        self.assertEquals(rsa_key2.modulus, key_modulus)
        self.assertEquals(rsa_key2.label, key_label)
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key2.exponent = "String not a int"
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key2.modulus = "not an hexa value"
        # Values should already be encoded in hexadecimal strings
        with self.assertRaises(OMAttributeTypeCheckError):
            rsa_key2.modulus = 235
        rsa_key2.modulus = format(235, "x")
        rsa_model.new(session2, exponent=key_exponent)
        with self.assertRaises(OMRequiredPropertyError):
            session2.commit()

        session2.close()

    def test_children_object_assignment(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        alice = create_alice(session1)
        john = create_john(session1)

        # Children
        bob_children = [alice, john]
        bob_children_ids = [c.id.iri for c in bob_children]
        bob.children = bob_children
        bob_uri = bob.id.iri
        session1.commit()

        # Force reload from the triplestore
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(alice)
        data_store.resource_cache.remove_resource(john)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_uri)
        self.assertEquals(bob_children_ids, [c.id.iri for c in bob2.children])
        session2.close()

    def test_children_uri_assignment(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        alice = create_alice(session1)
        john = create_john(session1)

        bob_uri = bob.id.iri
        bob_children_uris = [alice.id.iri, john.id.iri]
        bob.children = bob_children_uris
        session1.commit()

        # Force reload from the triplestore
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(alice)
        data_store.resource_cache.remove_resource(john)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_uri)
        self.assertEquals(bob2.id.iri, bob_uri)
        self.assertEquals(bob2.name, bob_name)
        self.assertEquals(bob_children_uris, [c.id.iri for c in bob2.children])
        session2.close()

    def test_set_assignment_instead_of_list(self):
        session = user_mediator.create_session()
        bob = create_bob(session)
        alice = create_alice(session)
        john = create_john(session)

        #Set assignment instead of a list
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.children = {alice.id.iri, john.id.iri}
        session.close()

    def test_children_list(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        bob_iri = bob.id.iri
        alice = create_alice(session1)
        john = create_john(session1)

        # Children
        bob_children = [alice, john]
        bob.children = bob_children
        session1.commit()

        children_request = """SELECT ?child
                              WHERE
                              { <%s> rel:parentOf ?children.
                                ?children rdf:rest*/rdf:first ?child
                              } """ % bob.id.iri
        children_found = [str(r) for r, in data_graph.query(children_request)]
        #print default_graph.serialize(format="turtle")
        # No guarantee about the order
        self.assertEquals(set(children_found), set([c.id.iri for c in bob_children]))

        bob_children_iris = [c.id.iri for c in bob_children]
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(alice)
        data_store.resource_cache.remove_resource(john)
        session1.close()

        session2 = user_mediator.create_session()
        bob = session2.get(iri=bob_iri)
        self.assertEquals([c.id.iri for c in bob.children], bob_children_iris)
        session2.close()

    def test_set_validation(self):
        session = user_mediator.create_session()
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set
            lp_model.new(session, name="Lola", mboxes="lola@example.org", short_bio_en="Will not exist.")
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set not a list
            lp_model.new(session, name="Lola", mboxes=["lola@example.org"], short_bio_en="Will not exist.")
        session.close()

    def test_gpg_key(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        bob_iri = bob.id.iri
        bob.gpg_key = new_gpg_key(session1)
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        session1.commit()
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(bob.gpg_key)
        session1.close()

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_iri)
        self.assertEquals(bob2.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob2.gpg_key.hex_id, gpg_hex_id)
        session2.close()

    def test_inversed_property_set(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)
        john.parents = {bob}
        session1.commit()

        john_parent_bob_query = u"ASK { <%s> rel:parentOf <%s> . }" % (john.id, bob.id)
        bob_parent_john_query = u"ASK { <%s> rel:parentOf <%s> . }" % (bob.id, john.id)

        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertTrue(data_graph.query(bob_parent_john_query))

        john.parents = {alice}
        session1.commit()
        john_parent_alice_query = u"ASK { <%s> rel:parentOf <%s> . }" % (john.id, alice.id)
        alice_parent_john_query = u"ASK { <%s> rel:parentOf <%s> . }" % (alice.id, john.id)

        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertFalse(data_graph.query(bob_parent_john_query))
        self.assertFalse(data_graph.query(john_parent_alice_query))
        self.assertTrue(data_graph.query(alice_parent_john_query))

        john.parents = {bob.id.iri, alice.id.iri}
        session1.commit()
        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertTrue(data_graph.query(bob_parent_john_query))
        self.assertFalse(data_graph.query(john_parent_alice_query))
        self.assertTrue(data_graph.query(alice_parent_john_query))
        session1.close()

    def test_inversed_property_retrieval_set(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)
        john.parents = {alice, bob}
        session1.commit()
        self.assertEquals({alice.id.iri, bob.id.iri}, {p.id.iri for p in john.parents})

        # Loads John from the datastore (not from its cache)
        john_iri = john.id.iri
        data_store.resource_cache.remove_resource(john)

        session2 = user_mediator.create_session()
        john2 = lp_model.get(session2, iri=john_iri)
        self.assertEquals({alice.id.iri, bob.id.iri}, {p.id.iri for p in john2.parents})
        session1.close()
        session2.close()

    def test_inversed_property_single_value(self):
        session = user_mediator.create_session()
        alice = create_alice(session)
        bob = create_bob(session)
        bob.employer = alice
        session.commit()

        alice_employer_bob_query = u"ASK { <%s> schema:employee <%s> . }" % (bob.id.iri, alice.id.iri)
        bob_employer_alice_query = u"ASK { <%s> schema:employee <%s> . }" % (alice.id.iri, bob.id.iri)

        self.assertFalse(data_graph.query(alice_employer_bob_query))
        self.assertTrue(data_graph.query(bob_employer_alice_query))

        john = create_john(session)
        bob.employer = john
        session.commit()
        bob_employer_john_query = u"ASK { <%s> schema:employee <%s> . }" % (bob.id.iri, john.id.iri)
        john_employer_bob_query = u"ASK { <%s> schema:employee <%s> . }" % (john.id.iri, bob.id.iri)

        self.assertFalse(data_graph.query(alice_employer_bob_query))
        self.assertFalse(data_graph.query(bob_employer_alice_query))
        self.assertFalse(data_graph.query(bob_employer_john_query))
        self.assertTrue(data_graph.query(john_employer_bob_query))
        session.close()

    def test_inversed_property_retrieval_single_value(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        bob.employer = alice
        session1.commit()
        self.assertEquals(alice.id.iri, bob.employer.id.iri)

        # Loads Bob from the datastore (not from its cache)
        bob_iri = bob.id.iri
        data_store.resource_cache.remove_resource(bob)

        session2 = user_mediator.create_session()
        bob2 = lp_model.get(session2, iri=bob_iri)
        self.assertEquals(alice.id.iri, bob2.employer.id.iri)

        # Checks if the datastore still extract reversed attributes
        # in "lazy" mode
        data_store.resource_cache.remove_resource(bob2)

        session3 = user_mediator.create_session()
        bob3 = session3.get(iri=bob_iri, eager_with_reversed_attributes=False)
        self.assertEquals(alice.id.iri, bob3.employer.id.iri)
        session1.close()
        session2.close()
        session3.close()

    def test_inversed_and_regular_update(self):
        session1 = user_mediator.create_session()
        alice1 = create_alice(session1)
        bob1 = create_bob(session1)
        bob1.employer = alice1
        session1.commit()

        alice_iri = alice1.id.iri

        session2 = user_mediator.create_session()
        alice2 = lp_model.get(session2, alice_iri)
        self.assertTrue(alice2.employee is not None)
        self.assertEquals(alice2.employee.id.iri, bob1.id.iri)

        alice2.employee = None
        session2.commit()

        bob_iri = bob1.id.iri
        session3 = user_mediator.create_session()
        bob2 = lp_model.get(session3, bob_iri)
        self.assertTrue(bob2.employer is None)

        session1.close()
        session2.close()
        session3.close()

    def test_inversed_property_cache_invalidation_after_deletion(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        bob.employer = alice
        session1.commit()
        alice_iri = alice.id.iri

        session2 = user_mediator.create_session()
        alice2 = lp_model.get(session2, alice_iri)
        self.assertTrue(alice2.employee is not None)
        self.assertEquals(alice2.employee.id.iri, bob.id.iri)

        session1.delete(bob)
        session1.commit()

        session3 = user_mediator.create_session()
        alice3 = lp_model.get(session3, alice_iri)
        self.assertTrue(alice3.employee is None)

        session1.close()
        session2.close()
        session3.close()
