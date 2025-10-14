"""Get show summaries with pagination."""
import json
from typing import Any

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.route('get_show_summaries', methods=['GET'], auth_level=func.AuthLevel.ANONYMOUS)
def get_show_summaries(req: func.HttpRequest) -> func.HttpResponse:
    """Get show summaries with pagination

    Args:
        req (func.HttpRequest): HTTP request object

    Query Parameters:
        offset (int): Offset for the pagination (default 0)
        limit (int): Limit for the pagination (default 100, max 1000)

    Returns:
        func.HttpResponse: HTTP response object
    """
    offset: int = int(req.params.get('offset', 0))
    limit: int = int(req.params.get('limit', 100))

    limit = min(limit, 1000)

    show_service: ShowService = ShowService()
    shows_summaries: list[dict[str, Any]] = show_service.get_show_summaries(offset, limit)

    response: dict[str, Any] = {
        "shows": shows_summaries,
        "total": len(shows_summaries),
        "offset": offset,
        "limit": limit,
    }

    return func.HttpResponse(
        body=json.dumps(response),
        status_code=200,
        mimetype='application/json'
    )
