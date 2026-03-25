from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse

_original_index = admin.site.index


def custom_admin_index(request, extra_context=None):
    user = request.user

    if user.is_authenticated:
        if user.is_superuser:
            return _original_index(request, extra_context)

            return redirect(reverse("admin:account_exhibitionvisitor_changelist"))

    return _original_index(request, extra_context)

admin.site.index = custom_admin_index
