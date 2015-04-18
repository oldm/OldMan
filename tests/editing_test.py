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

    def test_string_validation(self):
        bob = create_bob()
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.name = 2

    def test_person_types(self):
        bob = create_bob()
        expected_types = ["http://example.com/vocab#LocalPerson",
                          "http://xmlns.com/foaf/0.1/Person"]
        self.assertEquals(bob.types, expected_types)

        # Check the triplestore
        type_request = """SELECT ?t WHERE {?x a ?t }"""
        retrieved_types = {str(r) for r, in data_graph.query(type_request, initBindings={'x': URIRef(bob.id.iri)})}
        self.assertEquals(set(expected_types), retrieved_types)

    def test_bob_in_triplestore(self):
        request = """ASK { ?x foaf:name "%s"^^xsd:string }""" % bob_name
        self.assertFalse(bool(data_graph.query(request)))
        create_bob()
        self.assertTrue(bool(data_graph.query(request)))

    def test_bob_attributes(self):
        bob = create_bob()
        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id.iri)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)

    def test_bob_loading(self):
        bob = create_bob()
        bob_uri = bob.id.iri

        # Not saved
        bob.name = "You should not retrieve this string"

        # If any cache
        data_store.resource_cache.remove_resource(bob)
        bob = lp_model.get(iri=bob_uri)

        self.assertEquals(bob_name, bob.name)
        self.assertEquals(bob_blog, bob.blog.id.iri)
        self.assertEquals(bob_emails, bob.mboxes)
        self.assertEquals(bob_bio_en, bob.short_bio_en)
        self.assertEquals(bob_bio_fr, bob.short_bio_fr)

    def test_not_saved(self):
        bob = create_bob()
        new_name = "Fake Bob"
        bob.name = new_name
        # Not saved
        self.assertFalse(bool(data_graph.query("""ASK {?x foaf:name "%s"^^xsd:string }""" % new_name)))

    def test_multiple_mboxes(self):
        bob = create_bob()
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
        bob = create_bob()
        bob.short_bio_en = None
        bob.save()
        bob_iri = bob.id.iri
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        bob = lp_model.get(iri=bob_iri)

        self.assertEquals(bob.short_bio_en, None)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

    def test_reset_and_requirement(self):
        bob = create_bob()
        bob.short_bio_en = None
        self.assertTrue(bob.is_valid())
        bob.short_bio_fr = None
        self.assertFalse(bob.is_valid())

    def test_language(self):
        bob = create_bob()
        bob.short_bio_en = None
        bob.save()
        bob_iri = bob.id.iri

        # To make sure this object won't be retrieved in the cache
        forbidden_string = "You should not retrieve this string"
        bob.short_bio_en = forbidden_string
        self.assertEquals(bob.short_bio_en, forbidden_string)

        # If any cache
        data_store.resource_cache.remove_resource(bob)
        bob = lp_model.get(iri=bob_iri)
        self.assertEquals(bob.short_bio_en, None)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

        bob_bio_en_2 = "Test-driven developer."
        bob.short_bio_en = bob_bio_en_2
        bob.save()
        bob.short_bio_en = "You should not retrieve this string (again)"

        data_store.resource_cache.remove_resource(bob)
        bob = lp_model.get(iri=bob_iri)
        self.assertEquals(bob.short_bio_en, bob_bio_en_2)
        self.assertEquals(bob.short_bio_fr, bob_bio_fr)

    def test_rsa_key(self):
        rsa_key = create_rsa_key()
        rsa_skolemized_iri = rsa_key.id.iri
        # If any cache
        data_store.resource_cache.remove_resource(rsa_key)
        rsa_key = rsa_model.get(iri=rsa_skolemized_iri)
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

    def test_children_object_assignment(self):
        bob = create_bob()
        alice = create_alice()
        john = create_john()

        # Children
        bob_children = [alice, john]
        bob_children_ids = [c.id.iri for c in bob_children]
        bob.children = bob_children
        bob_uri = bob.id.iri
        bob.save()

        # Force reload from the triplestore
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(alice)
        data_store.resource_cache.remove_resource(john)
        bob = lp_model.get(iri=bob_uri)
        self.assertEquals(bob_children_ids, [c.id.iri for c in bob.children])

    def test_children_uri_assignment(self):
        bob = create_bob()
        alice = create_alice()
        john = create_john()

        bob_uri = bob.id.iri
        bob_children_uris = [alice.id.iri, john.id.iri]
        bob.children = bob_children_uris
        bob.save()

        # Force reload from the triplestore
        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(alice)
        data_store.resource_cache.remove_resource(john)

        bob = lp_model.get(iri=bob_uri)
        self.assertEquals(bob.id.iri, bob_uri)
        self.assertEquals(bob.name, bob_name)
        self.assertEquals(bob_children_uris, [c.id.iri for c in bob.children])

    def test_set_assignment_instead_of_list(self):
        bob = create_bob()
        alice = create_alice()
        john = create_john()

        #Set assignment instead of a list
        with self.assertRaises(OMAttributeTypeCheckError):
            bob.children = {alice.id.iri, john.id.iri}

    def test_children_list(self):
        bob = create_bob()
        bob_iri = bob.id.iri
        alice = create_alice()
        john = create_john()

        # Children
        bob_children = [alice, john]
        bob.children = bob_children
        bob.save()

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
        bob = user_mediator.get(iri=bob_iri)
        self.assertEquals([c.id.iri for c in bob.children], bob_children_iris)

    def test_set_validation(self):
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set
            lp_model.create(name="Lola", mboxes="lola@example.org", short_bio_en="Will not exist.")
        with self.assertRaises(OMAttributeTypeCheckError):
            # Mboxes should be a set not a list
            lp_model.create(name="Lola", mboxes=["lola@example.org"], short_bio_en="Will not exist.")

    def test_gpg_key(self):
        bob = create_bob()
        bob_iri = bob.id.iri
        bob.gpg_key = create_gpg_key()
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        bob.save()
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

        # If any cache
        data_store.resource_cache.remove_resource(bob)
        data_store.resource_cache.remove_resource(bob.gpg_key)
        bob = lp_model.get(iri=bob_iri)
        self.assertEquals(bob.gpg_key.fingerprint, gpg_fingerprint)
        self.assertEquals(bob.gpg_key.hex_id, gpg_hex_id)

    def test_inversed_property_set(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()
        john.parents = {bob}
        john.save()

        john_parent_bob_query = u"ASK { <%s> rel:parentOf <%s> . }" % (john.id, bob.id)
        bob_parent_john_query = u"ASK { <%s> rel:parentOf <%s> . }" % (bob.id, john.id)

        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertTrue(data_graph.query(bob_parent_john_query))

        john.parents = {alice}
        john.save()
        john_parent_alice_query = u"ASK { <%s> rel:parentOf <%s> . }" % (john.id, alice.id)
        alice_parent_john_query = u"ASK { <%s> rel:parentOf <%s> . }" % (alice.id, john.id)

        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertFalse(data_graph.query(bob_parent_john_query))
        self.assertFalse(data_graph.query(john_parent_alice_query))
        self.assertTrue(data_graph.query(alice_parent_john_query))

        john.parents = {bob.id.iri, alice.id.iri}
        john.save()
        self.assertFalse(data_graph.query(john_parent_bob_query))
        self.assertTrue(data_graph.query(bob_parent_john_query))
        self.assertFalse(data_graph.query(john_parent_alice_query))
        self.assertTrue(data_graph.query(alice_parent_john_query))


    def test_inversed_property_retrieval_set(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()
        john.parents = {alice, bob}
        john.save()
        self.assertEquals({alice.id.iri, bob.id.iri}, {p.id.iri for p in john.parents})

        # Loads John from the datastore (not from its cache)
        john_iri = john.id.iri
        data_store.resource_cache.remove_resource(john)
        john = lp_model.get(iri=john_iri)
        self.assertEquals({alice.id.iri, bob.id.iri}, {p.id.iri for p in john.parents})

    def test_inversed_property_single_value(self):
        alice = create_alice()
        bob = create_bob()
        bob.employer = alice
        bob.save()

        alice_employer_bob_query = u"ASK { <%s> schema:employee <%s> . }" % (bob.id.iri, alice.id.iri)
        bob_employer_alice_query = u"ASK { <%s> schema:employee <%s> . }" % (alice.id.iri, bob.id.iri)

        self.assertFalse(data_graph.query(alice_employer_bob_query))
        self.assertTrue(data_graph.query(bob_employer_alice_query))

        john = create_john()
        bob.employer = john
        bob.save()
        bob_employer_john_query = u"ASK { <%s> schema:employee <%s> . }" % (bob.id.iri, john.id.iri)
        john_employer_bob_query = u"ASK { <%s> schema:employee <%s> . }" % (john.id.iri, bob.id.iri)

        self.assertFalse(data_graph.query(alice_employer_bob_query))
        self.assertFalse(data_graph.query(bob_employer_alice_query))
        self.assertFalse(data_graph.query(bob_employer_john_query))
        self.assertTrue(data_graph.query(john_employer_bob_query))

    def test_inversed_property_retrieval_single_value(self):
        alice = create_alice()
        bob = create_bob()
        bob.employer = alice
        bob.save()
        self.assertEquals(alice.id.iri, bob.employer.id.iri)

        # Loads Bob from the datastore (not from its cache)
        bob_iri = bob.id.iri
        data_store.resource_cache.remove_resource(bob)
        bob = lp_model.get(iri=bob_iri)
        self.assertEquals(alice.id.iri, bob.employer.id.iri)

        # Checks if the datastore still extract reversed attributes
        # in "lazy" mode
        data_store.resource_cache.remove_resource(bob)
        bob = user_mediator.get(iri=bob_iri, eager_with_reversed_attributes=False)
        self.assertEquals(alice.id.iri, bob.employer.id.iri)

    def test_inversed_and_regular_update(self):
        alice = create_alice()
        bob = create_bob()
        bob.employer = alice
        bob.save()

        alice_iri = alice.id.iri
        alice = lp_model.get(alice_iri)
        self.assertTrue(alice.employee is not None)
        self.assertEquals(alice.employee.id.iri, bob.id.iri)

        alice.employee = None
        alice.save()

        bob_iri = bob.id.iri
        bob = lp_model.get(bob_iri)
        self.assertTrue(bob.employer is None)

    def test_inversed_property_cache_invalidation_after_deletion(self):
        alice = create_alice()
        bob = create_bob()
        bob.employer = alice
        bob.save()

        alice_iri = alice.id.iri
        alice = lp_model.get(alice_iri)
        self.assertTrue(alice.employee is not None)
        self.assertEquals(alice.employee.id.iri, bob.id.iri)

        bob.delete()
        alice = lp_model.get(alice_iri)
        self.assertTrue(alice.employee is None)
