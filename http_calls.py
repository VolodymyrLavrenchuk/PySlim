# -*- coding: utf-8 -*-
from ExecuteQuery import Execute
from date_utils import DateUtils
from socket import error as socket_error
from waferslim.converters import convert_arg
import urllib2
import json
import re
import sys
import time
import random
from datetime import date, datetime
from mm_file import MMFile
from string import Template
import binascii

lastRequestResult = None
lastRequestError = None
lastResponse = None
lastResponseTime = None

class HttpCall:

    def open(self, req):

        try:

            print "------------------------------------------------"
            print "Method: %s" % req.get_method()
            print "Request url: %s" % req.get_full_url()
            print "Request headers: %s" % req.headers
            if(req.has_data()):
                print "Request body: %s" % req.get_data()
            global lastResponse
            lastResponse = res = urllib2.urlopen(req)
            print "Response statusCode: %s" % res.getcode()
            print "Response headers: %s" % res.info().dict

        except BaseException, e:

            global lastRequestError
            global lastResponse
            lastResponse = lastRequestError = res = e
            print "Request error: %s" % e

        return res

    def request(self, url, args = None, headers = {}):

        return urllib2.Request(url, args, headers)
    
    def read(self, req):

        start = time.time()
        resp = self.open(req)

        global lastResponseTime
        lastResponseTime = time.time() - start
        print "Response time: %f sec." % lastResponseTime

        ret = None
        
        if type(resp) != urllib2.URLError and type(resp) != socket_error and type(resp) != TypeError:

            ret = resp.read()
            print "Response body: %s" % ret
            global lastRequestResult
            lastRequestResult = ret
            
        return ret
        
    def GET(self,url, headers = {}, args = None):

        if args:
            url = url + urllib2.quote(args,'=&')
        req = self.request(url, None, headers)

        return self.read(req)

    def setHostUrl( self, url ):

        global host_url
        host_url = url

    def get_full_url( self, url ):

        global host_url
        return url if url.startswith( "http://" ) or url.startswith( "https://" ) else host_url + url

class RestTools( HttpCall ):

    http_headers = {'Content-Type': 'application/json', 'Accept':'application/json'}

    def getRequest(self, url, data=None, headers={}):

        return self.request(self.get_full_url(url), data, headers)

    def get_str(self, url, args = None):

        return self.GET(self.get_full_url(url), {'Accept':'application/json'}, args)

    def get_hex_str( self, url, args = None ):

        resp = self.get_str( url, args )
        return binascii.hexlify( resp )

    def searchRegexpInHtml(self, pattern, url ):

        import re
        res = self.GET(url)
        data = re.search(pattern, res, re.M)
        return data.group(1)
     
    def get_json(self, url, args = None):

        try:
            res = []
            resp = self.get_str(url, args)
            if resp:
                res = json.loads(resp)
                if(type(res) == dict and res.has_key("hits")):
                    res = res["hits"]
        except ValueError:

            print "Failed to parse json"

        return res
    
    def get_attr_by_type(self,data, attr):

        res = data
        index = 0
        for a in attr.split('.'):

            match = re.match('^(\w*)\[([0-9])\]', a)
            if match:
                a = match.group(1)
                index = int(match.group(2))

            if len(res) > 0:
                types = {
                    dict: lambda : res[a] if res.has_key(a) else res,
                    list: lambda : res[index][a]
                }
                res = types[type(res)]()

        return res 
    
    def getAttributeFromResponse(self, attr, url, args = None):

        return self.get_attr_by_type(self.get_json(url, args), attr)
    
    def getAttributeFromResponseAsString(self, attr, url, args = None):

        return str(self.getAttributeFromResponse(attr, url, args))

    def currentTimeDiff( self, attr, url, args = None ):

        return DateUtils().js_time_diff( self.getAttributeFromResponse( attr, url, args ) )

    def wait(self, wait_sec, retries, func, **kwargs):

        for r in range(int(retries)):
            if func(kwargs):
                return True
            self.sleep(wait_sec)        
        return False

    def quoteUrl( self, url ):

        return urllib2.quote( url )

    def waitSecondTimesUrlResponseAttributeHasValue(self, wait_sec, retries, url, attr, value):

        def func(args):

            resp = self.getAttributeFromResponse(args["attr"], args["url"])
            resp_type = type(resp)

            try :
                return resp == resp_type(value)
            except ValueError:
                return False
        
        return self.wait(wait_sec, retries, func, attr = attr, url = url)
        
    def waitSecondTimesUrlHasValidResponse(self, wait_sec, retries, url):

        def func(args):
            return self.get_json(args["url"])
            
        return self.wait(wait_sec, retries, func, url = url)
    
    def waitSecondTimesUrlArgsResponseValue(self, wait_sec, retries, url, attrs, value):

        def func(args):
            return self.get_str(url) == value
            
        return self.wait(wait_sec, retries, func)
    
    def sleep(self, sec):

        time.sleep(float(sec))
        
    def makeLine( self, line ):

        return line.replace( '\n', '\\n' )

    def POST( self, url, data = "", headers = "" ):

        data = data.replace( '\n', '\r\n' )
        req = self.getRequest( url, data, json.loads( headers ) if headers else self.http_headers )

        return self.read( req )

    def PUT(self,url,data = ""):

        req = self.getRequest( url, data, self.http_headers )
        req.get_method = lambda: 'PUT'

        return self.read( req )

    def DELETE(self,url, data = ""):

        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'DELETE'

        return self.read( req )

    def PATCH(self, url, data = ""):

        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'PATCH'

        return self.read(req)

    def getId(self):

        global lastRequestResult
        return json.loads( lastRequestResult )[ '_id' ]

    def getStatusCode( self ):

        global lastResponse
        return lastResponse.getcode()

    def getResponseTime( self ):

        global lastResponseTime
        return lastResponseTime

    def getAttribute( self, AttrName ):

        global lastRequestResult

        val = json.loads( lastRequestResult )
        try:          
            for k in AttrName.split( '.' ):
                if isinstance(val, list) and k.isdigit():
                    k = int(k)
                elif isinstance(val, dict) and k.isdigit():
                    k = val.keys()[int(k)]
                val = val[ k ]
        except BaseException, e:
            print 'Exception: ', e
            val = ''
        return val

    def getRawRequestResult( self ):

        global lastRequestResult
        return lastRequestResult

    def getLastError(self):

        global lastRequestError
        return lastRequestError

    def getObjectStringFields( self, schema_url, index_name ):

        schema = self.get_json(schema_url)

        fields = []

        for key, value in schema[ index_name ][ 'mappings' ][ 'objects' ][ 'properties' ].iteritems():

            if 'fields' in value and '_raw' in value[ 'fields' ]:
                fields.append(key)

        return fields


