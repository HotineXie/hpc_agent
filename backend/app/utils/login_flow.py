import logging
import os

from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.serialize import DillCodeSource

logger = logging.getLogger(__name__)


def initialize_globus_compute_client() -> GlobusComputeClient:
    """
    Create a Globus Compute client for single-user local use.

    Auth priority:
    1. GLOBUS_COMPUTE_TOKEN env var (access token string)
    2. Native credential store (~/.globus_compute/) — populated by
       `globus-compute-endpoint login` or the SDK's first-run auth flow.
    """
    token = os.environ.get("GLOBUS_COMPUTE_TOKEN", "").strip()
    if token:
        import globus_sdk
        authorizer = globus_sdk.AccessTokenAuthorizer(access_token=token)
        return GlobusComputeClient(
            authorizer=authorizer,
            code_serialization_strategy=DillCodeSource(),
        )
    return GlobusComputeClient(code_serialization_strategy=DillCodeSource())
