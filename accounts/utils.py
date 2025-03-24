from accounts.models import Plan, PlanCapability, Capability, Product


def initialize_system():
    """Set up products, capabilities and plans"""

    # Create products
    analysis_product = Product.objects.get_or_create(
        code='contract_analysis',
        defaults={
            'name': 'Contract Analysis',
            'type': 'ANALYSIS',
            'description': 'Analysis of rental contracts'
        }
    )[0]

    chat_product = Product.objects.get_or_create(
        code='legal_chat',
        defaults={
            'name': 'Legal Chat',
            'type': 'CHAT',
            'description': 'AI-powered legal chat assistant'
        }
    )[0]

    # Create capabilities
    capabilities = {}

    # Integer-valued capabilities
    for code, name in [
        ('analyses', 'Number of Analyses'),
        ('storage_days', 'Storage Duration (Days)'),
        ('upload_size', 'Max Upload Size (MB)'),
        ('uploads', 'Number of Uploads'),
    ]:
        capabilities[code] = Capability.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'value_type': 'INTEGER'
            }
        )[0]

    # Boolean-valued capabilities
    for code, name in [
        ('pdf_export', 'PDF Export'),
        ('docx_import', 'DOCX Import'),
        ('extended_analysis', 'Extended Analysis'),
        ('unlimited_chat', 'Unlimited Chat Requests'),
        ('legal_advice_ai', 'Legal Advice via AI'),
        ('monthly_cancel', 'Monthly Cancelable')
    ]:
        capabilities[code] = Capability.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'value_type': 'BOOLEAN'
            }
        )[0]

    # Create plans

    # Student Plan (One-time)
    student_plan = Plan.objects.get_or_create(
        code='student',
        defaults={
            'name': 'Student',
            'product': analysis_product,
            'description': 'Für Studierende mit begrenztem Budget',
            'price': 4.00,
            'billing_type': 'ONE_TIME',
            'is_student_plan': True
        }
    )[0]

    # Set student plan capabilities
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

    # Basic Plan (One-time)
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

    # Set basic plan capabilities
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

    # Pro Plan (Subscription)
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

    # Set pro plan capabilities
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

    # Chat+ Plan (Subscription)
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

    # Set chat+ plan capabilities
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
