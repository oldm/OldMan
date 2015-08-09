import unittest
from default_model import *
from oldman.exception import OMAttributeAccessError


class FindTest(unittest.TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_filter_two_bobs(self):
        session1 = user_mediator.create_session()
        #Bob 1
        create_bob(session1)

        bob2_mail = "bob2@example.org"
        bob2_bio_en = "I am a double."
        # Bob 2
        lp_model.new(session1, name=bob_name, mboxes={bob2_mail}, short_bio_en=bob2_bio_en)
        session1.commit()
        session1.close()

        session2 = user_mediator.create_session()
        bobs = list(lp_model.filter(session2, name=bob_name))
        self.assertEquals(len(bobs), 2)
        self.assertEquals(bobs[0].name, bobs[1].name)
        self.assertEquals(bobs[0].name, bob_name)
        self.assertNotEquals(bobs[0].mboxes, bobs[1].mboxes)
        session2.close()

        session3 = user_mediator.create_session()
        # mboxes is NOT REQUIRED to be exhaustive
        bobs2 = {r.id.iri for r in lp_model.filter(session3, name=bob_name, mboxes={bob_email2})}
        self.assertEquals(len(bobs2), 1)
        session3.close()

        session4 = user_mediator.create_session()
        bobs3 = {r.id.iri for r in lp_model.filter(session4, name=bob_name, mboxes={bob_email1, bob_email2})}
        self.assertEquals(bobs2, bobs3)
        session4.close()

        # Nothing
        session5 = user_mediator.create_session()
        bobs4 = {r.id.iri for r in lp_model.filter(session5, name=bob_name, mboxes={bob_email1, bob_email2, bob2_mail})}
        self.assertEquals(len(bobs4), 0)
        session5.close()

    def test_wrong_filter(self):
        session1 = user_mediator.create_session()
        with self.assertRaises(OMAttributeAccessError):
            lp_model.filter(session1, undeclared_attr="not in datastore")
        session1.close()

    def test_model_all(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)

        ids = {alice.id.iri, bob.id.iri, john.id.iri}
        session1.close()

        session2 = user_mediator.create_session()
        self.assertEquals({r.id.iri for r in lp_model.all(session2)}, ids)
        session2.close()

    def test_sparql_filter(self):
        session1 = user_mediator.create_session()
        alice = create_alice(session1)
        bob = create_bob(session1)
        john = create_john(session1)
        ids = {alice.id.iri, bob.id.iri, john.id.iri}
        session1.close()

        session2 = user_mediator.create_session()
        r1 = "SELECT ?s WHERE { ?s a foaf:Person }"
        self.assertEquals({r.id.iri for r in session2.sparql_filter(r1)}, ids)
        session2.close()

        session3 = user_mediator.create_session()
        r2 = """SELECT ?s WHERE {
            ?s a foaf:Person ;
               foaf:name "%s"^^xsd:string .
        }""" % alice_name
        self.assertEquals({r.id.iri for r in session3.sparql_filter(r2)}, {alice.id.iri})
        session3.close()

    def test_no_filter_get(self):
        session1 = user_mediator.create_session()
        self.assertEquals(session1.get(), None)
        alice = create_alice(session1)

        session2 = user_mediator.create_session()
        # Unique object
        self.assertEquals(session2.get().id.iri, alice.id.iri)
        session1.close()
        session2.close()

    def test_empty_filter(self):
        """
            No filtering arguments -> all()
        """
        session1 = user_mediator.create_session()
        self.assertEquals(list(session1.filter()), [])
        alice = create_alice(session1)

        session2 = user_mediator.create_session()
        # Unique object
        self.assertEquals(list(session2.filter())[0].id.iri, alice.id.iri)

        bob = create_bob(session2)

        session3 = user_mediator.create_session()
        self.assertEquals({r.id.iri for r in session3.filter()}, {alice.id.iri, bob.id.iri})

        session1.close()
        session2.close()
        session3.close()

    def test_filter_hashless_iri_types_and_names(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        doc_iri = bob.id.hashless_iri
        alice = lp_model.new(session1, iri=(doc_iri + "#alice"), name=alice_name, mboxes={alice_mail},
                             short_bio_en=alice_bio_en)
        key = gpg_model.new(session1, iri=(doc_iri + "#key"), fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)
        session1.commit()
        create_john(session1, iri=u"http://localhost/john#me")

        session2 = user_mediator.create_session()
        self.assertEquals({bob.id.iri, alice.id.iri, key.id.iri}, {r.id.iri for r in session2.filter(hashless_iri=doc_iri)})
        session2.close()

        session3 = user_mediator.create_session()
        self.assertEquals({bob.id.iri, alice.id.iri}, {r.id.iri for r in session3.filter(hashless_iri=doc_iri,
                                                                                         types=[MY_VOC + "LocalPerson"])})
        session3.close()

        session4 = user_mediator.create_session()
        # Missing type (name is thus ambiguous)
        with self.assertRaises(OMAttributeAccessError):
            session4.filter(hashless_iri=doc_iri, name=alice_name)
        self.assertEquals({alice.id.iri}, {r.id.iri for r in lp_model.filter(session4, hashless_iri=doc_iri, name=alice_name)})
        session4.close()
        session1.close()

    def test_get_hashless_iri_types_and_names(self):
        session1 = user_mediator.create_session()
        bob = create_bob(session1)
        doc_iri = bob.id.hashless_iri
        key = gpg_model.new(session1, iri=(doc_iri + "#key"), fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)
        document = session1.new(iri=doc_iri, types=[str(FOAF + "Document")])
        session1.commit()

        session2 = user_mediator.create_session()
        self.assertEquals(document.id.iri, session2.get(hashless_iri=doc_iri).id.iri)
        session2.close()
        session3 = user_mediator.create_session()
        self.assertEquals(bob.id.iri, session3.get(hashless_iri=doc_iri, types=[MY_VOC + "LocalPerson"]).id.iri)
        session3.close()
        session4 = user_mediator.create_session()
        self.assertEquals(key.id.iri, session4.get(hashless_iri=doc_iri, types=[MY_VOC + "LocalGPGPublicKey"]).id.iri)
        session4.close()

        session1.close()

    def test_limit(self):
        session1 = user_mediator.create_session()
        n = 20
        for _ in range(20):
            create_alice(session1)
        self.assertEquals(len(list(session1.filter())), n)
        self.assertEquals(len(list(lp_model.filter(session1))), n)
        self.assertEquals(len(list(lp_model.all(session1))), n)
        self.assertEquals(len(list(session1.filter(limit=10))), 10)
        self.assertEquals(len(list(lp_model.filter(session1, limit=10))), 10)
        self.assertEquals(len(list(lp_model.all(session1, limit=10))), 10)
        session1.close()