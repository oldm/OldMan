from .crud import HashLessCRUDer
from .controller import HTTPController

from oldman.vocabulary import HYDRA_COLLECTION_IRI, HYDRA_PAGED_COLLECTION_IRI


def create_basic_hydra_controller(manager, post_operations=None, config={}):
    if post_operations is None:
        post_operations = {HYDRA_COLLECTION_IRI: "append",
                           HYDRA_PAGED_COLLECTION_IRI: "append"}
    elif HYDRA_COLLECTION_IRI not in post_operations:
        post_operations = post_operations.copy()
        post_operations[HYDRA_COLLECTION_IRI] = "append"

    cruder = HashLessCRUDer(manager)
    return HTTPController(cruder, post_operations, config)
