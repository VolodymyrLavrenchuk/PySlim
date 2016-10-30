from waferslim.converters import convert_arg, convert_result, StrConverter

import json
import re
import time
import urllib
import urllib.request
from socket import error as socket_error

from .ExecuteQuery import Execute
from .date_utils import DateUtils

global lastRequestError
global lastResponse

lastRequestResult = None
lastRequestError = None
lastResponse = None
lastResponseTime = None

g_headers = dict()
g_array_field = "hits"

class HttpCall:
    def open(self, req):

        try:

            print("------------------------------------------------")
            print("Method: %s" % req.get_method())
            print("Request url: %s" % req.get_full_url())
            print("Request headers: %s" % req.headers)
            if req.data is not None:
                print("Request body: %s" % req.data)
            global lastResponse
            lastResponse = res = urllib.request.urlopen(req)
            print("Response statusCode: %s" % res.getcode())
            print("Response headers: %s" % res.info())

        except urllib.error.HTTPError as e:

            lastResponse = res = e

            print("Response statusCode: %s" % res.getcode())
            print("Response headers: %s" % res.info())

        except BaseException as e:
            lastResponse = lastRequestError = res = e
            print("Response error: %s" % e)
            raise Exception("Response error %s" % e)

        return res

    def request(self, url, args=None, headers={}):
        return urllib.request.Request(url, args, headers)

    def read(self, req):

        start = time.time()
        resp = self.open(req)

        global lastResponseTime
        lastResponseTime = time.time() - start
        print("Response time: %f sec." % lastResponseTime)

        ret = None

        if type(resp) != urllib.error.URLError and type(resp) != socket_error and type(resp) != TypeError and type(
                resp) != AttributeError:
            ret = resp.read()
            print("Response body: %s" % ret)
            global lastRequestResult

            lastRequestResult = ret.decode('utf-8')

        return ret

    def GET(self, url, headers={}, args=None):

        headers.update(g_headers)

        if args:
            url = url + urllib.parse.quote(args, '=&')
        req = self.request(url, None, headers)

        return self.read(req)

    def ArrayField(self, value):

        global g_array_field
        g_array_field = value

    def Header(self, h, v):

        global g_headers
        g_headers[h] = v

        print("Headers:")
        print(g_headers)

    def setHostUrl(self, url):

        global host_url
        host_url = url

    def get_full_url(self, url):

        global host_url
        
        if url.startswith("http://") or url.startswith("https://"):
            return url
        else: 
            return host_url + url

