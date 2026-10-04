def active_page(request):
    """
    Automatically determine the active app/page
    for sidebar navigation.
    """

    app_name = ""

    if request.resolver_match:

        app_name = request.resolver_match.app_name

        if not app_name:
            app_name = request.resolver_match.url_name

    return {
        "active_page": app_name
    }
