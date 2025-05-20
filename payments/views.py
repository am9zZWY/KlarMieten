import json
import logging

import stripe
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from klarmieten import settings

logger = logging.getLogger(__name__)

# Initialize Stripe API
stripe.api_key = settings.STRIPE_SECRET_KEY

# For sample support and debugging, not required for production:
stripe.set_app_info(
    'stripe-samples/checkout-single-subscription',
    version='0.0.1',
    url='https://github.com/stripe-samples/checkout-single-subscription')

stripe.api_version = '2020-08-27'


# Fetch the Checkout Session to display the JSON result on the success page
def get_checkout_session(request):
    session_id = request.GET.get('sessionId')
    checkout_session = stripe.checkout.Session.retrieve(session_id)
    return JsonResponse(checkout_session)


@require_http_methods(["POST"])
def create_checkout_session(request):
    price = request.POST.get('priceId')
    domain_url = settings.DOMAIN

    try:
        # Create new Checkout Session for the order
        checkout_session = stripe.checkout.Session.create(
            success_url=domain_url + '/success/?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=domain_url + '/canceled/',
            mode='subscription',
            # automatic_tax={'enabled': True},
            line_items=[
                {
                    'price': price,
                    'quantity': 1,
                },
            ]
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        logger.error(e)
        return JsonResponse({'error': {'message': str(e)}}, status=400)


@require_http_methods(["POST"])
def customer_portal(request):
    # For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
    checkout_session_id = request.POST.get('sessionId')
    checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)

    # This is the URL to which the customer will be redirected after they are
    # done managing their billing with the portal.
    return_url = settings.DOMAIN

    session = stripe.billing_portal.Session.create(
        customer=checkout_session.customer,
        return_url=return_url,
    )
    return redirect(session.url, code=303)


@csrf_exempt
def webhook_received(request):
    # You can use webhooks to receive information about asynchronous payment events.
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    if request.method == 'POST':
        request_data = json.loads(request.body)

        if webhook_secret:
            # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
            signature = request.META.get('HTTP_STRIPE_SIGNATURE')
            try:
                event = stripe.Webhook.construct_event(
                    payload=request.body, sig_header=signature, secret=webhook_secret)
                data = event['data']
            except Exception as e:
                return HttpResponse(str(e), status=400)
            # Get the type of webhook event sent - used to check the status of PaymentIntents.
            event_type = event['type']
        else:
            data = request_data['data']
            event_type = request_data['type']
        data_object = data['object']

        print('event ' + event_type)

        if event_type == 'checkout.session.completed':
            print('🔔 Payment succeeded!')

        return JsonResponse({'status': 'success'})

    return HttpResponse(status=400)
