from waferslim.converters import convert_arg, convert_result, StrConverter

import json
import sys
import logging
import ast
import re
import time
import traceback
import urllib
import urllib.request
from abc import ABC, abstractmethod

from socket import error as socket_error

from .ExecuteQuery import Execute
from .date_utils import DateUtils
from .retrying import RetryError, retry

global lastRequestError
global lastResponse
global host_url
global max_attempt_number
max_attempt_number = 5

lastRequestResult = None
lastRequestError = None
lastResponse = None
lastResponseTime = None

g_headers = dict()
g_array_field = "hits"

_LOGGER_NAME = 'PySlim'
logging.getLogger(_LOGGER_NAME).setLevel(logging.DEBUG)

def make_request(func, req):
    logging.getLogger(_LOGGER_NAME).info('begin')
    print("Making request with attempts %s" % max_attempt_number)

    def retry_on_exception(exc):
        print("Exception: %s" % exc)
        if isinstance(exc, urllib.error.HTTPError):
            print("reason: %s" % exc.reason)
            will_retry = exc.status >= 500
            print("Will retry: %s" % will_retry)
            return will_retry

        return False

    @retry(stop_max_attempt_number=max_attempt_number,
           wait_exponential_max=10000,
           wait_exponential_multiplier=700,
           wait_jitter_max=3000,
           retry_on_exception=retry_on_exception)
    def do_with_retry():
        return func(req)

    try:
        return do_with_retry()
    except RetryError as e:
        return e.last_attempt.value

class HttpCallBase(ABC):
    def set_retries_number(self, number):
        global max_attempt_number
        max_attempt_number = int(number)

    def print_response(self, res):
        print("Response statusCode: %s" % res.getcode())
        print("Response headers: %s" % res.info())

    def open(self, req):
        logging.getLogger(_LOGGER_NAME).info('begin')

        try:
            print("------------------------------------------------")
            print("Method: %s" % req.get_method())
            print("Request url: %s" % req.get_full_url())
            print("Request headers: %s" % req.headers)
            if req.data is not None:
                print("Request body: %s" % req.data)
            print(req.data)
            global lastResponse
            lastResponse = res = make_request(self.make_call, req)  # urllib.request.urlopen(req)
            print("Success.")
            self.print_response(res)

        except urllib.error.HTTPError as e:

            lastResponse = lastRequestError = res = e

            print("HTTPError")
            self.print_response(res)

        except BaseException as e:
            lastResponse = lastRequestError = res = e
            print("BaseException")
            print("Response error: %s" % e)
            raise Exception("Response error %s" % e)

        logging.getLogger(_LOGGER_NAME).info('end')
        return res

    @abstractmethod
    def make_call(self, req):
        pass

    def request(self, url, args=None, headers={}):
        return urllib.request.Request(url, args, headers)

    def read(self, req):
        logging.getLogger(_LOGGER_NAME).info('begin')
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
            try:
                lastRequestResult = ret.decode('utf-8')
            except BaseException as e:
                print("Can`t decode utf-8. Return as is")
                lastRequestResult = ret

        logging.getLogger(_LOGGER_NAME).info('end')
        return ret

    def ArrayField(self, value):

        global g_array_field
        g_array_field = value

    def Header(self, h, v):

        global g_headers
        g_headers[h] = v

        print("Headers:")
        print(g_headers)

class HttpCall(HttpCallBase):
    def make_call(self, req):
        return urllib.request.urlopen(req)

