import logging

from django.conf import settings
from django.core.management import call_command

logger = logging.getLogger(__name__)


def compile_translations_after_migrate(sender, **kwargs):
    """
    Keep compiled translation catalogs up to date after migrations.
    """
    if getattr(settings, "RUNNING_TESTS", False):
        return

    logger.info("Running compilemessages after migrate for app '%s'", sender.label)
    try:
        call_command("compilemessages", verbosity=0)
    except Exception:
        logger.exception("compilemessages failed after migrate")
