# -*- coding: utf-8 -*-

from unittest import TestCase
from rdflib import ConjunctiveGraph, URIRef
import json

from ld_orm import default_model_generator
from ld_orm.attribute import AttributeTypeError, RequiredAttributeError

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
                    "bio": "http://purl.org/vocab/bio/0.1/",
                    "short_bio": "bio:olb"
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
                    "property": "short_bio",
                    "required": True,
                    "readonly": False,
                    "writeonly": False
                }
            ]
        }

        self.schema_graph.parse(data=json.dumps(self.local_person_def), format="json-ld")
        self.schema_graph.parse(self.bcogrel_uri)

        self.person_context = {
            "@context": {
                "myvoc": self.my_voc_prefix,
                "foaf": "http://xmlns.com/foaf/0.1/",
                "bio": "http://purl.org/vocab/bio/0.1/",
                "xsd": "http://www.w3.org/2001/XMLSchema#",
                "LocalPerson": "myvoc:LocalPerson",
                "Person": "foaf:Person",
                "name": {
                    "@id": "foaf:name",
                    "@type": "xsd:string"
                },
                "mboxes": "foaf:mbox",
                "blogs": {
                    "@id": "foaf:weblog",
                    "@type": "@id"
                },
                "short_bio_fr": {
                    "@id": "bio:olb",
                    "@language": "fr"
                },
                "short_bio_en": {
                    "@id": "bio:olb",
                    "@language": "en"
                }
            }
        }

        self.model_generator = default_model_generator()
        #print self.graph.serialize(format="turtle")
        if ModelTest.LocalPerson is None:
            ModelTest.LocalPerson = self.model_generator.generate("LocalPerson", self.person_context,
                                                                  self.schema_graph, self.data_graph)

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
        self.assertRaises(RequiredAttributeError, p1.save)

        p1.short_bio_en = "It is my life."
        self.assertTrue(p1.is_valid())
        p1.save()

        self.assertEquals(name, p1.name)
        self.assertEquals(blogs, p1.blogs)

        # Because of descriptors, these attributes should not appear in __dict__
        self.assertEquals(vars(p1), {})

        with self.assertRaises(AttributeTypeError):
            p1.name = 2
        p1.name = "Robert"

        # Not saved
        self.assertFalse(bool(self.data_graph.query("""ASK {?x foaf:name "Robert" }""")))

        roger_email1 = "roger@localhost"
        p2 = self.LocalPerson(name="Roger", mboxes=[roger_email1], short_bio_fr="Spécialiste en tests.")
        self.assertTrue(p2.is_valid())
        # Saved
        self.assertTrue(bool(self.data_graph.query("""ASK {?x foaf:name "Roger" }""")))

        # Change email addresses
        roger_email2 = "roger@example.com"
        roger_email3 = "roger@example.org"
        p2.mboxes=[roger_email2, roger_email3]
        p2.save()
        mbox_query = """ASK {?x foaf:mbox %s }"""
        self.assertFalse(bool(self.data_graph.query(mbox_query % roger_email1 )))
        self.assertTrue(bool(self.data_graph.query(mbox_query % roger_email2 )))
        self.assertTrue(bool(self.data_graph.query(mbox_query % roger_email3 )))


        with self.assertRaises(RequiredAttributeError):
            self.LocalPerson(name="Gertrude", mboxes=["gertrude@localhost"])





    def test_existing_instances(self):
        # Declare a LocalPerson
        self.data_graph.parse(data=json.dumps({"@id" : self.bcogrel_uri,
                                    "@type": "LocalPerson",
                                    # Required (missing in my WebID)
                                    "mboxes": [
                                        "bcogrel@example.com"
                                    ]
                                    }),
                    context=self.person_context,
                    format="json-ld")

        #TODO: get a LocalPerson from this entry
        #print self.graph.serialize(format="trig")



# fields = []
# for member_name, member_object in inspect.getmembers(LocalPerson):
#     if inspect.isdatadescriptor(member_object):
#          fields.append(member_name)
# print "Fields: %s" % fields
