"""Shared base and field helpers for the NHCX models."""

from django.db import models

from care.emr.models.base import EMRBaseModel

CODE_LENGTH = 255
URL_LENGTH = 1024


class NhcxBaseModel(EMRBaseModel):
    """EMRBaseModel whose ``delete()`` removes the row.

    The specs replace child rows wholesale (delete then insert) under unique
    keys such as ``(claim, kind, code)``; a soft-deleted row would keep the key
    taken, so NHCX rows are deleted for real.
    """

    class Meta:
        abstract = True

    def delete(self, *args, **kwargs):
        return models.Model.delete(self, *args, **kwargs)


def code_field(**kwargs):
    kwargs.setdefault("max_length", CODE_LENGTH)
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.CharField(**kwargs)


def url_field(**kwargs):
    kwargs.setdefault("max_length", URL_LENGTH)
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.CharField(**kwargs)


def text_field(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.TextField(**kwargs)


def json_field(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.JSONField(**kwargs)


def money_field(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.DecimalField(max_digits=20, decimal_places=2, **kwargs)


def quantity_field(**kwargs):
    return models.DecimalField(max_digits=12, decimal_places=2, **kwargs)


def timestamp_field(**kwargs):
    kwargs.setdefault("null", True)
    kwargs.setdefault("blank", True)
    return models.DateTimeField(**kwargs)


class LegStage(models.TextChoices):
    """The leg a row belongs to (D17, D23, D24, D28, D29 ``stage``)."""

    preauth = "preauth"
    claim = "claim"