class RestTools(HttpCall):
    http_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    def format_raw_get(self, url, args=None):
        return json.dumps(self.get_json(url),sort_keys=True)
    
    def getRequest(self, url, data=None, headers={}):
        headers.update(g_headers)
        return self.request(self.get_full_url(url), data.encode('utf-8'), headers)

    def get_str(self, url, args=None):
        return self.GET(self.get_full_url(url), {'Accept': 'application/json'}, args).decode('utf-8')

    def get_hex_str(self, url, args=None):
        resp = self.get_str(url, args)
        import binascii
        return binascii.hexlify(resp)

    def searchRegexpInHtml(self, pattern, url):

        import re
        res = self.GET(url)
        data = re.search(pattern, res, re.M)
        return data.group(1)

    def get_json(self, url, args=None):
        try:
            res = []
            resp = self.get_str(url, args)
            if resp:

                res = json.loads(resp)
                if type(res) == dict:
                    if g_array_field in res:
                        res = res[g_array_field]
        except ValueError:

            print("Failed to parse json")

        print("get_json result: %s" % res)
        return res
        
    

    def get_attr_by_type(self, data, attr):

        res = data
        index = 0
        for a in attr.split('.'):

            match = re.match('^(\w*)\[([0-9])\]', a)
            if match:
                a = match.group(1)
                index = int(match.group(2))

            if len(res) > 0:
                types = {
                    dict: lambda: res[a] if a in res else res,
                    list: lambda: res[index][a]
                }
                res = types[type(res)]()

        return res

    def getAttributeFromResponse(self, attr, url, args=None):
        return self.get_attr_by_type(self.get_json(url, args), attr)

    def getAttributeFromResponseAsString(self, attr, url, args=None):

        return str(self.getAttributeFromResponse(attr, url, args))

    def currentTimeDiff(self, attr, url, args=None):
        return DateUtils().js_time_diff(self.getAttributeFromResponse(attr, url, args))

    def wait(self, wait_sec, retries, func, **kwargs):

        for r in range(int(retries)):
            if func(kwargs):
                return True
            self.sleep(wait_sec)
        return False

    def quoteUrl(self, url):
        return urllib.parse.quote(url)


    def waitSecondTimesUrlResponseAttributeHasValue(self, wait_sec, retries, url, attr, value):
        def func(args):

            resp = self.getAttributeFromResponse(args["attr"], args["url"])

            resp_type = type(resp)

            try:
                return resp == resp_type(value)
            except ValueError:
                return False

        result = self.wait(wait_sec, retries, func, attr=attr, url=url)
        if result is False:
            raise Exception('Actual value: %s' % self.getAttributeFromResponse(attr, url))

        return result

    def waitSecondTimesUrlResponseAttributeNotZero(self, wait_sec, retries, url, attr):
        def func(args):

            resp = self.getAttributeFromResponse(args["attr"], args["url"])

            try:
                return resp > 0
            except ValueError:
                return False

        return self.wait(wait_sec, retries, func, attr=attr, url=url)

    def waitSecondTimesUrlHasValidResponse(self, wait_sec, retries, url):

        def func(args):
            return self.get_json(args["url"])

        return self.wait(wait_sec, retries, func, url=url)

    def waitSecondTimesUrlArgsResponseValue(self, wait_sec, retries, url, attrs, value):

        def func(args):
            return self.get_str(url) == value

        return self.wait(wait_sec, retries, func)

    def sleep(self, sec):

        time.sleep(float(sec))

    def makeLine(self, line):

        return line.replace('\n', '\\n')

    def POST(self, url, data="", headers=""):

        data = data.replace('\n', '\r\n')
        req = self.getRequest(url, data, json.loads(headers) if headers else self.http_headers)

        return self.read(req)

    def PUT(self, url, data=""):
        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'PUT'

        return self.read(req)

    def DELETE(self, url, data=""):
        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'DELETE'

        return self.read(req)

    def PATCH(self, url, data=""):
        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'PATCH'

        return self.read(req)

    def getId(self):
        global lastRequestResult
        return json.loads(lastRequestResult)['_id']

    def getStatusCode(self):
        global lastResponse
        return lastResponse.getcode()

    def getResponseTime(self):

        global lastResponseTime
        return lastResponseTime

    def getAttribute(self, AttrName):

        global lastRequestResult
        return json.loads(lastRequestResult)[AttrName]
        
    def findAttributeByName(self, keyName, keyValue, attrName):
    
        global lastRequestResult
        res = json.loads(lastRequestResult)
        
        if type(res) == dict:
            if g_array_field in res:
                res = res[g_array_field]
                
        return [r[attrName] for r in res if r[keyName] == keyValue][0]
    
    

    def getRawRequestResult(self):

        global lastRequestResult
        return lastRequestResult

    def getLastError(self):

        global lastRequestError
        return lastRequestError

    def getObjectStringFields(self, schema_url, index_name):

        schema = self.get_json(schema_url)

        fields = []

        for key, value in schema[index_name]['mappings']['objects']['properties'].iteritems():

            if 'fields' in value and '_raw' in value['fields']:
                fields.append(key)

        return fields


class HttpResultAsTable(RestTools, Execute):
    def __init__(self, url, args=None):
        self.result = self.get_json(url, args)
        if type(self.result) == dict:
            if g_array_field in self.result:
                self.result = self.result[g_array_field]

    def get_dataset(self):

        values = []

        if not type(self.result) == list:
            self.result = [self.result]

        for row in self.result:

            item = {}
            for key in self.header:

                if "_source" in row and key in row["_source"]:
                    item[key] = row["_source"][key]
                else:

                    val = ''
                    if key in row:
                        val = row[key]
                    else:
                        try:
                            val = row['_source'] if '_source' in row else row
                            for k in key.split('.'):
                                if isinstance(val, list) and k.isdigit():
                                    k = int(k)
                                elif isinstance(val, dict) and k.isdigit():
                                    k = val.keys()[int(k)]

                                print(val)    
                                print(k)    

                                val = val[k]

                        except BaseException as e:
                            print('HttpResultAsTable Exception: ', e)
                            val = ''

                    item[key] = val

            values.append(item)

        return values, self.header

    def table(self, table):

        self.header = table[0]

        for h in self.header:

            if h.rfind('?') + 1 == len(h):

                _h = h.rstrip('?')
                setattr(self, _h, lambda x: x)
            else:
                setattr(self, "set%s" % str.replace(h, h[0], h[0].upper(), 1), lambda x: x)


class LastResultAsTable(HttpResultAsTable):
    def __init__(self):
        global lastRequestResult

        o = json.loads(lastRequestResult)
        self.result = o['hits']['hits']
        print('OUTPUT: ', self.result)


