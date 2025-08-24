"""Update shows manaully"""
import logging

import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="get_updates_manually")
@bp.route(route="update_shows_manually", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def get_updates_manually(req: func.HttpRequest) -> func.HttpResponse:
    """Update shows manually

    An optional 'since' query parameter can be provided to filter updates to a
    specified period (e.g., day, week, or month)

    Args:
        req (func.HttpRequest): Request object
    Returns:
        func.HttpResponse: Response object
    """
    # Get 'since' param, default to 'day' if not present in the query string.
    since: str = req.params.get('since', 'day')

    if since not in ('day', 'week', 'month'):  # if invalid, log error and return
        logging.error(f"Invalid since parameter provided: {since}")
        return func.HttpResponse(
            "Query parameter 'since' must be 'day', 'week', or 'month'.",
            status_code=400
        )

    show_service: ShowService = ShowService()  # create update service
    show_service.get_updates(since)  # update shows manually

    message = f"Getting all updates from TV Maze for the last {since}"

    return func.HttpResponse(message, status_code=202)
