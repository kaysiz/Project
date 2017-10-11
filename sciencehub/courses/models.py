from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .fields import OrderField


class Subject(models.Model):
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=200, unique=True)

	class Meta:
		ordering = ('title',)

	def __str__(self):
		return self.title


class Course(models.Model):
	# owner is the course creator | 
	owner = models.ForeignKey(User, related_name='courses_created')
	# subject that course belongs. Fk that links to Subject model
	subject = models.ForeignKey(Subject, related_name='courses')
	# course title
	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=200, unique=True)
	# description of course
	overview = models.TextField()
	# date and time of creation
	created = models.DateTimeField(auto_now_add=True)
	students = models.ManyToManyField(User, related_name='courses_joined', blank=True)

	class Meta:
		ordering = ('-created',)

	def __str__(self):
		return self.title


class Module(models.Model):
	course = models.ForeignKey(Course, related_name='modules')
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	order = OrderField(blank=True, for_fields=['course'])

	class Meta:
		ordering = ['order']


	def __str__(self):
		return '{}. {}'.format(self.order,self.title)


class Content(models.Model):
	module = models.ForeignKey(Module, related_name='contents')
	# fk to the ContenType model, limited choices to limit the content types that can be used for relationship
	content_type = models.ForeignKey(ContentType,limit_choices_to={'model__in':('text','video','image','file')})
	# store primary key of related object
	object_id = models.PositiveIntegerField()
	# a GenericForeignKey field to the related object two preceding fields
	item = GenericForeignKey('content_type', 'object_id')
	order = OrderField(blank=True, for_fields=['module'])

	class Meta:
		ordering = ['order']


class ItemBase(models.Model):
	'''render_to_string for rendering a template and returning the rendered
	content as a string. Each element of content is rendered using a template
	named after content. This helps render diverse content'''
	owner = models.ForeignKey(User, related_name='%(class)s_related')
	title = models.CharField(max_length=250)
	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now_add=True)

	class Meta:
		abstract = True

	def __str__(self):
		return self.title

	def render(self):
		return render_to_string('courses/content/{}.html'.format(self._meta.model_name), {'item': self})



class Text(ItemBase):
	# Text Content
	content = models.TextField()


class File(ItemBase):
	# Files, pdfs,etc
	file = models.FileField(upload_to='files')


class Image(ItemBase):
	# Videos
	file = models.FileField(upload_to='images')


class Video(ItemBase):
	url = models.URLField()




		








		

