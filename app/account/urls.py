from django.urls import path

from account import views


urlpatterns = [
    path("", views.exhibition_landing, name="exhibition_landing"),
    path("registration/", views.exhibition_register_email, name="exhibition_register_email"),
    path("registration/form/", views.exhibition_register, name="exhibition_register"),
    path("registration/success/", views.exhibition_register_success, name="exhibition_register_success"),
    path("checkin/", views.exhibition_checkin, name="exhibition_checkin"),
    path("ticket/<str:token>/", views.exhibition_ticket, name="exhibition_ticket"),
    path("ticket/<str:token>/pdf/", views.exhibition_ticket_pdf, name="exhibition_ticket_pdf"),
    path("ticket/<str:token>/print/", views.exhibition_ticket_print, name="exhibition_ticket_print"),
    path("contacts/", views.contacts_page, name="contacts_page"),
]
