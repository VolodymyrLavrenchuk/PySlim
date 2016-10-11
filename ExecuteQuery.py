#from logger import log
from waferslim.converters import Converter, register_converter, converter_for

class Obj(object):
	def __init__(self):
		self.x = {}
		
	def as_dict(self):
		return self.x					

class ObjConverter(Converter):
	def to_string(self, obj):
		dict_items = obj.as_dict().items
		converter = converter_for(list)
		return converter.to_string([[key, value] for key, value in dict_items()])
		
register_converter(Obj, ObjConverter())

class Execute(object):
	def query(self):
		dataset, keys = self.get_dataset()
		#log.Info(dataset)
		#log.Info(keys)
		return [self.get_obj(row, keys) for row in dataset]
		
	def get_dataset(self):		
		return [{}], []
		
	def exec_blank_field(self, field_v):
		if not field_v or field_v == "":
			return "BLANK"
		return field_v
		
	def get_obj(self, row, keys):
		o=Obj()
		for key in keys:
			data = row.get(key, '')
			if not isinstance(data, unicode ):
				data = self.converting(data)
			else:
				data = self.ret(data)
			o.x[str(key)] = data
		return o

	def ret(self, data):
		return data
		
	def converting(self, data):
		return str(data)
