import json
import logging
import time
from typing import Dict, List, Tuple

from globus_compute_sdk import Client as GlobusComputeClient
from globus_compute_sdk.errors import TaskPending
from globus_sdk import ComputeAPIError

from app.utils.functions import get_machine_metadata

_METADATA_SUBMIT_MAX_ATTEMPTS = 3
_METADATA_POLL_MAX_ATTEMPTS = 15
_METADATA_INITIAL_DELAY = 1.0
_METADATA_MAX_DELAY = 8.0
_RETRYABLE_COMPUTE_ERROR_CODES = {"RESOURCE_CONFLICT"}

logger = logging.getLogger(__name__)


def _is_retryable_compute_error(error: ComputeAPIError) -> bool:
    code = getattr(error, "code", None)
    status = getattr(error, "http_status", None)
    return (code and code in _RETRYABLE_COMPUTE_ERROR_CODES) or status == 409


def globus_compute_wrapped_run(
    globus_compute_client: GlobusComputeClient,
    endpoint_id: str,
    function_id: str,
    user_endpoint_config: Dict | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
):
    batch = globus_compute_client.create_batch(
        user_endpoint_config=user_endpoint_config
    )
    batch.add(function_id, args=args, kwargs=kwargs)
    r = globus_compute_client.batch_run(endpoint_id, batch)
    return r["tasks"][function_id][0]


def _submit_metadata_task_with_retry(
    endpoint_uuid,
    globus_compute_client,
    metadata_func_id,
    logger,
    max_attempts=_METADATA_SUBMIT_MAX_ATTEMPTS,
    user_endpoint_config=None,
):
    delay = _METADATA_INITIAL_DELAY
    for attempt in range(1, max_attempts + 1):
        try:
            return globus_compute_wrapped_run(
                globus_compute_client,
                endpoint_id=endpoint_uuid,
                function_id=metadata_func_id,
                user_endpoint_config=user_endpoint_config,
            )
        except ComputeAPIError as exc:
            if not _is_retryable_compute_error(exc) or attempt == max_attempts:
                logger.error("Error running metadata for endpoint %s: %s", endpoint_uuid, exc)
                return None
            logger.warning("Metadata conflict for %s attempt %s/%s, retry in %.1fs",
                           endpoint_uuid, attempt, max_attempts, delay)
            time.sleep(delay)
            delay = min(delay * 2, _METADATA_MAX_DELAY)
    return None


def _wait_for_metadata_result(globus_compute_client, metadata_task_id, logger,
                               max_attempts=_METADATA_POLL_MAX_ATTEMPTS):
    delay = _METADATA_INITIAL_DELAY
    for attempt in range(1, max_attempts + 1):
        try:
            return globus_compute_client.get_result(metadata_task_id)
        except TaskPending:
            logger.info("Metadata task %s pending attempt %s/%s",
                        metadata_task_id, attempt, max_attempts)
            time.sleep(delay)
            delay = min(delay * 1.5, _METADATA_MAX_DELAY)
        except Exception as exc:
            logger.error("Error retrieving metadata task %s: %s", metadata_task_id, exc)
            return None
    logger.error("Metadata task %s still pending after %s attempts", metadata_task_id, max_attempts)
    return None


def endpoint_initialization_status(globus_compute_client, database):
    all_endpoints = globus_compute_client.get_endpoints(role="any")
    endpoints_in_db = database.get_endpoints()

    endpoint_map = {}
    for ep in all_endpoints:
        endpoint_map[ep["uuid"]] = {
            "name": ep.get("display_name", ep.get("name", "")),
            "is_managed": False,
        }
    for ep in endpoints_in_db:
        if ep.endpoint_uuid in endpoint_map:
            endpoint_map[ep.endpoint_uuid]["is_managed"] = ep.is_managed
        else:
            endpoint_map[ep.endpoint_uuid] = {
                "name": ep.endpoint_name,
                "is_managed": ep.is_managed,
            }
    return endpoint_map


def register_all_endpoints(globus_compute_client, database, logger):
    endpoints = globus_compute_client.get_endpoints(role="any")
    all_endpoints = []
    for ep in endpoints:
        endpoint_name = ep.get("display_name", ep.get("name", ""))
        endpoint_uuid = ep["uuid"]
        try:
            endpoint_status = globus_compute_client.get_endpoint_status(
                endpoint_uuid=endpoint_uuid
            )["status"]
        except Exception as e:
            logger.error("Error getting status for %s: %s", endpoint_name, e)
            continue
        try:
            endpoint_metadata = globus_compute_client.get_endpoint_metadata(
                endpoint_uuid=endpoint_uuid
            )
            endpoint_host = endpoint_metadata.get("hostname", "unknown")
        except Exception:
            endpoint_host = "unknown"

        if not database.exists_endpoint(endpoint_uuid=endpoint_uuid):
            database.save_endpoint(
                endpoint_uuid=endpoint_uuid,
                endpoint_name=endpoint_name,
                endpoint_host=endpoint_host,
                endpoint_status=endpoint_status,
            )
        else:
            database.update_endpoint_status(
                endpoint_uuid=endpoint_uuid,
                endpoint_status=endpoint_status,
            )
        all_endpoints.append({
            "endpoint_uuid": endpoint_uuid,
            "endpoint_name": endpoint_name,
            "endpoint_host": endpoint_host,
            "endpoint_status": endpoint_status,
        })
    return all_endpoints


def load_accounts_partitions(
    endpoint_uuid: str,
    database,
    logger: logging.Logger,
    globus_compute_client: GlobusComputeClient,
) -> Tuple[List[str], List[str]]:
    try:
        endpoint_metadata = globus_compute_client.get_endpoint_metadata(
            endpoint_uuid=endpoint_uuid
        )
    except ComputeAPIError as e:
        logger.error("Error getting endpoint metadata for %s: %s", endpoint_uuid, e)
        return [], []

    user_endpoint_config = database.get_endpoint_user_config(endpoint_uuid=endpoint_uuid)
    metadata_func_id = globus_compute_client.register_function(get_machine_metadata)
    metadata_task_id = _submit_metadata_task_with_retry(
        endpoint_uuid, globus_compute_client, metadata_func_id, logger,
        user_endpoint_config=user_endpoint_config,
    )
    metadata = {}
    if metadata_task_id:
        result = _wait_for_metadata_result(globus_compute_client, metadata_task_id, logger)
        if result is not None:
            if isinstance(result, dict):
                metadata = result
            else:
                raw = getattr(result, "stdout", None) or str(result)
                try:
                    metadata = json.loads(raw)
                except Exception:
                    logger.error("Could not parse metadata JSON for %s", endpoint_uuid)

    account_list = metadata.get("accounts", [])
    partition_list = metadata.get("partitions", [])

    if account_list:
        database.save_accounts(endpoint_uuid=endpoint_uuid, accounts=account_list)
    if partition_list:
        database.save_partition(endpoint_uuid=endpoint_uuid, partitions=partition_list)

    return account_list, partition_list
