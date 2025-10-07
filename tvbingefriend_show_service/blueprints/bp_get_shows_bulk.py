"""Get all shows with pagination."""
import json
from typing import Any

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.route('/get_shows_bulk', methods=['GET'])
def get_shows_bulk(req: func.HttpRequest) -> func.HttpResponse:
    """Get all shows with pagination (no search filtering)

    Args:
        req (func.HttpRequest): HTTP request object

    Query Parameters:
        offset (int): Offset for the pagination (default 0)
        limit (int): Limit for the pagination (default 100, max 1000)

    Returns:
        func.HttpResponse: HTTP response object
    """
    offset: int | None = req.params.get('offset')
    limit: int | None = req.params.get('limit')

    show_service: ShowService = ShowService()
    shows_bulk: list[dict[str, Any]] = show_service.get_shows_bulk(offset, limit)

    response: dict[str, Any] = {
        "shows": shows_bulk,
        "total": len(shows_bulk),
        "offset": offset,
        "limit": limit,
    }

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=200,
        mimetype='application/json'
    )