class RestTools:

    http_headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}

    httpClient = HttpCall()

    def setHostUrl(self, url):

        global host_url
        host_url = url

    def get_full_url(self, url):

        global host_url

        if url.startswith("http://") or url.startswith("https://"):
            return url
        else:
            return host_url + url

    def setHttpClient(self, obj):
        self.httpClient = obj()

    def format_raw_get(self, url, args=None):
        return json.dumps(self.get_json(url), sort_keys=True)

    def getRequest(self, url, data=None, headers={}):
        logging.getLogger(_LOGGER_NAME).info('begin')
        headers.update(g_headers)
        print('getRequest:' + data)
        if data != None and hasattr(data, 'encode'):
            data = data.encode('utf-8')
        #print('getRequest:' + data)
        logging.getLogger(_LOGGER_NAME).info('end')
        return self.httpClient.request(self.get_full_url(url), data, headers)

    def get_str(self, url, args=None):
        logging.getLogger(_LOGGER_NAME).info(url)
        return self.httpClient.GET(self.get_full_url(url), {'Accept': 'application/json'}, args).decode('utf-8')

    def get_hex_str(self, url, args=None):
        resp = self.httpClient.GET(self.get_full_url(url), {'Accept': 'application/json'}, args)
        import binascii
        return binascii.hexlify(resp).decode('utf-8')

    def searchRegexpInHtml(self, pattern, url):

        import re
        res = self.GET(url)
        data = re.search(pattern, res, re.M)
        return data.group(1)

    def get_json(self, url, args=None):
        res = []
        logging.getLogger(_LOGGER_NAME).info(url)

        try:
            resp = self.get_str(url, args)
            logging.getLogger(_LOGGER_NAME).info(resp)
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

    def unpack(self, res):

        if type(res) == dict:
            if g_array_field in res:
                res = res[g_array_field]

        return res

    def getAttributeFromLastResponse(self, attr):

        import json
        res = json.loads(lastRequestResult)

        res = self.unpack(res)
        return self.get_attr_by_type(res, attr)

    def getAttributeLengthFromLastResponse(self, attr):

        return len(self.getAttributeFromLastResponse(attr))

    def getAttributeFromResponse(self, attr, url, args=None):
        return self.get_attr_by_type(self.get_json(url, args), attr)

    def getAttributeFromResponseAsString(self, attr, url, args=None):

        return str(self.getAttributeFromResponse(attr, url, args))

    def currentTimeDiff(self, attr, url, args=None):
        return DateUtils().js_time_diff(self.getAttributeFromResponse(attr, url, args))

    def wait(self, wait_sec, retries, func, **kwargs):

        for r in range(int(retries)):
            try:
                if func(kwargs):
                    return True
            except Exception as e:
                print(e)
                traceback.print_exc()

            self.sleep(wait_sec)
        return False

    def quoteUrl(self, url):
        return urllib.parse.quote(url)

    def waitSecondTimesUrlResponseCondition(self, wait_sec, retries, url, condition):
        def func(args):
            resp = self.get_json(url)

            print("Got condition resp %s" % resp)
            if resp is None:
                return False
            try:
                result = eval(condition, globals(), locals())
            except:
                logging.exception("Failed condtiion")
                return False
            print("Got condition result %s" % result)
            return result

        result = self.wait(wait_sec, retries, func, url=url)
        return result

    def waitSecondTimesUrlResponseAttributeHasValue(self, wait_sec, retries, url, attr, value):
        def func(args):

            resp = self.getAttributeFromResponse(args["attr"], args["url"])

            if resp is None:
                return False

            resp_type = type(resp)

            try:
                return resp == resp_type(value)
            except ValueError:
                return False

        result = self.wait(wait_sec, retries, func, attr=attr, url=url)
        return result

    def waitSecondTimesUrlResponseAttributeNotZero(self, wait_sec, retries, url, attr):
        def func(args):

            resp = self.getAttributeFromResponse(args["attr"], args["url"])

            try:
                return resp > 0
            except ValueError:
                return False

        return self.wait(wait_sec, retries, func, attr=attr, url=url)

    def waitSecondTimesUrlResponseAttributeNotEmpty(self, wait_sec, retries, url, attr):
        def func(args):
            resp = self.getAttributeFromResponse(args["attr"], args["url"])

            if resp:
                return True
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

    def ArrayField(self, value):
        self.httpClient.ArrayField(value)

    def GraphqlQuery(self, url, data="", headers=""):
        logging.getLogger(_LOGGER_NAME).info('begin')

        print('data:' + data)
        if(isinstance(data , str)):
            data = data.replace('\n', '\r\n')
        logging.getLogger(_LOGGER_NAME).info(data)
        req = self.getRequest(url, data, json.loads(headers) if headers else self.http_headers)
        logging.getLogger(_LOGGER_NAME).info('end')
        return self.httpClient.read(req)

    def GraphqlMutation(self, url, data="", headers=""):
        logging.getLogger(_LOGGER_NAME).info('begin')

        print('data:' + data)
        if(isinstance(data , str)):
            data = data.replace('\n', '\r\n')
        logging.getLogger(_LOGGER_NAME).info(data)
        req = self.getRequest(url, data, json.loads(headers) if headers else self.http_headers)
        logging.getLogger(_LOGGER_NAME).info('end')
        return self.httpClient.read(req)

    def OPTIONS(self, url, data=""):
        req = self.getRequest(url, data, self.http_headers)
        req.get_method = lambda: 'OPTIONS'

        return self.httpClient.read(req)

    def getId(self):
        global lastRequestResult
        return json.loads(lastRequestResult)['_id']

    def getStatusCode(self):
        global lastResponse
        return lastResponse.getcode()

    def getLastResponseHeaders(self):
        global lastResponse
        return lastResponse.info()
        
    def getLastResponseHeader(self, name):
        global lastResponse
        return lastResponse.info()[name]

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

        val = [r[attrName] for r in res if r[keyName] == keyValue]

        return val and val[0] or None

    def getRawRequestResult(self):

        global lastRequestResult
        return lastRequestResult

    def getLastError(self):

        global lastRequestError
        return lastRequestError

    def getObjectStringFields(self, schema_url, index_name):

        schema = self.get_json(schema_url)

        fields = []

        for key, value in schema[index_name]['mappings']['objects']['properties'].items():

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
        logging.getLogger(_LOGGER_NAME).info('get_dataset' + str(self.result))

        values = []

        if not type(self.result) == list:
            logging.getLogger(_LOGGER_NAME).info('get_dataset: not list')
            self.result = [self.result]

        for row in self.result:
            logging.getLogger(_LOGGER_NAME).info('get_dataset row: ' + str(row))

            item = {}
            for key in self.header:
                logging.getLogger(_LOGGER_NAME).info('get_dataset key: ' + key)

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
                                    k = list(val.keys())[int(k)]

                                print(val)
                                print(k)

                                val = val[k]

                        except BaseException as e:
                            print('HttpResultAsTable Exception: ', e)
                            val = ''

                    item[key] = val

            values.append(item)

        logging.getLogger(_LOGGER_NAME).info('get_dataset self.header' + str(self.header))
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
        if type(o) == dict and "data" in o:
            o = o['data']
            if type(o) == dict and "listPatients" in o:
                o = o['listPatients']
                #if type(o) == dict and "items" in o:
                 #   o = o['items']
        self.result = o
        logging.getLogger(_LOGGER_NAME).info('LastResultAsTable_init:' + str(self.result))
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
        self.result = {'status_code': lastResponse.getcode(), 'headers': lastResponse.info(), 'body': body}


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
    def __init__(self, method, url, count=1, query=None, args=None, body=None, prefix=None):
        logging.getLogger(_LOGGER_NAME).info('begin')
        self.method = method
        self.url = url
        self.count = count
        self.query = query
        self.args = args
        self.body = body
        self.prefix = prefix
        self.get_headers = {}
        self.set_headers = {}
        self.rows = []
        self.row = {}

    def check_bool(self, val):

        if isinstance(val, str) and val.lower() == "false":
            return False

        if isinstance(val, str) and val.lower() == "true":
            return True

        return val

    def check_dict(self, val):

        val = self.parse_json(val)

        if isinstance(val, str):
            if val.startswith("["):
                return val[1:len(val) - 1].split(",")
            if val.startswith("{"):
                return ast.literal_eval(val)

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
        logging.getLogger(_LOGGER_NAME).info('begin')

        if type(rows) != tuple:
            data = {}
            data['query'] = self.prefix + self.body
            self.processRow(data)
        else:
            header = rows[0]
            for h in header:
                h = h.strip()
                if h.startswith('#'):
                    continue
                if h.endswith('?'):
                    self._add_getattr(h)
                    continue
                self._add_setattr(h)

            for item in range(int(self.count)):

                for row in rows[1:]:
                    data = {}
                    sep = ''
                    vars = ''
                    for idx in range(len(header)):
                        coll_name = header[idx]
                        logging.getLogger(_LOGGER_NAME).info(coll_name)

                        if coll_name.startswith('#'):
                            logging.getLogger(_LOGGER_NAME).info('skip:'+coll_name)
                        elif re.match('.*\?$', coll_name):
                            logging.getLogger(_LOGGER_NAME).info('skip:'+coll_name)
                            pass
                        elif not self.isUndefined(row[idx]):
                            val = row[idx]
                            logging.getLogger(_LOGGER_NAME).info(json.dumps(val))
                            quot = ''
                            if coll_name.endswith('String'):
                                quot='"'
                            vars = vars + sep + coll_name + ' = ' + quot + str(self.check_hashtable(self.check_dict(self.check_bool(val)))) + quot
                            sep = ', '
                    if vars != '':
                        vars = '(' + vars + ')'
                    data['query'] = self.prefix + vars + self.body
                    self.rows.append(data)
                    #self.processRow(data)

        self.makeRequestWithBody()
        logging.getLogger(_LOGGER_NAME).info('end')

    def _prepare_data(self):
        sep = ''
        vars = ''
        for row in self.row.keys():
            coll_name = self.set_headers[row]
            logging.getLogger(_LOGGER_NAME).info(f'_prepare_data: coll_name: {coll_name}')
            val = self.row[row]
            logging.getLogger(_LOGGER_NAME).info(json.dumps(f'_prepare_data: val: {val}'))
            quot = ''
            if coll_name.endswith('String') or coll_name.endswith('[String]') or coll_name.endswith('[String!]'):
                quot='"'
            vars = vars + sep + coll_name + ' = ' + quot + str(self.check_hashtable(self.check_dict(self.check_bool(val)))) + quot
            sep = ', '
        if vars != '':
            vars = '(' + vars + ')'
        logging.getLogger(_LOGGER_NAME).info(json.dumps(f'_prepare_data: vars: {vars}'))
        data = {}
        data['query'] = self.prefix + vars + self.body
        return data

    def _set_data(self, name, value):
        logging.getLogger(_LOGGER_NAME).info(f'_set_data({name}): {value}')
        self.row[name] = value

    def _getx(self, name):
        return self._getField(self.get_headers[name])

    def _add_getattr(self, header):
        print('header: ' + header)
        header = header[:-1]
        print('header: ' + header)
        sep = '.'
        if ' ' in header:
            sep = ' '
        items1 = header.split(sep)
        items = []
        for item in items1:
            fi = item.find('[',1,-2)
            if item.endswith(']') and fi != -1:
                items.append(item[0:fi])
                items.append(item[fi:])
            else:
                items.append(item)

        print('items: ' + str(items))
        attr = items[0]
        for i in items[1:]:
            attr += str.replace(i, i[0], i[0].upper(), 1)
            print('attr: ' + attr)
        for idx in range(len(items)):
            item = items[idx]
            if (item.startswith('[') and item.endswith(']')):
                items[idx] = item[1:-1]
        items.insert(0, 'data')
        print('items: ' + str(items))
        if attr in ['graphqlResult', 'httpResult']:
            print('skip: ' + attr)
            return
        self.get_headers[attr] = items
        setattr(self, attr, lambda self=self: self._getx(attr))

    def _add_setattr(self, header):
        h = header
        for i in [';', ':', '!', '*', ' ', '$', '[', ']'] : 
            h = h.replace(i, '')
        attr = "set%s" % str.replace(h, h[0], h[0].upper(), 1)
        logging.getLogger(_LOGGER_NAME).info('attr:' + attr)
        #setattr(self, attr, lambda x: x)
        setattr(self, attr, lambda value: self._set_data(attr, value))
        self.set_headers[attr] = header

    def _getField(self, parts):
        result = ''
        if self.graphqlResult() == '':
            global lastRequestResult
            o = json.loads(lastRequestResult)
            logging.getLogger(_LOGGER_NAME).info('o: ' + str(o))
            result = o
            for part in parts:
                logging.getLogger(_LOGGER_NAME).info('part:' + str(part) + ' type: ' + str(type(o)))
                if type(o) == dict and part in o:
                    if str.isdigit(part):
                        print('------------------ to digit' )
                        part = int(part)
                    o = o[part]
                    logging.getLogger(_LOGGER_NAME).info('o: ' + str(o))
                    result = o
                elif type(o) == list:
                    if str.isdigit(part) or (part[0] == '-' and str.isdigit(part[1:])):
                        print('------------------ to digit' )
                        part = int(part)
                    o = o[part]
                    logging.getLogger(_LOGGER_NAME).info('o: ' + str(o))
                    result = o
                else:
                    logging.getLogger(_LOGGER_NAME).info('o: ' + str(o))
        return str(result)

    def _processRow(self, data):
        logging.getLogger(_LOGGER_NAME).info('begin')
        logging.getLogger(_LOGGER_NAME).info(json.dumps(data))

        func = getattr(self, self.method)

        data = json.dumps(data)
        logging.getLogger(_LOGGER_NAME).info(data)

        ret = func(self.url, data)

        if len(ret) > 0:
            try:
                res = json.loads(ret.decode('utf-8'))
            except BaseException as e:
                print("Get json from response \"%s\" error: %s" % (ret, e))
        logging.getLogger(_LOGGER_NAME).info('end')

    def makeRequestWithBody(self):
        pass

    def httpResult(self):
        global lastResponse
        return lastResponse.getcode()

    def graphqlResult(self):
        result = ''
        global lastResponse
        if lastResponse.getcode() in [200,400]:
            global lastRequestResult
            o = json.loads(lastRequestResult)
            if type(o) == dict and "errors" in o:
                o = o['errors']
                logging.getLogger(_LOGGER_NAME).info(o)
                o = map(lambda err: err['message'], o)
                logging.getLogger(_LOGGER_NAME).info(o)
                result = o = ' '.join(o)
                logging.getLogger(_LOGGER_NAME).info(o)
        return result

    def execute(self):
        #data = self.rows[0]
        #del self.rows[0]
        data = self._prepare_data()
        self._processRow(data)

    def reset(self):
        self.row = {}

    def beginTable(self):
        pass

    def endTable(self):
        pass

