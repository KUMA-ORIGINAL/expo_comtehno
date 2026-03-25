class LanguageMiddleware:
    """
    Legacy middleware kept for backward compatibility.
    Language switching is handled by Django LocaleMiddleware.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
