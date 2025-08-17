"""Start get all shows from TV Maze"""
import azure.functions as func

from tvbingefriend_show_service.services.show_service import ShowService

bp: func.Blueprint = func.Blueprint()


@bp.function_name(name="start_get_all")
@bp.route(route="start_get_shows", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def start_get_all(req: func.HttpRequest) -> func.HttpResponse:
    """Start get all shows from TV Maze

    An optional 'page' query parameter can be provided to start from a specific page.

    Args:
        req (func.HttpRequest): Request object

    Returns:
        func.HttpResponse: Response object
    """

    show_service: ShowService = ShowService()  # intialize show service

    page = show_service.get_shows_page_number(req)  # get show index page number
    if isinstance(page, func.HttpResponse):  # if page is an http response, return it
        return page

    show_service.start_get_all_shows(page=page)  # initiate retrieval of all shows

    response_text = f"Getting all shows from TV Maze, starting from page {page}"  # set response text
    response = func.HttpResponse(response_text, status_code=202)  # set http response

    return response
