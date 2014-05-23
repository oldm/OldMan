import unittest
from default_model import *


class FindTest(unittest.TestCase):
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

    def test_model_all(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()

        ids = {alice.id, bob.id, john.id}
        self.assertEquals({r.id for r in lp_model.all()}, ids)

    def test_sparql_filter(self):
        alice = create_alice()
        bob = create_bob()
        john = create_john()
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
        alice = create_alice()
        # Unique object
        self.assertEquals(manager.get().id, alice.id)

    def test_empty_filter(self):
        """
            No filtering arguments -> all()
        """
        self.assertEquals(list(manager.filter()), [])
        alice = create_alice()
        # Unique object
        self.assertEquals(list(manager.filter())[0].id, alice.id)

        bob = create_bob()
        self.assertEquals({r.id for r in manager.filter()}, {alice.id, bob.id})