class LastRawResultAsTable(HttpResultAsTable):
    def __init__(self):
        global lastRequestResult
        self.result = json.loads(lastRequestResult)
        print('OUTPUT: ', self.result)


class ResponseAsTable(HttpResultAsTable):
    def __init__(self, url, args=None):
        body = self.get_json(url, args)
        if type(body) == dict and g_array_field in body:
            body = body[g_array_field]

        global lastResponse
        print(lastResponse.info())

        self.result = {'status_code': lastResponse.getcode(), 'headers': lastResponse.info().dict, 'body': body}


class LastResponseAsTable(HttpResultAsTable):
    def __init__(self):
        body = None

        try:

            global lastRequestResult
            print('lastRequestResult: %s' % lastRequestResult)
            body = json.loads(lastRequestResult)
            if type(body) == dict and g_array_field in body:
                body = body[g_array_field]

        except BaseException as e:

            body = lastRequestResult
            print('LastResponseAsTable Exception: ', e)

        global lastResponse

        self.result = {'status_code': lastResponse.getcode(), 'headers': lastResponse.info(), 'body': body}


class BodyFromTable(RestTools):
    def __init__(self, method, url, count=1, query=None, args=None):
        self.method = method
        self.url = url
        self.ids = []
        self.count = count
        self.query = query
        self.args = args

    def check_bool(self, val):
        
        if isinstance(val, str) and val.lower() == "false":
            return False
            
        if isinstance(val, str) and val.lower() == "true":
            return True

        return val
        
    def check_dict(self, val):

        val = self.parse_json(val)
        print('Parse:' + str(val))
        print(val.__class__)
        
        if isinstance(val, str) and val.startswith("["):
            return val[1:len(val) - 1].split(",")
        
        return val

    @convert_arg(to_type=dict)
    def convert_from_hashtable(self, data):
        return data

    def check_hashtable(self, val):
        if isinstance(val, str) and val.find("hash_table") != -1:
            return self.convert_from_hashtable(re.sub('\t|\n|\r', '', val))
        else:
            return val

    def parse_json(self, val):
        try:
            return json.loads(val)
        except BaseException as e:
            return val

    def isUndefined(self, val):

        return val == "undefined"

    def table(self, rows):

        if type(rows) != tuple:
            self.processRow({}, "")
        else:
            header = rows[0]
            for h in header:
                if h == "_id?":
                    setattr(self, "_id", lambda self=self: self.ids.pop(0))
                else:
                    setattr(self, "set%s" % str.replace(h, h[0], h[0].upper(), 1), lambda x: x)

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
                                val = row[idx]                                                            
                                data[header[idx]] = self.check_hashtable(self.check_dict(self.check_bool(val)))

                    self.processRow(data, id)

        self.makeRequestWithBody()
    
    def makeUrl(self, data, id):
        if not id:
            return self.url
        return self.url + '/' + id

    def processRow(self, data, id):

        func = getattr(self, self.method)
        url = self.makeUrl(data, id)
        
        ct = g_headers.get("Content-Type")

        if ct == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(data)
        else:
            data = json.dumps(data)

        ret = func(url, data)

        if self.method == "POST" and len(ret) > 0:
            try:
                res = json.loads(ret.decode('utf-8'))

                if "_id" in res:
                    self.ids.append(res["_id"])
            except BaseException as e:
                print("Get json from response \"%s\" error: %s" % (ret, e))

    def makeRequestWithBody(self):
        pass

        
class Post(BodyFromTable):
    def __init__(self, url, count=1, query=None, args=None):
        BodyFromTable.__init__(self, "POST", url, count, query, args)


class Put(BodyFromTable):
    def __init__(self, url, count=1, query=None, args=None):
        BodyFromTable.__init__(self, "PUT", url, count, query, args)


class Patch(BodyFromTable):
    def __init__(self, url):
        BodyFromTable.__init__(self, "PATCH", url)


class Delete(BodyFromTable):
    def __init__(self, url):
        BodyFromTable.__init__(self, "DELETE", url)


class Bulk(BodyFromTable):
    def __init__(self, url, method):
        self.body = []
        self.method = method
        BodyFromTable.__init__(self, method, url)

    def processRow(self, data, id):
        data.update({'_id': id})
        self.body += [data]

    def makeRequestWithBody(self):
        body = '\n'.join(map(lambda x: json.dumps(x), self.body))
        print(getattr(self, self.method)(self.url, body))


class BulkPost(Bulk):
    def __init__(self, url):
        Bulk.__init__(self, url, 'POST')


class BulkPatch(Bulk):
    def __init__(self, url):
        Bulk.__init__(self, url, 'PATCH')


