import json
from util.remote_object import RemoteObject
from payment_method import PaymentMethod

class Transaction(RemoteObject):

    reference_id        = None
    transaction_token   = None
    created_at          = None
    descriptor          = {}
    custom              = {}
    transaction_type    = None
    amount              = None
    currency_code       = None
    processor_success     = None
    payment_method      = None

    field_names = ["reference_id", "created_at", "descriptor", "custom", "transaction_type", "amount",
                    "currency_code", "processor_success", "payment_method", "info", "errors", "transaction_token"]

    json_field_names = ["custom", "descriptor"]

    head_xml_element_name = "transaction"

    def __init__(self, **kwargs):
        self.populated = False
        if kwargs.get('reference_id', None) == kwargs.get('payment_method', None) == None:
            raise ValueError("Must supply either a reference_id or a payment_method")

        if 'feefighters' in kwargs:
            self._merchant_key = kwargs['feefighters'].merchant_key
            self._merchant_password = kwargs['feefighters'].merchant_password
        else:
            self._merchant_key = kwargs['merchant_key']
            self._merchant_password = kwargs['merchant_password']

        if kwargs.get('reference_id', None):   # pull up info for an existing transaction
            self.reference_id = kwargs.get('reference_id', None)
            if kwargs.get('do_fetch', True):
                self.fetch()
        else:                   # create a new transaction                              
            self.payment_method = kwargs.get('payment_method', None)
            if kwargs.get('do_fetch', True):
                self.payment_method.fetch()
            self.processor_token = kwargs['processor_token'] # can be got from the transaction via fetch, if a reference_id is there

        self.errors = []
        self.info = []

    def _transaction_request(self, request_name, url_parameter, payload = {}, field_names = None):
        success = True
        if self._remote_object_request(request_name, url_parameter, payload, field_names):
            if type(self.payment_method) == dict:
                self.payment_method = PaymentMethod(payment_method_initial = {'payment_method':self.payment_method}, merchant_key = self._merchant_key,
                    merchant_password = self._merchant_password)
            if self.payment_method.errors:
                self.errors.append({"error":{"errors":[{"context": "client", "source": "client", "key": "errors_in_returned_payment_method" }], "info":[]}})
                success = False
        else:
            if type(self.payment_method) == dict:
                self.payment_method = PaymentMethod(payment_method_initial = {'payment_method':self.payment_method}, merchant_key = self._merchant_key,
                    merchant_password = self._merchant_password)
            success = False

        if self.transaction_type:
            self.transaction_type = self.transaction_type.lower() # so we don't get tripped up remembering "Purchase" vs "purchase"
        return success

    def _add_json_fields(self, out_data):
        for field in ['custom', 'descriptor']:
            if getattr(self, field) != None:
                try:
                    out_data['transaction'][field] = json.dumps(getattr(self, field))
                except:
                    self.errors.append({"error":{"errors":[{"context": "client", "source": "client", "key": "json_encoding_error" }], "info":[]}})
                    return False
            else:
                out_data['transaction'][field] = "{}"

        return True


    def purchase(self, amount, currency_code, billing_reference, customer_reference): # default 'USD'?
        if self.reference_id:
            self.errors = [{"context": "client", "source": "client", "key": "attempted_purchase_on_existing_transaction" }]
            return False

        out_data = {'transaction':{
            'type':'purchase',
            'amount': str(amount),
            'currency_code': currency_code,
            'payment_method_token': self.payment_method.payment_method_token,
            'billing_reference':billing_reference,
            'customer_reference':customer_reference,
        }}

        if not self._add_json_fields(out_data):
            return False

        return self._transaction_request("purchase_transaction", self.processor_token, out_data)

    def authorize(self, amount, currency_code, billing_reference, customer_reference): # default 'USD'?
        if self.reference_id:
            return {"error":{"errors":[{"context": "client", "source": "client", "key": "attempted_authorize_on_existing_transaction" }], "info":[]}}

        out_data = {'transaction':{
            'type':'authorize',
            'amount': str(amount),
            'currency_code': currency_code,
            'payment_method_token': self.payment_method.payment_method_token,
            'billing_reference':billing_reference,
            'customer_reference':customer_reference,
        }}

        if not self._add_json_fields(out_data):
            return False

        return self._transaction_request("authorize_transaction", self.processor_token, out_data)

    def capture(self, amount): # default 'USD'?
        # in case we're rebuilding this transaction from a reference_id, and they didn't want to fetch initially
        if self.transaction_token == None:
            self.fetch()

        new_transaction = Transaction(merchant_key = self._merchant_key, merchant_password = self._merchant_password, 
                                      reference_id=self.reference_id, do_fetch= False)
        new_transaction.transaction_token = self.transaction_token

        out_data = {'transaction':{
            'amount': str(amount),
        }}

        new_transaction._transaction_request("capture_transaction", new_transaction.transaction_token, out_data)

        return new_transaction

    def void(self):
        # in case we're rebuilding this transaction from a reference_id, and they didn't want to fetch initially
        if self.transaction_token == None:
            self.fetch()

        new_transaction = Transaction(merchant_key = self._merchant_key, merchant_password = self._merchant_password, 
                                      reference_id=self.reference_id, do_fetch= False)
        new_transaction.transaction_token = self.transaction_token

        new_transaction._transaction_request("void_transaction", new_transaction.transaction_token)

        return new_transaction

    def credit(self, amount):
        # in case we're rebuilding this transaction from a reference_id, and they didn't want to fetch initially
        if self.transaction_token == None:
            self.fetch()

        out_data = {'transaction':{
            'amount': str(amount),
        }}

        new_transaction = Transaction(merchant_key = self._merchant_key, merchant_password = self._merchant_password, 
                                      reference_id=self.reference_id, do_fetch= False)
        new_transaction.transaction_token = self.transaction_token

        new_transaction._transaction_request("credit_transaction", new_transaction.transaction_token, out_data)

        return new_transaction

    def fetch(self):
        return self._transaction_request("fetch_transaction", self.reference_id, {},list(set(self.field_names) - set(['reference_id'])))
