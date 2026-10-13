from django.contrib import admin

from care.nhcx import models

for model in (
    models.FacilityProfile,
    models.PractitionerProfile,
    models.Claim,
    models.ClaimPlan,
    models.ClaimAuth,
    models.ClaimPreauth,
    models.ClaimSubmission,
    models.ClaimPayment,
    models.ClaimQuery,
    models.ClaimEnquiry,
    models.Counter,
):
    admin.site.register(model)
