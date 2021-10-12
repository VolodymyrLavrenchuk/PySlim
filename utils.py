import logging
from .ExecuteQuery import Execute


_LOGGER_NAME = "PySlim"


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def _preprocess_expression(expression):
        return expression.replace("<pre>", "").replace("</pre>", "")

    def pyeval(self, expression):
        expression = self._preprocess_expression(expression)
        logging.getLogger(_LOGGER_NAME).info('Executing python expression:' + expression)
        return eval(expression)


class PyObjectAsTable(Execute):
    def __init__(self, pystr):
        self.result = eval(pystr)
        self.header = None
        print(self.result)

    def table(self, table):
        self.header = table[0]
        logging.getLogger(_LOGGER_NAME).info("Header passed: " + str(self.header))
        for h in self.header:
            if h.rfind('?') + 1 == len(h):
                _h = h.rstrip('?')
                setattr(self, _h, lambda x: x)
            else:
                setattr(self, "set%s" % str.replace(h, h[0], h[0].upper(), 1), lambda x: x)

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
                                    k = list(val.keys())[int(k)]
                                logging.getLogger(_LOGGER_NAME).info(val)
                                logging.getLogger(_LOGGER_NAME).info(k)
                                val = val[k]

                        except BaseException as e:
                            logging.getLogger(_LOGGER_NAME).info('HttpResultAsTable Exception: ', e)
                            val = ''

                item[key] = val
            values.append(item)
        logging.getLogger(_LOGGER_NAME).info("Returning: " + str(values))
        return values, self.header
