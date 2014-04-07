from unittest import TestCase
from rdflib import ConjunctiveGraph, plugin
import json

from ld_orm.model import default_model_generator
from ld_orm.attribute import AttributeTypeError

class ModelTest(TestCase):

    LocalPerson = None

    def setUp(self):
        self.graph = ConjunctiveGraph()

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

        self.graph.parse(data=json.dumps(self.local_person_def), format="json-ld")
        self.graph.parse(self.bcogrel_uri)

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
                                                                        self.graph)

    def test_new_instances(self):
        name = "Toto"
        blogs = ["http://blog.bcgl.fr"]
        p1 = self.LocalPerson()
        p1.name = name
        #print p1.name
        p1.blogs = blogs

        self.assertEquals(name, p1.name)
        self.assertEquals(blogs, p1.blogs)

        # Because of descriptors, these attributes should not appear in __dict__
        self.assertEquals(vars(p1), {})

        with self.assertRaises(AttributeTypeError):
            p1.name = 2
        p1.name = "Robert"



    def test_existing_instances(self):
        # Declare a LocalPerson
        self.graph.parse(data=json.dumps({"@id" : self.bcogrel_uri,
                                    "@type": "LocalPerson",
                                    # Required (missing in my WebID)
                                    "mboxes": [
                                        "bcogrel@example.com"
                                    ]
                                    }),
                    context=self.person_context,
                    format="json-ld")
        #print self.graph.serialize(format="turtle")



# fields = []
# for member_name, member_object in inspect.getmembers(LocalPerson):
#     if inspect.isdatadescriptor(member_object):
#          fields.append(member_name)
# print "Fields: %s" % fields
