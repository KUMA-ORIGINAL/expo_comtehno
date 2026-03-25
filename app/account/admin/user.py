from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.html import format_html
from django_countries import countries

from unfold.admin import ModelAdmin as UnfoldModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from ..models import User
from common.base_admin import BaseModelAdmin

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(GroupAdmin, UnfoldModelAdmin):
    pass


@admin.register(User)
class UserAdmin(UserAdmin, BaseModelAdmin):
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    model = User
    list_filter = ("is_staff", "is_superuser", "is_active", "groups",)
    search_fields = ("phone_number",)
    ordering = ('-date_joined',)
    list_display_links = ('id', 'phone_number')
    list_per_page = 50