class GraphqlQuery(BodyFromTable):
    def __init__(self, url, count=1, query=None, args=None, body=None, prefix=None):
        global host_url
        logging.getLogger(_LOGGER_NAME).info('GraphqlQuery(BodyFromTable)')
        logging.getLogger(_LOGGER_NAME).info(host_url)
        logging.getLogger(_LOGGER_NAME).info(json.dumps(url))
        logging.getLogger(_LOGGER_NAME).info(json.dumps(query))
        logging.getLogger(_LOGGER_NAME).info(json.dumps(args))
        logging.getLogger(_LOGGER_NAME).info(json.dumps(count))
        BodyFromTable.__init__(self, "GraphqlQuery", host_url, count, query, args, url, "query MyQuery")

class GraphqlMutation(BodyFromTable):
    def __init__(self, url, count=1, query=None, args=None, body=None, prefix=None):
        global host_url
        logging.getLogger(_LOGGER_NAME).info('GraphqlMutation(BodyFromTable)')
        logging.getLogger(_LOGGER_NAME).info(host_url)
        logging.getLogger(_LOGGER_NAME).info(json.dumps(url))
        logging.getLogger(_LOGGER_NAME).info(json.dumps(args))
        BodyFromTable.__init__(self, "GraphqlMutation", host_url, count, query, args, url, "mutation MyMutation")
