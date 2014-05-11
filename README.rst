====================
OldMan:  Python OLDM
====================

Python Object RDF mapper based on JSON-LD contexts and the `Hydra RDF vocabulary
<http://www.markus-lanthaler.com/hydra/spec/latest/core/>`_.

Alpha, under active development.

 * Declarative programming: Python model classes are generated from Hydra RDF assertions (hydra:supportedProperty) and JSON-LD contexts.
 * Stores the objects in a SPARQL-enabled triplestore.
 * Uses short names from the JSON-LD context.
 * Checks hydra:required and rdfs:range properties, xsd datatypes defined in JSON-LD context.
 * Extensible to other vocabularies (SPIN support could be added).
 * Python 2.7.