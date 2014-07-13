import unittest
from default_model import *


class SerializationTest(unittest.TestCase):
    def setUp(self):
        set_up()

    def tearDown(self):
        tear_down()

    def test_bob_json(self):
        bob = create_bob()
        bob_json = json.loads(bob.to_json())
        self.assertEquals(bob_json["name"], bob_name)
        self.assertEquals(bob_json["blog"], bob_blog)
        self.assertEquals(set(bob_json["mboxes"]), bob_emails)
        self.assertEquals(bob_json["short_bio_en"], bob_bio_en)
        self.assertEquals(bob_json["short_bio_fr"], bob_bio_fr)
        self.assertEquals(bob_json["types"], lp_model.ancestry_iris)

    def test_bob_jsonld(self):
        bob = create_bob()
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
        rsa_key = create_rsa_key()
        key_jsonld = json.loads(rsa_key.to_jsonld())
        self.assertEquals(key_jsonld["modulus"], key_modulus)
        self.assertEquals(key_jsonld["exponent"], key_exponent)
        self.assertEquals(key_jsonld["label"], key_label)
        # Blank node so IRI must not appear
        self.assertFalse("id" in key_jsonld)

    def test_rdf(self):
        bob = create_bob()
        bob_uri = URIRef(bob.id)
        g = Graph()
        g.parse(data=bob.to_rdf("turtle"), format="turtle")
        self.assertEquals(g.value(bob_uri, URIRef(FOAF + "name")).toPython(), bob_name)
        self.assertEquals(g.value(bob_uri, URIRef(FOAF + "weblog")).toPython(), bob_blog)
        self.assertEquals({mbox.toPython() for mbox in g.objects(bob_uri, URIRef(FOAF + "mbox"))},
                          bob_emails)
        self.assertEquals({bio.toPython() for bio in g.objects(bob_uri, URIRef(BIO + "olb"))},
                          {bob_bio_en, bob_bio_fr})

    def test_children_jsonld(self):
        bob = create_bob()
        alice = create_alice()
        john = create_john()
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
        bob = create_bob()
        bob_iri = bob.id
        rsa_key = create_rsa_key()
        bob.keys = {rsa_key}
        bob.save()
        # If any cache
        data_store.resource_cache.remove_resource(bob)

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
