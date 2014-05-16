# -*- coding: utf-8 -*-
"""
    Additional test on properties
"""

from unittest import TestCase
from os import path
from rdflib import ConjunctiveGraph, URIRef, Literal, Graph, XSD
import json
from oldman import create_resource_manager, parse_graph_safely
from oldman.exception import OMPropertyDefError, OMReadOnlyAttributeError

default_graph = ConjunctiveGraph()
schema_graph = default_graph.get_context(URIRef("http://localhost/schema"))
data_graph = default_graph.get_context(URIRef("http://localhost/data"))

EXAMPLE = "http://localhost/vocab#"

local_class_def = {
    "@context": [
        {
            "ex": EXAMPLE
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "ex:LocalClass",
    "@type": "hydra:Class",
    "supportedProperty": [
        {
            "property": "ex:roProperty",
            "readonly": True
        }, {
            "property": "ex:secret",
            "writeonly": True
        }
    ]
}

bad_class_def = {
    "@context": [
        {
            "ex": EXAMPLE
        },
        #"http://www.w3.org/ns/hydra/core"
        json.load(open(path.join(path.dirname(__file__), "hydra_core.jsonld")))["@context"]
    ],
    "@id": "ex:BadClass",
    "@type": "hydra:Class",
    "supportedProperty": [
        {
            "property": "ex:badProperty",
            "readonly": True,
            "writeonly": True
        }
    ]
}

parse_graph_safely(schema_graph, data=json.dumps(local_class_def), format="json-ld")
parse_graph_safely(schema_graph, data=json.dumps(bad_class_def), format="json-ld")


context = {
    "@context": {
        "ex": EXAMPLE,
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "id": "@id",
        "type": "@type",
        "LocalClass": "ex:LocalClass",
        "BadClass": "ex:BadClass",
        "required_property": {
            "@id": "ex:requiredProperty",
            "@type": "xsd:string"
        },
        "ro_property": {
            "@id": "ex:roProperty",
            "@type": "xsd:string"
        },
        "secret": {
            "@id": "ex:secret",
            "@type": "xsd:string"
        },
        "bad_property": {
            "@id": "ex:badProperty",
            "@type": "xsd:string"
        }
    }
}

manager = create_resource_manager(schema_graph, default_graph)
lc_model = manager.create_model("LocalClass", context, iri_prefix="http://localhost/objects/")


class PropertyTest(TestCase):

    def tearDown(self):
        """ Clears the data graph """
        data_graph.update("CLEAR DEFAULT")
        manager.clear_resource_cache()

    def test_read_and_write_only(self):
        with self.assertRaises(OMPropertyDefError):
            manager.create_model("BadClass", context, data_graph)

    def test_write_only(self):
        obj = lc_model.new()
        secret = "My secret"
        obj.secret = secret
        for obj_dump in [obj.to_json(), obj.to_jsonld()]:
            self.assertFalse(secret in obj_dump)
            dct = json.loads(obj_dump)
            self.assertFalse("secret" in dct)

        self.assertFalse(secret in obj.to_rdf("turtle"))

    def test_read_only(self):
        obj = lc_model.new()
        # End-user
        end_user_str = "A user is not allowed to write this"
        obj.ro_property = end_user_str
        with self.assertRaises(OMReadOnlyAttributeError):
            obj.save()
        #Admin
        admin_str = "An admin is allowed to write it"
        obj.ro_property = admin_str
        obj.save(is_end_user=False)
        self.assertEquals(admin_str, obj.ro_property)

        with self.assertRaises(OMReadOnlyAttributeError):
            lc_model.create(ro_property=end_user_str)

    def test_read_only_update(self):
        obj = lc_model.new()
        admin_str = "An admin is allowed to write it"
        obj.ro_property = admin_str
        obj.save(is_end_user=False)

        obj_dict = obj.to_dict()
        obj_dict["secret"] = "My secret again"
        # No problem with ro_property because it is not changed
        obj.full_update(obj_dict)

        obj_dict["ro_property"] = "Writing a read-only property"
        with self.assertRaises(OMReadOnlyAttributeError):
            obj.full_update(obj_dict)
        obj.full_update(obj_dict, is_end_user=False)

    def test_read_only_graph_update(self):
        obj = lc_model.new()
        obj_iri = URIRef(obj.id)
        admin_str = "An admin is allowed to write it"
        obj.ro_property = admin_str
        obj.save(is_end_user=False)

        graph = Graph()
        graph.parse(data=obj.to_rdf("xml"), format="xml")
        obj.full_update_from_graph(graph)
        self.assertEquals(obj.ro_property, admin_str)

        ro_prop = URIRef(EXAMPLE + "roProperty")
        graph.remove((obj_iri, ro_prop, Literal(admin_str, datatype=XSD.string)))
        str2 = "Writing a read-only property"
        graph.add((obj_iri, ro_prop, Literal(str2, datatype=XSD.string)))
        print graph.serialize(format="turtle")
        with self.assertRaises(OMReadOnlyAttributeError):
            obj.full_update_from_graph(graph)
        obj.full_update_from_graph(graph, is_end_user=False)

        graph.remove((obj_iri, ro_prop, Literal(str2, datatype=XSD.string)))
        obj.full_update_from_graph(graph, is_end_user=False)
        self.assertEquals(obj.ro_property, None)