class HttpResultAsTable(RestTools, Execute):

    def __init__(self, url, args = None):

        self.result = self.get_json(url, args)
        if(type(self.result) == dict and self.result.has_key("hits")):
            self.result = self.result["hits"]
    
    def get_dataset(self):
        
        values = []
        
        if not type(self.result) == list:
          self.result = [ self.result ]

        for row in self.result:

            item = {}
            for key in self.header:

                if row.has_key("_source") and row["_source"].has_key(key):

                    item[key] = row["_source"][key]
                else:

                    val = ''
                    if(row.has_key(key)):
                        val = row[key]
                    else:
                        try:
                            val = row[ '_source' ] if row.has_key('_source') else row
                            for k in key.split( '.' ):
                                if isinstance(val, list) and k.isdigit():
                                    k = int(k)
                                elif isinstance(val, dict) and k.isdigit():
                                    k = val.keys()[int(k)]
                                val = val[ k ]
                        except BaseException, e:
                            print 'Exception: ', e
                            val = ''
                                                           
                    item[key] = val

            values.append(item)
            
        return values, self.header
        
    def table(self, table):

        self.header = table[0]

        for h in self.header:

            if h.rfind( '?' ) + 1 == len( h ):

                _h = h.rstrip( '?' )
                setattr( self, _h, lambda x: x )
            else:
                setattr( self, "set%s" % unicode.replace( h, h[ 0 ], h[ 0 ].upper(), 1 ),  lambda x: x )

class LastResultAsTable(HttpResultAsTable):

    def __init__(self):

        global lastRequestResult
        o = json.loads(lastRequestResult)
        if(type(o) == dict and o.has_key("hits")):
            self.result = o['hits']['hits']
        elif(type(o) == dict and o.has_key("docs")):
            self.result = o['docs']
        print 'OUTPUT: ', self.result

class LastRawResultAsTable( HttpResultAsTable ):

    def __init__( self ):

        global lastRequestResult
        self.result = json.loads( lastRequestResult )
        print 'OUTPUT: ', self.result

class ResponseAsTable(HttpResultAsTable):

    def __init__(self, url, args = None):
        body = self.get_json(url, args)
        if(type(body) == dict and body.has_key("hits")):
            body = body["hits"]

        global lastResponse
        self.result = { 'status_code': lastResponse.getcode(), 'headers': lastResponse.info().dict, 'body': body }

class LastResponseAsTable(HttpResultAsTable):

    def __init__( self ):

        body = None

        try:

            global lastRequestResult
            body = json.loads( lastRequestResult )
            if(type(body) == dict and body.has_key("hits")):
                body = body["hits"]

        except BaseException, e:

            body = lastRequestResult
            print 'Exception: ', e

        global lastResponse
        self.result = { 'status_code': lastResponse.getcode(), 'headers': lastResponse.info().dict, 'body': body }

