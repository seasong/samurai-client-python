from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
import hashlib
from django.contrib.auth.models import User
from feefighters.payment_method import PaymentMethod as CorePaymentMethod
from feefighters.transaction import Transaction as CoreTransaction

def secret_id_for_user(user):
    hash = hashlib.sha1()
    hash.update(str(user.id) + settings.SAMURAI_SALT)
    return hash.hexdigest()

class RemoteObject(object):
    def as_dict(self):
        return self._core_remote_object.as_dict()

class PaymentMethod(models.Model, RemoteObject):
    payment_method_token = models.CharField(max_length=100, editable=False, unique=True)
    user = models.ForeignKey(User, editable=False)
    last_transaction_error = models.BooleanField(default=False) # stores whether the last transaction was an error
    disabled = models.BooleanField(default=False) 

    def __init__(self, *args, **kwargs):
        super(PaymentMethod, self).__init__(*args, **kwargs)

        # Gonna do_fetch = False here. We don't want to fetch every object every time we run PaymentMethod.objects.all() in the shell
        # And we won't have control over fetching when we do a filter.
        self._core_remote_object = CorePaymentMethod(feefighters = settings.SAMURAI_CREDENTIALS,
            payment_method_token = self.payment_method_token, do_fetch = False)

        self._get_fields_from_core()

    def _get_fields_from_core(self):
        for field_name in self._core_remote_object.field_names + ['payment_method_token', 'populated']:
            setattr(self, field_name, getattr(self._core_remote_object, field_name))

    def _set_fields_into_core(self):
        for field_name in self._core_remote_object.field_names:
            setattr(self._core_remote_object, field_name, getattr(self, field_name))

    def fetch(self):
        self._set_fields_into_core()
        result = self._core_remote_object.fetch()
        self._get_fields_from_core()
        return result

    def redact(self):
        self._set_fields_into_core()
        result = self._core_remote_object.redact()
        self._get_fields_from_core()
        return result

    def retain(self):
        self._set_fields_into_core()
        result = self._core_remote_object.retain()
        self._get_fields_from_core()
        return result

    def update(self):
        self._set_fields_into_core()
        result = self._core_remote_object.update()
        self._get_fields_from_core()
        return result


    def clean(self):
        "checks the custom field for a unique identifier related to self.user as a security measure"

        if self.custom.get('django_user_unique', None) != secret_id_for_user(self.user):
            raise ValidationError("Secret user id doesn't match!")
        if 'django_prev_payment_method_token' in self.custom:
            prev_payment_method_token_query = PaymentMethod.objects.filter(payment_method_token = self.custom['django_prev_payment_method_token'])
            if prev_payment_method_token_query.exists():
                if prev_payment_method_token_query[0].user != self.user:
                    raise ValidationError("Old payment method token of different user.")
       
#    def replace(self, payment_method):
#
#       self.payment_method_token = 
#       self.delete()

