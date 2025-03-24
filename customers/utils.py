from customers.models import Plan, PlanCapability, Capability, Product


def initialize_system():
    """Produkte, Fähigkeiten und Pläne einrichten"""

    # Produkte erstellen
    analysis_product = Product.objects.get_or_create(
        code='contract_analysis',
        defaults={
            'name': 'Vertragsanalyse',
            'type': 'ANALYSIS',
            'description': 'Analyse von Mietverträgen'
        }
    )[0]

    chat_product = Product.objects.get_or_create(
        code='legal_chat',
        defaults={
            'name': 'Rechtschat',
            'type': 'CHAT',
            'description': 'KI-gestützter rechtlicher Chat-Assistent'
        }
    )[0]

    # Fähigkeiten erstellen
    capabilities = {}

    # Ganzzahlige Fähigkeiten
    for code, name in [
        ('analyses', 'Anzahl der Analysen'),
        ('storage_days', 'Speicherdauer (Tage)'),
        ('upload_size', 'Max. Upload-Größe (MB)'),
        ('uploads', 'Anzahl der Uploads'),
    ]:
        capabilities[code] = Capability.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'value_type': 'INTEGER'
            }
        )[0]

    # Boolesche Fähigkeiten
    for code, name in [
        ('pdf_export', 'PDF-Export'),
        ('docx_import', 'DOCX-Import'),
        ('extended_analysis', 'Erweiterte Analyse'),
        ('unlimited_chat', 'Unbegrenzte Chat-Anfragen'),
        ('legal_advice_ai', 'Rechtsberatung via KI'),
        ('monthly_cancel', 'Monatlich kündbar')
    ]:
        capabilities[code] = Capability.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'value_type': 'BOOLEAN'
            }
        )[0]

    # Pläne erstellen

    # Studierenden-Plan (Einmalig)
    student_plan = Plan.objects.get_or_create(
        code='student',
        defaults={
            'name': 'Studierende',
            'product': analysis_product,
            'description': 'Für Studierende mit begrenztem Budget',
            'price': 4.00,
            'billing_type': 'ONE_TIME',
            'is_student_plan': True
        }
    )[0]

    # Studierenden-Plan Fähigkeiten festlegen
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['analyses'],
        defaults={'value_int': 1}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['uploads'],
        defaults={'value_int': 1}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['storage_days'],
        defaults={'value_int': 14}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['pdf_export'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['docx_import'],
        defaults={'value_bool': False}
    )

    # Basis-Plan (Einmalig)
    basic_plan = Plan.objects.get_or_create(
        code='basic',
        defaults={
            'name': 'Basic',
            'product': analysis_product,
            'description': 'Für die einmalige Nutzung',
            'price': 7.00,
            'billing_type': 'ONE_TIME'
        }
    )[0]

    # Basis-Plan Fähigkeiten festlegen
    PlanCapability.objects.get_or_create(
        plan=basic_plan, capability=capabilities['analyses'],
        defaults={'value_int': 1}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['uploads'],
        defaults={'value_int': 1}
    )
    PlanCapability.objects.get_or_create(
        plan=basic_plan, capability=capabilities['storage_days'],
        defaults={'value_int': 7}
    )
    PlanCapability.objects.get_or_create(
        plan=basic_plan, capability=capabilities['pdf_export'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=basic_plan, capability=capabilities['docx_import'],
        defaults={'value_bool': False}
    )

    # Pro-Plan (Abonnement)
    pro_plan = Plan.objects.get_or_create(
        code='pro',
        defaults={
            'name': 'Pro',
            'product': analysis_product,
            'description': 'Für mehrere Mietverträge',
            'price': 10.00,
            'billing_type': 'SUBSCRIPTION',
            'billing_interval': 'month'
        }
    )[0]

    # Pro-Plan Fähigkeiten festlegen
    PlanCapability.objects.get_or_create(
        plan=pro_plan, capability=capabilities['analyses'],
        defaults={'value_int': 5}
    )
    PlanCapability.objects.get_or_create(
        plan=student_plan, capability=capabilities['uploads'],
        defaults={'value_int': 5}
    )
    PlanCapability.objects.get_or_create(
        plan=pro_plan, capability=capabilities['storage_days'],
        defaults={'value_int': 30}
    )
    PlanCapability.objects.get_or_create(
        plan=pro_plan, capability=capabilities['pdf_export'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=pro_plan, capability=capabilities['docx_import'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=pro_plan, capability=capabilities['extended_analysis'],
        defaults={'value_bool': True}
    )

    # Chat+ Plan (Abonnement)
    chat_plus_plan = Plan.objects.get_or_create(
        code='chat_plus',
        defaults={
            'name': 'Chat+',
            'product': chat_product,
            'description': 'Persönlicher Rechtsassistent',
            'price': 2.00,
            'billing_type': 'SUBSCRIPTION',
            'billing_interval': 'month',
            'student_discount_percentage': 50
        }
    )[0]

    # Chat+ Plan Fähigkeiten festlegen
    PlanCapability.objects.get_or_create(
        plan=chat_plus_plan, capability=capabilities['unlimited_chat'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=chat_plus_plan, capability=capabilities['legal_advice_ai'],
        defaults={'value_bool': True}
    )
    PlanCapability.objects.get_or_create(
        plan=chat_plus_plan, capability=capabilities['monthly_cancel'],
        defaults={'value_bool': True}
    )
