"""Get a specific show by ID"""
import json
import logging

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="get_show_by_id")
@bp.route(route="shows/{show_id:int}", methods=["GET"])
def get_show_by_id(req: func.HttpRequest) -> func.HttpResponse:
    """Get a show by its ID

    Args:
        req (func.HttpRequest): HTTP request

    Returns:
        func.HttpResponse: HTTP response with show data
    """
    try:
        show_id = req.route_params.get('show_id')
        if not show_id:
            return func.HttpResponse(
                body="Show ID is required",
                status_code=400
            )

        show_id_int = int(show_id)
        show_service = ShowService()
        show = show_service.get_show_by_id(show_id_int)

        if not show:
            return func.HttpResponse(
                body=f"Show with ID {show_id} not found",
                status_code=404
            )

        return func.HttpResponse(
            body=json.dumps(show),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )

    except ValueError:
        return func.HttpResponse(
            body="Invalid show ID format",
            status_code=400
        )
    except Exception as e:
        logging.error(f"get_show_by_id: Unhandled exception: {e}", exc_info=True)
        return func.HttpResponse(
            body="Internal server error",
            status_code=500
        )