from django.contrib import admin

from contract_analysis.models.contract import Contract, ContractDetails

admin.site.register(Contract)
admin.site.register(ContractDetails)
