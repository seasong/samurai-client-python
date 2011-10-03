from datetime import datetime

from xml.dom.minidom import parseString as parseStringToXML, Node

class XmlUtil(object):
    @staticmethod
    def dict_to_xml(in_data):
        doc_tagname = in_data.keys()[0]
        xml = parseStringToXML("<%s></%s>" % (doc_tagname, doc_tagname) )
        for tag_name, tag_value in in_data[doc_tagname].iteritems():
            newElement = xml.createElement(tag_name)
            newTextNode = xml.createTextNode( str(tag_value) )
            xml.documentElement.appendChild( newElement )
            newElement.appendChild( newTextNode )
        return xml.toxml()

    @staticmethod
    def xml_to_dict(xml_string):
        try:
            xml_data = parseStringToXML(xml_string)
        except: # parse error, or something
            return None # error code, perhaps

        return XmlUtil.xml_outer_node_to_dict(xml_data.documentElement)

    # I made a mistake here. I should have made this more agnostic to tag names, and only looked at the type attribute
    # and context/key in the case of messages. The consumer of the dict should take care of making it convenient
    # for the consumer of the classes. Probably not worth going back at this point, though.
    @staticmethod
    def xml_outer_node_to_dict(xml_node):
        out_data = {'errors':[], 'info':[]}

        # from their API, we don't expect more than two levels of nodes.
        # doc_element > messages > message, or doc_element > datum 
        # with the exceptions of processor_response, and an embedded payment_method
        for outer_node in (node for node in xml_node.childNodes if node.nodeType == Node.ELEMENT_NODE):
            element_type = outer_node.getAttribute('type')
            element_name = outer_node.tagName

            if element_name == 'payment_method':
                payment_method = XmlUtil.xml_outer_node_to_dict(outer_node)['payment_method']
                out_data['payment_method'] = payment_method
            elif element_name == 'processor_response':
                # the structure of 'processor_response' happens to be very similar to the document at large. level 1, data. level 2, messages
                # so we'll just call this function recursively
                processor_response = XmlUtil.xml_outer_node_to_dict(outer_node)['processor_response']
                out_data['processor_success'] = processor_response.get('success', False)
                for error in processor_response['errors']:
                    out_data['errors'].append( dict(error , source = "processor") ) # it's set as a "samurai" error
                for info in processor_response['info']:
                    out_data['info'].append( dict(info , source = "processor") ) # it's set as a "samurai" info 
            # doc_element > messages > message 
            elif element_name == 'messages':
                for message in outer_node.getElementsByTagName("message"):
                    # ({'context': context, 'key': key }, samurai/processor)
                    if message.getAttribute('subclass') == "error":
                        out_data['errors'].append( { 'context': message.getAttribute('context'), 'key': message.getAttribute('key'), 'source': "samurai"} )
                    if message.getAttribute('subclass') == "info":
                        out_data['info'].append( { 'context': message.getAttribute('context'), 'key': message.getAttribute('key'), 'source': "samurai"} )

            # doc_element > datum 
            else: 
                if outer_node.childNodes == []:
                    out_data[element_name] = ""
                else:
                    for inner_node in (node for node in outer_node.childNodes if node.nodeType == Node.TEXT_NODE):
                        if element_type == 'integer':
                            out_data[element_name] = int(inner_node.nodeValue)
                        elif element_type == 'datetime':
                            out_data[element_name] = datetime.strptime(inner_node.nodeValue, "%Y-%m-%d %H:%M:%S UTC")
                        elif element_type == 'boolean':
                            out_data[element_name] = {'true':True, 'false':False} [ inner_node.nodeValue ]
                        else:
                            out_data[element_name] = inner_node.nodeValue

            return { xml_node.tagName: out_data }

