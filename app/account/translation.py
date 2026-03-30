from modeltranslation.translator import TranslationOptions, register

from account.models import RegistrationCampaign, RegistrationField


@register(RegistrationCampaign)
class RegistrationCampaignTranslationOptions(TranslationOptions):
    fields = (
        "title",
        "subtitle",
        "applicant_email_subject",
        "applicant_email_body",
        "staff_email_subject",
        "staff_email_body",
        "success_message",
        "participation_terms",
        "event_dates",
        "event_schedule",
        "event_location",
        "event_contact",
        "ticket_footer_note",
    )


@register(RegistrationField)
class RegistrationFieldTranslationOptions(TranslationOptions):
    fields = (
        "label",
        "choices_text",
    )
