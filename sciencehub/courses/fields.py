from django.db import models
from django.core.exceptions import ObjectDoesNotExist

class OrderField(models.PositiveIntegerField):
	''' Custom OrderField, inherits from the PositiveIntergerField field. Our OrderField takes an option for_fields parameter that allows
	us to indicate the fields that the order has to be calculated with respect to. Our field overrides the pre_save() method of the 
	PositiveIntegerField field, which is executed before saving the field into the database.
	'''
	def __init__(self, for_fields=None, *args, **kwargs):
		self.for_fields = for_fields
		super(OrderField, self).__init__(*args,**kwargs)

	def pre_save(self, model_instance, add):
		if getattr(model_instance, self.attname) is None:
			# no value currently
			try:
				qs = self.model.objects.all()
				if self.for_fields:
					# filter by objects with same field values
					# for the fields in "for_fields"
					query = {field: getattr(model_instance, field) for field in self.for_fields}
					qs = qs.filter(**query)
				#get the order of last item
				last_item = qs.latest(self.attname)
				value = last_item.order + 1
			except ObjectDoesNotExist:
				value = 0
			setattr(model_instance, self.attname, value)
			return value
		else:
			return super(OrderField, self).pre_save(model_instance, add)
				

					
