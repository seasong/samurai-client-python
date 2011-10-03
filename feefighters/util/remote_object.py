import json
from request_util import RequestUtil

REQUESTS = {
    "transparent_redirect":     ("POST",     "https://api.samurai.feefighters.com/v1/payment_methods"),       # just for testing
    "fetch_payment_method":     ("GET",     "https://api.samurai.feefighters.com/v1/payment_methods/%s.xml"),
    "update_payment_method":    ("PUT",     "https://api.samurai.feefighters.com/v1/payment_methods/%s.xml"),
    "retain_payment_method":    ("POST",    "https://api.samurai.feefighters.com/v1/payment_methods/%s/retain.xml"),
    "redact_payment_method":    ("POST",    "https://api.samurai.feefighters.com/v1/payment_methods/%s/redact.xml"),
    "purchase_transaction":     ("POST",    "https://api.samurai.feefighters.com/v1/processors/%s/purchase.xml"),
    "authorize_transaction":    ("POST",    "https://api.samurai.feefighters.com/v1/processors/%s/authorize.xml"),
    "capture_transaction":      ("POST",    "https://api.samurai.feefighters.com/v1/transactions/%s/capture.xml"),
    "void_transaction":         ("POST",    "https://api.samurai.feefighters.com/v1/transactions/%s/void.xml"),
    "credit_transaction":      ("POST",    "https://api.samurai.feefighters.com/v1/transactions/%s/credit.xml"),
    "fetch_transaction":        ("GET",     "https://api.samurai.feefighters.com/v1/transactions/%s.xml"),
}

class RemoteObject(object):

    def _remote_object_request(self, request_name, url_parameter, payload = {}, field_names = None):
        "This is a method that handles all requests, and should update the object's attributes with the new data"

        if field_names == None:
            field_names = self.field_names
    
        request = REQUESTS[request_name]
        in_data = RequestUtil.request( request[0], request[1] % url_parameter, self._merchant_key, self._merchant_password, payload)

        return self._load_data_from_dict(in_data, field_names)

    def _load_data_from_dict(self, in_data, field_names): 

        self.errors = self.info = []

        # check if the head element is what we expect
        if "error" not in in_data and self.head_xml_element_name not in in_data:
            in_data = {'error': {'errors':[{'source': 'client', 'context': 'client', 'key': 'wrong_head_element'}], 'info':[]}}

        # check if we have all expected fields. if not, assume the whole thing is a wash.
        elif self.head_xml_element_name in in_data: # if this is a response with <error> as the head element, we won't expect these fields
            for field in field_names:
                if field not in in_data[self.head_xml_element_name]:
                    in_data = {'error': {'errors':[{'source': 'client', 'context': 'client', 'key': 'missing_fields'}], 'info':[]}}
                    break

        # handle <error> responses
        if "error" in in_data:
            self.errors = in_data['error']['errors']
            self.info = in_data['error']['info']

            self._last_data = None

            self.populated = False

            return False

        # handle responses with the expected head element
        else:
            for field in field_names:
                setattr(self, field, in_data[self.head_xml_element_name][field])

            for field in self.json_field_names:
                if in_data[self.head_xml_element_name][field] == "":
                    in_data[self.head_xml_element_name][field] = "{}"

                try:
                    setattr(self, field, json.loads(in_data[self.head_xml_element_name][field]))
                except:
                    self.errors.append({'source': 'client', 'context': 'client', 'key':'json_decoding_error'}  )

            self._last_data = in_data[self.head_xml_element_name] # so we know what changed, for update()

            self.populated = True

            return not bool(self.errors)

    def as_dict(self):
        fields_as_dict = {}
        for field_name in self.field_names:
            fields_as_dict[field_name] = getattr(self, field_name)
        return fields_as_dict 