class BodyFromTable(RestTools):

    def __init__(self, method, url, count = 1, query = None, args = None):

        self.method = method
        self.url = url
        self.ids = []
        self.count  = count
        self.query = query
        self.args = args

    def check_dict(self, val):

        val = self.parse_json(val)

        if isinstance(val, basestring) and val.startswith("["):
            return val[1:len(val)-1].split(",")
    
        return val
        
    @convert_arg(to_type=dict)
    def convert_from_hashtable(self, data):

        return data
        
    def check_hashtable(self,val):

        if isinstance(val, basestring) and val.find("hash_table") != -1:
            return self.convert_from_hashtable(re.sub('\t|\n|\r','',val))
        else:
            return val        

    def parse_json(self, val):

        try:
            return json.loads( val )
        except BaseException, e:
            return val

    def isUndefined(self, val):

        return val == "undefined"

    def table(self, rows):

        if type(rows) != tuple :
            self.processRow({}, "")
        else:
            header = rows[0]
            for h in header:
                if h == "_id?":
                    setattr(self, "_id", lambda self=self: self.ids.pop(0))
                else:
                    setattr(self, "set%s" % unicode.replace(h,h[0],h[0].upper(),1),  lambda x:x)

            link_ids = []
            if self.query:
                link_ids = self.get_json(self.query, self.args)

            for item in range(int(self.count)):

                for row in rows[1:]:
                    data = {}
                    id = ""
                    for idx in range(len(header)):
                        coll_name = header[idx]

                        if coll_name == '_id':
                            id = row[idx]
                        elif re.match('.*\?$', coll_name):
                            pass
                        else:
                            if not self.isUndefined(row[idx]):
                                data[header[idx]] = self.check_hashtable(self.check_dict(row[idx]))

                    self.processRow(data, id)

        self.makeRequestWithBody()

    def makeUrl(self, data, id):

        if not id:
            return self.url
        return self.url + '/' + id

    def processRow(self, data, id):

        func = getattr(self, self.method)
        url = self.makeUrl(data, id)
        ret = func(url, json.dumps(data))
        if self.method == "POST" and len(ret) > 0:
            try:
                res = json.loads(ret)
                if res.has_key("_id"):
                    self.ids.append(res["_id"])
            except BaseException, e:
                print "Get json from response \"%s\" error: %s" % ( ret, e)

    def makeRequestWithBody(self):

        pass

class Post(BodyFromTable):

    def __init__(self, url, count=1, query=None, args = None):

        BodyFromTable.__init__(self,"POST", url, count, query, args)

class Put(BodyFromTable):

    def __init__(self, url, count=1, query=None, args = None):

        BodyFromTable.__init__(self,"PUT", url, count, query, args)

class Patch(BodyFromTable):

    def __init__(self,url):

        BodyFromTable.__init__(self,"PATCH", url)      

class Delete(BodyFromTable):

    def __init__(self,url):

        BodyFromTable.__init__(self,"DELETE", url)              

class Bulk(BodyFromTable):

    def __init__(self, url, method):

        self.body = []
        self.method = method
        BodyFromTable.__init__(self, method, url)

    def processRow(self, data, id):

        data.update({'_id': id})
        self.body += [data]

    def makeRequestWithBody(self):

        body = '\n'.join( map( lambda x: json.dumps( x ), self.body ) )
        print getattr(self, self.method)(self.url, body)

class BulkPost(Bulk):

    def __init__(self, url):

        Bulk.__init__(self, url, 'POST')

class BulkPatch(Bulk):

    def __init__(self, url):

        Bulk.__init__(self, url, 'PATCH')

class BulkUpload(RestTools, MMFile):

    _timeout = 60  # default timeout for testing bulk operations 1 min.

    def open(self, req):

        print "------------------------------------------------"
        print "Method: %s" % req.get_method()
        print "Request url: %s" % req.get_full_url()
        print "Request headers: %s" % req.headers
        print "Request timeout: %f" % float(self._timeout)

        global lastResponseTime
        lastResponseTime = 0

        try:

            global lastResponse
            lastResponse = res = urllib2.urlopen(req.get_full_url(), req.get_data(), int(self._timeout))

        except BaseException, e:

            global lastRequestError
            global lastResponse
            lastResponse = lastRequestError = res = e
            print "Request error: %s" % e

        return res

    # Upload array of data, replacing '$_index' mask in each line with its index value
    def createBulkData(self, url, data, count, timeout=60):

        self._timeout = timeout
        self._createBody(data, count)
        response = self.read(self.getRequest(url, self.mmgetBody(), self.http_headers))
        self.mmclose()

        return response

    def _createBody(self, data, count):

        self.mmcreateFile()
        for i in range(int(count)):

            self.mmwrite(Template(data).safe_substitute(_index=i) + "\n")
            if i % 1000 == 1000:
                self.mmflush()

        self.mmflush()
        self.mmseek(0)

class BulkTable(BodyFromTable, MMFile):

    flush_every = 1000
    number = 1

    def __init__(self, method, url, number):

        self.number = number
        self.mmcreateFile()
        BodyFromTable.__init__(self, method, url)

    def processRow(self, data, id):

        for i in range(int(self.number)):

            data.update( {'_id':  str(id)} )
            self.mmwrite(Template(json.dumps(data)).safe_substitute(_index=i) + "\n")

            if i % self.flush_every == self.flush_every:
                self.mmflush()

        self.mmflush()

    def makeRequestWithBody(self):

        self.mmseek(0)

        req = self.getRequest(self.url, self.mmgetBody(), self.http_headers)
        req.get_method = lambda: self.method
        response = self.read(req)

        self.mmclose()
        return response