class Transaction(models.Model, RemoteObject):
    transaction_token = models.CharField(max_length=100, editable=False)
    processor_token = models.CharField(max_length=100, editable=False)
    reference_id = models.CharField(unique = True, max_length=100, editable=False)
    payment_method = models.ForeignKey(PaymentMethod, editable=False)
    transaction_type = models.CharField(max_length=20, editable=False)
    amount = models.CharField(max_length=10, editable=False, blank = True, default="") # null and blank to avoid migration
    currency_code = models.CharField(max_length=10, editable=False, blank = True, default="")
    created_at = models.DateTimeField(editable=False, null = True, blank = True, default=None)
    processor_success = models.NullBooleanField(editable=False, null = True, blank = True, default=None)

    def __init__(self, *args, **kwargs):
        super(Transaction, self).__init__(*args, **kwargs)

        # Gonna do_fetch = False here. We don't want to fetch every object every time we run Transaction.objects.all() in the shell
        # And we won't have control over fetching when we do a filter.
        if self.reference_id == None:
            self._core_remote_object = CoreTransaction(feefighters = settings.SAMURAI_CREDENTIALS,
                payment_method = self.payment_method._core_remote_object, processor_token = self.processor_token, do_fetch = False)
        else:
            self._core_remote_object = CoreTransaction(feefighters = settings.SAMURAI_CREDENTIALS,
                reference_id = self.reference_id, processor_token = self.processor_token, do_fetch = False)

        # exclude here since overwriting before fetch could wipe out what's from the DB
        # all we want are things that aren't in the database. Even if it's a new transaction and the values are None, we want the attributes there.
        self._get_fields_from_core(exclude = ["transaction_token", "reference_id", "transaction_type", "amount", "currency_code",
            "created_at", "processor_success"])
        self._set_fields_into_core()

    def _get_fields_from_core(self, exclude = []):
        for field_name in set(self._core_remote_object.field_names + ['populated']) - set(['payment_method', 'processor_token']) - set(exclude):
            setattr(self, field_name, getattr(self._core_remote_object, field_name))

        # self.payment_method should really always be set, but I'm avoiding unnecessary errors if I made a mistake somewhere
        if self.payment_method and self._core_remote_object.payment_method: 
            self.payment_method._core_remote_object = self._core_remote_object.payment_method

    def _set_fields_into_core(self):
        for field_name in set(self._core_remote_object.field_names) - set(['payment_method', 'processor_token']):
            setattr(self._core_remote_object, field_name, getattr(self, field_name))
        self._core_remote_object.payment_method = self.payment_method._core_remote_object
        

    def _save_new_transaction(self, new_transaction_core):
        new_transaction = Transaction(transaction_token = new_transaction_core.transaction_token, reference_id = new_transaction_core.reference_id,
            payment_method = self.payment_method, transaction_type = new_transaction_core.transaction_type, amount = new_transaction_core.amount,
            currency_code = new_transaction_core.currency_code, created_at = new_transaction_core.created_at,
            processor_success = new_transaction_core.processor_success )
        try:
            new_transaction.full_clean()
            new_transaction.save()
        except:
            self._set_payment_method_last_transaction_error(True)
            return None
        else:
            self._set_payment_method_last_transaction_error(False)
            new_transaction._core_remote_object = new_transaction_core
            new_transaction._get_fields_from_core()
            return new_transaction

    def _set_payment_method_last_transaction_error(self, error):
        payment_method = self.payment_method
        payment_method.last_transaction_error = error
        payment_method.save()

    def purchase(self, amount, currency_code, billing_reference, customer_reference):
        self._set_fields_into_core()
        result = self._core_remote_object.purchase(amount, currency_code, billing_reference, customer_reference)
        self._get_fields_from_core()
        try:
            self.full_clean()
        except:
            self._set_payment_method_last_transaction_error(True)
            return False
        if self.reference_id != "":
            self.save()
        self._set_payment_method_last_transaction_error(not result)
        return result

    def authorize(self, amount, currency_code, billing_reference, customer_reference):
        self._set_fields_into_core()
        result = self._core_remote_object.authorize(amount, currency_code, billing_reference, customer_reference)
        self._get_fields_from_core()
        try:
            self.full_clean()
        except:
            return False
        self.save()
        self._set_payment_method_last_transaction_error(not result)
        return result

    def capture(self, amount):
        self._set_fields_into_core()
        new_transaction_core = self._core_remote_object.capture(amount)
        return self._save_new_transaction(new_transaction_core)

    def void(self):
        self._set_fields_into_core()
        new_transaction_core = self._core_remote_object.void()
        return self._save_new_transaction(new_transaction_core)

    def credit(self, amount):
        self._set_fields_into_core()
        new_transaction_core = self._core_remote_object.credit(amount)
        return self._save_new_transaction(new_transaction_core)

    def fetch(self):
        self._set_fields_into_core()
        result = self._core_remote_object.fetch()
        self._get_fields_from_core()
        return result
