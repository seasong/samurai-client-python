class FeeFighters(object):
    "If you want to create multiple payment methods without repeating yourself with the authentication info, you can use this"

    def __init__(self, **kwargs):
        self.merchant_key = kwargs["merchant_key"]
        self.merchant_password = kwargs["merchant_password"]