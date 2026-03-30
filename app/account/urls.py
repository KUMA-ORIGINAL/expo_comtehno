from django.urls import path

from account import views


urlpatterns = [
    path("", views.registration_index, name="registration_index"),
    path("r/<slug:slug>/", views.registration_form, name="registration_form"),
    path("r/<slug:slug>/success/", views.registration_success, name="registration_success"),
    path("ticket/<str:token>/", views.exhibition_ticket, name="exhibition_ticket"),
    path("ticket/<str:token>/pdf/", views.exhibition_ticket_pdf, name="exhibition_ticket_pdf"),
    path("ticket/<str:token>/print/", views.exhibition_ticket_print, name="exhibition_ticket_print"),
    path("checkin/", views.exhibition_checkin, name="exhibition_checkin"),
]
