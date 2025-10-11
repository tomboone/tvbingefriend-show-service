"""Get all shows with pagination."""
import json
from typing import Any

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.route('get_shows_bulk', methods=['GET'])
def get_shows_bulk(req: func.HttpRequest) -> func.HttpResponse:
    """Get all shows with pagination (no search filtering)

    Args:
        req (func.HttpRequest): HTTP request object

    Query Parameters:
        offset (int): Offset for the pagination (default 0, ignored if show_ids provided)
        limit (int): Limit for the pagination (default 100, max 1000)
        show_ids (str): Optional comma-separated list of show IDs to retrieve

    Returns:
        func.HttpResponse: HTTP response object
    """
    offset: int = int(req.params.get('offset', 0))
    limit: int = int(req.params.get('limit', 100))
    show_ids_param: str | None = req.params.get('show_ids')

    limit = min(limit, 1000)

    # Parse show_ids if provided
    show_ids: list[int] | None = None
    if show_ids_param:
        try:
            show_ids = [int(id_str.strip()) for id_str in show_ids_param.split(',') if id_str.strip()]
        except ValueError:
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid show_ids format. Must be comma-separated integers."}),
                status_code=400,
                mimetype='application/json'
            )

    show_service: ShowService = ShowService()
    shows_bulk: list[dict[str, Any]] = show_service.get_shows_bulk(offset, limit, show_ids)

    response: dict[str, Any] = {
        "shows": shows_bulk,
        "total": len(shows_bulk),
        "offset": offset,
        "limit": limit,
    }

    # Add show_ids to response if they were provided
    if show_ids is not None:
        response["show_ids"] = show_ids

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=200,
        mimetype='application/json'
    )
