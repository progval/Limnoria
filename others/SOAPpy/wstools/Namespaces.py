#! /usr/bin/env python
"""Namespace module, so you don't need PyXML 
"""

try:
    from xml.ns import SOAP, SCHEMA, WSDL, XMLNS, DSIG, ENCRYPTION
except:
    class SOAP:
        ENV         = "http://schemas.xmlsoap.org/soap/envelope/"
        ENC         = "http://schemas.xmlsoap.org/soap/encoding/"
        ACTOR_NEXT  = "http://schemas.xmlsoap.org/soap/actor/next"

    class SCHEMA:
        XSD1        = "http://www.w3.org/1999/XMLSchema"
        XSD2        = "http://www.w3.org/2000/10/XMLSchema"
        XSD3        = "http://www.w3.org/2001/XMLSchema"
        XSD_LIST    = [ XSD1, XSD2, XSD3 ]
        XSI1        = "http://www.w3.org/1999/XMLSchema-instance"
        XSI2        = "http://www.w3.org/2000/10/XMLSchema-instance"
        XSI3        = "http://www.w3.org/2001/XMLSchema-instance"
        XSI_LIST    = [ XSI1, XSI2, XSI3 ]
        BASE        = XSD3

    class WSDL:
        BASE        = "http://schemas.xmlsoap.org/wsdl/"
        BIND_HTTP   = "http://schemas.xmlsoap.org/wsdl/http/"
        BIND_MIME   = "http://schemas.xmlsoap.org/wsdl/mime/"
        BIND_SOAP   = "http://schemas.xmlsoap.org/wsdl/soap/"

    class XMLNS:
        BASE        = "http://www.w3.org/2000/xmlns/"
        XML         = "http://www.w3.org/XML/1998/namespace"
        HTML        = "http://www.w3.org/TR/REC-html40"

    class DSIG:
        BASE         = "http://www.w3.org/2000/09/xmldsig#"
        C14N         = "http://www.w3.org/TR/2000/CR-xml-c14n-20010315"
        C14N_COMM    = "http://www.w3.org/TR/2000/CR-xml-c14n-20010315#WithComments"
        C14N_EXCL    = "http://www.w3.org/2001/10/xml-exc-c14n#"
        DIGEST_MD2   = "http://www.w3.org/2000/09/xmldsig#md2"
        DIGEST_MD5   = "http://www.w3.org/2000/09/xmldsig#md5"
        DIGEST_SHA1  = "http://www.w3.org/2000/09/xmldsig#sha1"
        ENC_BASE64   = "http://www.w3.org/2000/09/xmldsig#base64"
        ENVELOPED    = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
        HMAC_SHA1    = "http://www.w3.org/2000/09/xmldsig#hmac-sha1"
        SIG_DSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#dsa-sha1"
        SIG_RSA_SHA1 = "http://www.w3.org/2000/09/xmldsig#rsa-sha1"
        XPATH        = "http://www.w3.org/TR/1999/REC-xpath-19991116"
        XSLT         = "http://www.w3.org/TR/1999/REC-xslt-19991116"

    class ENCRYPTION:
        BASE    = "http://www.w3.org/2001/04/xmlenc#"
        BLOCK_3DES    = "http://www.w3.org/2001/04/xmlenc#des-cbc"
        BLOCK_AES128    = "http://www.w3.org/2001/04/xmlenc#aes128-cbc"
        BLOCK_AES192    = "http://www.w3.org/2001/04/xmlenc#aes192-cbc"
        BLOCK_AES256    = "http://www.w3.org/2001/04/xmlenc#aes256-cbc"
        DIGEST_RIPEMD160    = "http://www.w3.org/2001/04/xmlenc#ripemd160"
        DIGEST_SHA256    = "http://www.w3.org/2001/04/xmlenc#sha256"
        DIGEST_SHA512    = "http://www.w3.org/2001/04/xmlenc#sha512"
        KA_DH    = "http://www.w3.org/2001/04/xmlenc#dh"
        KT_RSA_1_5    = "http://www.w3.org/2001/04/xmlenc#rsa-1_5"
        KT_RSA_OAEP    = "http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p"
        STREAM_ARCFOUR    = "http://www.w3.org/2001/04/xmlenc#arcfour"
        WRAP_3DES    = "http://www.w3.org/2001/04/xmlenc#kw-3des"
        WRAP_AES128    = "http://www.w3.org/2001/04/xmlenc#kw-aes128"
        WRAP_AES192    = "http://www.w3.org/2001/04/xmlenc#kw-aes192"
        WRAP_AES256    = "http://www.w3.org/2001/04/xmlenc#kw-aes256"


class WSSE:
    BASE    = "http://schemas.xmlsoap.org/ws/2002/04/secext"

class WSU:
    BASE    = "http://schemas.xmlsoap.org/ws/2002/04/utility"
    UTILITY = "http://schemas.xmlsoap.org/ws/2002/07/utility"

class WSR:
    PROPERTIES = "http://www.ibm.com/xmlns/stdwip/web-services/WS-ResourceProperties"
    LIFETIME   = "http://www.ibm.com/xmlns/stdwip/web-services/WS-ResourceLifetime"

class WSA:
    ADDRESS    = "http://schemas.xmlsoap.org/ws/2003/03/addressing"
    ADDRESS2004    = "http://schemas.xmlsoap.org/ws/2004/03/addressing"
    ANONYMOUS  = "%s/role/anonymous" %ADDRESS
    ANONYMOUS2004  = "%s/role/anonymous" %ADDRESS2004
    FAULT      = "http://schemas.xmlsoap.org/ws/2004/03/addressing/fault"

class WSP:
    POLICY = "http://schemas.xmlsoap.org/ws/2002/12/policy"



