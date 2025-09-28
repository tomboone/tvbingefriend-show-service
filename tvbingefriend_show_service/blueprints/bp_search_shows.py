"""Search shows API endpoint"""
import json
import logging
import hashlib
from urllib.parse import unquote

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="search_shows")
@bp.route(route="shows/search", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def search_shows(req: func.HttpRequest) -> func.HttpResponse:
    """Search shows by name with instant results

    Args:
        req (func.HttpRequest): HTTP request with query parameters:
            - q: Search query string (required)
            - limit: Number of results to return (optional, default 20, max 50)
            - offset: Number of results to skip for pagination (optional, default 0)

    Returns:
        func.HttpResponse: HTTP response with search results
    """
    try:
        # Get query parameters
        query = req.params.get('q', '').strip()
        if not query:
            return func.HttpResponse(
                body=json.dumps({"error": "Query parameter 'q' is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # URL decode the query in case it's encoded
        query = unquote(query)

        # Validate and set pagination parameters
        try:
            limit = min(int(req.params.get('limit', 20)), 50)  # Max 50 results
            offset = max(int(req.params.get('offset', 0)), 0)  # Min 0 offset
        except (ValueError, TypeError):
            return func.HttpResponse(
                body=json.dumps({"error": "Invalid limit or offset parameter"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )

        # Search shows
        show_service = ShowService()
        results = show_service.search_shows(query, limit, offset)

        # Create response data
        response_data = {
            "query": query,
            "limit": limit,
            "offset": offset,
            "count": len(results),
            "results": results
        }

        # Generate ETag for caching
        etag = hashlib.md5(json.dumps(response_data, sort_keys=True).encode(), usedforsecurity=False).hexdigest()

        # Check if client has current version
        if_none_match = req.headers.get('If-None-Match')
        if if_none_match == etag:
            return func.HttpResponse(status_code=304)

        return func.HttpResponse(
            body=json.dumps(response_data),
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes (shorter for search)
                "ETag": etag
            }
        )

    except Exception as e:
        logging.error(f"search_shows: Unhandled exception: {e}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({"error": "Internal server error"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )