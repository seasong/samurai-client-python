import json

from util.remote_object import RemoteObject

class PaymentMethod(RemoteObject):

    payment_method_token = None
    created_at = None
    updated_at = None
    custom = {}
    is_retained = None
    is_redacted = None
    is_sensitive_data_valid = None
    last_four_digits = None
    card_type = None
    first_name = None
    last_name = None
    expiry_month = None
    expiry_year = None
    address_1 = None
    address_2 = None
    city = None
    state = None
    zip = None
    country = None

    _last_data = None

    field_names = ["created_at", "updated_at", "is_retained", "is_redacted", "is_sensitive_data_valid", "errors", "info", 
        "last_four_digits", "card_type", "first_name", "last_name", "expiry_month", "expiry_year", "address_1", "address_2",
        "city", "state",  "zip", "country", "custom"]

    json_field_names = ["custom"]

    updatable_field_names = [name for name in field_names if name not in ['custom', 'created_at', 'updated_at', 'errors', 'info']]

    head_xml_element_name = "payment_method"

    def __init__(self, *args, **kwargs):
        if 'feefighters' in kwargs and 'payment_method_initial' in kwargs:
            raise ValueError("Can't supply both feefighters and payment_method_initial")
        
        if 'payment_method_initial' in kwargs:
            # we want to grab the token here, since this payment method will probably be coming back from a transaction
            self._load_data_from_dict(kwargs['payment_method_initial'], self.field_names + ["payment_method_token"])
            self._merchant_key = kwargs['merchant_key']
            self._merchant_password = kwargs['merchant_password']
        elif 'feefighters' in kwargs:
            self._merchant_key = kwargs['feefighters'].merchant_key
            self._merchant_password = kwargs['feefighters'].merchant_password
            self.payment_method_token = kwargs['payment_method_token']
        else:
            self._merchant_key = kwargs['merchant_key']
            self._merchant_password = kwargs['merchant_password']
            self.payment_method_token = kwargs['payment_method_token']

        self._last_data = {}
        self.populated = False
        if kwargs.get("do_fetch", True):
            self.fetch() # why not? probably gonna do this anyway

        self.errors = []
        self.info = []

    def update(self):
        out_data = {'payment_method':{}}

        for attr_name in self.updatable_field_names:
            # the None would be if they hadn't fetched yet
            if self._last_data.get(attr_name, None) != getattr(self, attr_name) and getattr(self, attr_name) != None:
                out_data['payment_method'][attr_name] = getattr(self, attr_name)

        if self.custom != None and ('custom' not in self._last_data or json.loads(self._last_data['custom']) != self.custom):
            try:
                out_data['payment_method']['custom'] = json.dumps(self.custom)
            except:
                self.errors.append({"error":{"errors":[{"context": "client", "source": "client", "key": "json_encoding_error" }], "info":[]}})
                return False

        return self._remote_object_request("update_payment_method", self.payment_method_token, out_data)
        
    def fetch(self):
        return self._remote_object_request("fetch_payment_method", self.payment_method_token)

    def retain(self):
        return self._remote_object_request("retain_payment_method", self.payment_method_token)

    def redact(self):
        return self._remote_object_request("redact_payment_method", self.payment_method_token)
