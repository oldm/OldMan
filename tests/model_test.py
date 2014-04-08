# -*- coding: utf-8 -*-

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
import json

from ld_orm import default_model_generator
from ld_orm.attribute import DataAttributeTypeError, RequiredDataAttributeError

class ModelTest(TestCase):

    LocalPerson = None

    def setUp(self):
        self.graph = ConjunctiveGraph()
        self.schema_graph = self.graph.get_context(URIRef("http://localhost/schema"))
        self.data_graph = self.graph.get_context(URIRef("http://localhost/data"))
        self.my_voc_prefix = "http://example.com/vocab#"
        self.bcogrel_uri = "https://benjamin.bcgl.fr/profile#me"

        self.local_person_def = {
            "@context": [
                {
                    "myvoc": self.my_voc_prefix,
                    "foaf": "http://xmlns.com/foaf/0.1/",
                    "bio": "http://purl.org/vocab/bio/0.1/"
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
                }
            ]
        }

        self.schema_graph.parse(data=json.dumps(self.local_person_def), format="json-ld")

        self.person_context = {
            "@context": {
                "myvoc": self.my_voc_prefix,
                "foaf": "http://xmlns.com/foaf/0.1/",
                "bio": "http://purl.org/vocab/bio/0.1/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "id": "@id",
                "type": "@type",
                "LocalPerson": "myvoc:LocalPerson",
                "Person": "foaf:Person",
                "name": {
                    "@id": "foaf:name",
                    "@type": "xsd:string"
                },
                "mboxes": {
                    "@id": "foaf:mbox",
                    "@type": "xsd:string"
                },
                "blogs": {
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
                }
            }
        }

        self.model_generator = default_model_generator()
        #print self.graph.serialize(format="turtle")
        if ModelTest.LocalPerson is None:
            ModelTest.LocalPerson = self.model_generator.generate("LocalPerson", self.person_context,
                                                                  self.schema_graph, self.data_graph,
                                                                  uri_prefix="http://localhost/persons/")

    def test_new_instances(self):
        name = "Toto"
        blogs = ["http://blog.bcgl.fr"]
        p1 = self.LocalPerson()
        p1.name = name
        #print p1.name
        p1.blogs = blogs
        p1.mboxes = ["toto@localhost"]

        #TODO: should sent a exception because
        # short bio is missing
        self.assertFalse(p1.is_valid())
        self.assertRaises(RequiredDataAttributeError, p1.save)

        p1.short_bio_en = "It is my life."
        self.assertTrue(p1.is_valid())
        p1.save()

        # Prevent a strange bug
        self.data_graph = p1.storage_graph

        self.assertEquals(name, p1.name)
        self.assertEquals(blogs, p1.blogs)

        # Because of descriptors, these attributes should not appear in __dict__ except id
        self.assertEquals(vars(p1).keys(), ["id"])

        with self.assertRaises(DataAttributeTypeError):
            p1.name = 2
        p1.name = "Robert"

        # Not saved
        self.assertFalse(bool(self.data_graph.query("""ASK {?x foaf:name "Robert" }""")))

        roger_email1 = "roger@localhost"
        roger_name = "Roger"
        p2 = self.LocalPerson(name=roger_name, mboxes=[roger_email1], short_bio_fr="Spécialiste en tests.")
        self.assertTrue(p2.is_valid())
        p2.save()
        # Saved
        #print self.data_graph.serialize(format="turtle")
        self.assertEquals(self.data_graph, p2.storage_graph)
        name_query = """ASK {?x foaf:name "%s"^^xsd:string }"""
        self.assertTrue(bool(self.data_graph.query(name_query % roger_name )))

        # Change email addresses
        roger_email2 = "roger@example.com"
        roger_email3 = "roger@example.org"
        p2.mboxes=[roger_email2, roger_email3]
        p2.save()
        mbox_query = """ASK {?x foaf:mbox "%s"^^xsd:string }"""
        self.assertTrue(bool(self.data_graph.query(mbox_query % roger_email2 )))
        self.assertTrue(bool(self.data_graph.query(mbox_query % roger_email3 )))
        # Has been removed
        self.assertFalse(bool(self.data_graph.query(mbox_query % roger_email1 )))

        gertrude_uri = "http://localhost/persons/gertrude"
        p3 = self.LocalPerson(id=gertrude_uri, name="Gertrude", mboxes=["gertrude@localhost"])
        self.assertFalse(p3.is_valid())
        p3.short_bio_fr = "Enthusiasm is key."
        p3.save()
        self.assertTrue(bool(self.data_graph.query("ASK { <%s> ?p ?o }" % gertrude_uri)))

        p4 = self.LocalPerson.objects.get(name=roger_name)
        self.assertEquals(p2.id, p4.id)
        self.assertEquals(p2, p4)


    def test_existing_instances(self):
        # My WebID
        self.data_graph.parse(self.bcogrel_uri)

        me = self.LocalPerson.objects.get(id=self.bcogrel_uri)
        self.assertFalse(me.is_valid())

        mboxes = ["bcogrel@example.com", "bcogrel@example.org"]
        self.data_graph.parse(data=json.dumps({"@id" : self.bcogrel_uri,
                                   "@type": "LocalPerson",
                                   # Required (missing in my WebID)
                                   "mboxes": mboxes
                                   }),
                   context=self.person_context,
                   format="json-ld")

        #print self.data_graph.serialize(format="turtle")

        # Loaded from the cache
        me = self.LocalPerson.objects.get(id=self.bcogrel_uri)
        # Outdated because of the out-of-band update
        self.assertFalse(me.is_valid())

        # Clear the cache and it works!
        self.LocalPerson.objects.clear()
        me = self.LocalPerson.objects.get(id=self.bcogrel_uri)
        self.assertNotEquals(me.mboxes, None)
        self.assertEquals(set(me.mboxes), set(mboxes))
        me.is_valid()



# fields = []
# for member_name, member_object in inspect.getmembers(LocalPerson):
#     if inspect.isdatadescriptor(member_object):
#          fields.append(member_name)
# print "Fields: %s" % fields
