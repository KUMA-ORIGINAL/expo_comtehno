from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from ..models import User
from common.base_admin import BaseModelAdmin

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(GroupAdmin, UnfoldModelAdmin):
    pass


@admin.register(User)
class UserAdmin(UserAdmin, BaseModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    model = User
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Личная информация"), {"fields": ("first_name", "last_name", "middle_name", "phone_number")}),
        (_("Права доступа"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Важные даты"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "phone_number", "first_name", "last_name", "middle_name", "password1", "password2"),
            },
        ),
    )
    list_display = ('id', 'email', 'first_name', 'last_name')
    list_filter = ("is_staff", "is_superuser", "is_active", "groups",)
    search_fields = ("email",)
    ordering = ('-date_joined',)
    list_display_links = ('id', 'email')
    list_per_page = 50
