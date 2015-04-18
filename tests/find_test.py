import unittest
from default_model import *
from oldman.exception import OMAttributeAccessError


class FindTest(unittest.TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_filter_two_bobs(self):
        #Bob 1
        create_bob()

        bob2_mail = "bob2@example.org"
        bob2_bio_en = "I am a double."
        # Bob 2
        lp_model.create(name=bob_name, mboxes={bob2_mail}, short_bio_en=bob2_bio_en)

        bobs = list(lp_model.filter(name=bob_name))
        self.assertEquals(len(bobs), 2)
        self.assertEquals(bobs[0].name, bobs[1].name)
        self.assertEquals(bobs[0].name, bob_name)
        self.assertNotEquals(bobs[0].mboxes, bobs[1].mboxes)

        # mboxes is NOT REQUIRED to be exhaustive
        bobs2 = {r.id.iri for r in lp_model.filter(name=bob_name, mboxes={bob_email2})}
        self.assertEquals(len(bobs2), 1)
        bobs3 = {r.id.iri for r in lp_model.filter(name=bob_name, mboxes={bob_email1, bob_email2})}
        self.assertEquals(bobs2, bobs3)

        # Nothing
        bobs4 = {r.id.iri for r in lp_model.filter(name=bob_name, mboxes={bob_email1, bob_email2, bob2_mail})}
        self.assertEquals(len(bobs4), 0)

    def test_wrong_filter(self):
        with self.assertRaises(OMAttributeAccessError):
            lp_model.filter(undeclared_attr="not in datastore")

    def test_model_all(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()

        ids = {alice.id.iri, bob.id.iri, john.id.iri}
        self.assertEquals({r.id.iri for r in lp_model.all()}, ids)

    def test_sparql_filter(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()
        ids = {alice.id.iri, bob.id.iri, john.id.iri}

        r1 = "SELECT ?s WHERE { ?s a foaf:Person }"
        self.assertEquals({r.id.iri for r in user_mediator.sparql_filter(r1)}, ids)

        r2 = """SELECT ?s WHERE {
            ?s a foaf:Person ;
               foaf:name "%s"^^xsd:string .
        }""" % alice_name
        self.assertEquals({r.id.iri for r in user_mediator.sparql_filter(r2)}, {alice.id.iri})

    def test_no_filter_get(self):
        self.assertEquals(user_mediator.get(), None)
        alice = create_alice()
        # Unique object
        self.assertEquals(user_mediator.get().id.iri, alice.id.iri)

    def test_empty_filter(self):
        """
            No filtering arguments -> all()
        """
        self.assertEquals(list(user_mediator.filter()), [])
        alice = create_alice()
        # Unique object
        self.assertEquals(list(user_mediator.filter())[0].id.iri, alice.id.iri)

        bob = create_bob()
        self.assertEquals({r.id.iri for r in user_mediator.filter()}, {alice.id.iri, bob.id.iri})

    def test_filter_hashless_iri_types_and_names(self):
        bob = create_bob()
        doc_iri = bob.id.hashless_iri
        alice = lp_model.create(iri=(doc_iri + "#alice"), name=alice_name, mboxes={alice_mail},
                                short_bio_en=alice_bio_en)
        key = gpg_model.create(iri=(doc_iri + "#key"), fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)
        create_john(iri=u"http://localhost/john#me")

        self.assertEquals({bob.id.iri, alice.id.iri, key.id.iri}, {r.id.iri for r in user_mediator.filter(hashless_iri=doc_iri)})
        self.assertEquals({bob.id.iri, alice.id.iri}, {r.id.iri for r in user_mediator.filter(hashless_iri=doc_iri,
                                                                                    types=[MY_VOC + "LocalPerson"])})
        # Missing type (name is thus ambiguous)
        with self.assertRaises(OMAttributeAccessError):
            user_mediator.filter(hashless_iri=doc_iri, name=alice_name)
        self.assertEquals({alice.id.iri}, {r.id.iri for r in lp_model.filter(hashless_iri=doc_iri, name=alice_name)})

    def test_get_hashless_iri_types_and_names(self):
        bob = create_bob()
        doc_iri = bob.id.hashless_iri
        key = gpg_model.create(iri=(doc_iri + "#key"), fingerprint=gpg_fingerprint, hex_id=gpg_hex_id)
        document = user_mediator.create(iri=doc_iri, types=[str(FOAF + "Document")])

        self.assertEquals(document.id.iri, user_mediator.get(hashless_iri=doc_iri).id.iri)
        self.assertEquals(bob.id.iri, user_mediator.get(hashless_iri=doc_iri, types=[MY_VOC + "LocalPerson"]).id.iri)
        self.assertEquals(key.id.iri, user_mediator.get(hashless_iri=doc_iri, types=[MY_VOC + "LocalGPGPublicKey"]).id.iri)

    def test_limit(self):
        n = 20
        for _ in range(20):
            create_alice()
        self.assertEquals(len(list(user_mediator.filter())), n)
        self.assertEquals(len(list(lp_model.filter())), n)
        self.assertEquals(len(list(lp_model.all())), n)
        self.assertEquals(len(list(user_mediator.filter(limit=10))), 10)
        self.assertEquals(len(list(lp_model.filter(limit=10))), 10)
        self.assertEquals(len(list(lp_model.all(limit=10))), 10)