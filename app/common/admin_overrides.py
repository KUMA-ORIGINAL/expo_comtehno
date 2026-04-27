from django.contrib import admin
_original_index = admin.site.index


def custom_admin_index(request, extra_context=None):
    return _original_index(request, extra_context)

admin.site.index = custom_admin_index
