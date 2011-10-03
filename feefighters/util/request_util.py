import urllib2
import base64

from xml_util import XmlUtil

class RequestUtil(object):
    @staticmethod
    def request(method, url, username, password, out_data={}):
        """
            Takes an input dictionary. For PUT, sends as XML payload to the supplied URL with the given method.
            For POST, sends as POST variables.
            Returns XML result as dictionary, accounting for FeeFighters' conventions, setting datatypes

            Raises/Returns error in case of HTTPS error, <error> outer tag returned
        """

        request_debugging = 1

        req = RequestWithPut(url)
        base64string = base64.encodestring('%s:%s' % (username, password))[:-1]
        authheader =  "Basic %s" % base64string
        req.add_header("Authorization", authheader)

        try:
            if method == "GET":
                handle = urllib2.urlopen(req)
            else:
                if method == "PUT":
                    req.use_put_method = True
                req.add_header('Content-Type', 'application/xml')
                if (out_data):
                    payload = XmlUtil.dict_to_xml(out_data)
                else:
                    payload = ""

                # Build the opener, using HTTPS handler
                opener = urllib2.build_opener(urllib2.HTTPSHandler(debuglevel=request_debugging))
                handle = opener.open(req, payload)

                # handle = urllib2.urlopen(req, payload)

            in_data = handle.read()
            handle.close()

            return XmlUtil.xml_to_dict(in_data)
        except urllib2.HTTPError, e:
            if request_debugging:
                print e.read()
            return {"error":{"errors":[{"context": "client", "source": "client", "key": "http_error_response_" + str(e.code) }], "info":[]}}
        except:
            return {"error":{"errors":[{"context": "client", "source": "client", "key": "unknown_response_error" }], "info":[]}}

class RequestWithPut(urllib2.Request):
    use_put_method = False
    def get_method(self):
        super_method = urllib2.Request.get_method(self) # can't use super, urllib2.Request seems to be old-style class
        if self.use_put_method and super_method == 'POST':
            return 'PUT'
        else:
            return super_method
