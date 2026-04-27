import base64
import io
import os

import qrcode
from django.conf import settings
from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.http import Http404
from django.utils.translation import gettext_lazy as _

SUBMISSION_TICKET_SALT = "reg-submission-ticket"

try:
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    REPORTLAB_AVAILABLE = True
except ModuleNotFoundError:
    REPORTLAB_AVAILABLE = False


def build_qr_data_uri(value: str) -> str:
    img = qrcode.make(value)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def build_qr_image_reader(value: str):
    img = qrcode.make(value)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def get_pdf_font_name():
    static_font = os.path.join(
        str(settings.BASE_DIR),
        "account",
        "static",
        "fonts",
        "Inter_18pt-Bold.ttf",
    )
    candidates = [
        ("InterBold18", static_font),
        ("ArialUnicode", "C:/Windows/Fonts/arial.ttf"),
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ("LiberationSans2", "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for font_name, font_path in candidates:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, font_path))
                return font_name
            except Exception:
                continue
    return "Helvetica"


def build_submission_ticket_token(submission_id: int) -> str:
    return signing.dumps({"submission_id": submission_id}, salt=SUBMISSION_TICKET_SALT)


def ensure_submission_ticket_token(submission) -> str:
    if submission.ticket_token:
        return submission.ticket_token
    token = build_submission_ticket_token(submission.id)
    submission.ticket_token = token
    submission.save(update_fields=["ticket_token"])
    return token


def get_submission_by_ticket_token(token: str):
    from account.models.registration import RegistrationSubmission

    try:
        payload = signing.loads(token, salt=SUBMISSION_TICKET_SALT)
        sid = payload.get("submission_id")
    except (BadSignature, SignatureExpired, ValueError, TypeError):
        raise Http404(_("Билет недействителен или срок ссылки истек."))
    if not sid:
        raise Http404(_("Билет не найден."))
    try:
        submission = RegistrationSubmission.objects.select_related("campaign").get(id=sid)
        if submission.ticket_token and submission.ticket_token != token:
            raise Http404(_("Билет недействителен."))
        if not submission.ticket_token:
            submission.ticket_token = token
            submission.save(update_fields=["ticket_token"])
        return submission
    except RegistrationSubmission.DoesNotExist:
        raise Http404(_("Билет не найден."))


def try_resolve_ticket_token(token: str):
    return "submission", get_submission_by_ticket_token(token)


def submission_ticket_code(submission_id: int) -> str:
    return f"REG-{int(submission_id):06d}"
