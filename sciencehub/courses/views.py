from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView , DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import permission_required
from django.views.generic.base import TemplateResponseMixin, View
from django.forms.models import modelform_factory
from django.apps import apps
from django.db.models import Count
from django.views.generic.detail import DetailView
from braces.views import CsrfExemptMixin, JsonRequestResponseMixin

from .models import Course, Module, Content, Subject
from students.forms import CourseEnrollForm
from .forms import ModuleFormSet


class CourseDetailView(DetailView):
	model = Course
	template_name = 'courses/course/detail.html'

	def get_context_data(self, **kwargs):
		'''We use the get_context_data() method to include the enrollment 
		form in the context for rendering the templates. We initialize the 
		hidden course field of the form with the current Course object, so 
		that it can be submitted directly.'''
		context = super(CourseDetailView, self).get_context_data(**kwargs)
		context['enroll_form'] = CourseEnrollForm(initial={'course': self.object})
		return context


class CourseListView(TemplateResponseMixin, View):
	'''Get all subjects and total number of courses for each of them
	Annotatae and Count methods for adding. Retrieve all courses and
	modules in each. If slug is supplied we get corresponding subject.
	Query limited to courses belonging to certain subject'''
	model = Course
	template_name = 'courses/course/homepage.html'

	def get(self, request, subject=None):
		subjects = Subject.objects.annotate(total_courses=Count('courses'))
		courses = Course.objects.annotate(total_modules=Count('modules'))
		if subject:
			subject = get_object_or_404(Subject, slug=subject)
			courses = courses.filter(subject=subject)
		return self.render_to_response({'subjects': subjects,'subject': subject,'courses': courses})

class OwnerMixin(object):
	''' Mixin will override this method to filter objects that belong 
	to current user i.e, request.user'''
	def get_queryset(self):
		qs = super(OwnerMixin, self).get_queryset()
		return qs.filter(owner=self.request.user)


class OwnerEditMixin(object):
	def form_valid(self, form):
		# Checking validity of form
		form.instance.owner = self.request.user
		return super(OwnerEditMixin, self).form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin):
	model = Course
	fields = ['subjects','title','slug','overview']
	success_url = reverse_lazy('manage_course_list')


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
	# Model fields to build model form
	fields = ['subject', 'title', 'slug', 'overview']
	# Used by Views to redirect after form validity has been confirmed 
	success_url = reverse_lazy('manage_course_list')
	template_name = 'courses/manage/course/form.html'


class ManageCourseListView(OwnerCourseMixin,ListView):
	#List courses Created by User
	template_name = 'courses/manage/course/list.html'


class CourseCreateView(PermissionRequiredMixin,OwnerCourseEditMixin, CreateView):
	permission_required = 'courses.add_course'


class CourseUpdateView(PermissionRequiredMixin,OwnerCourseEditMixin, UpdateView):
	template_name = 'courses/manage/course/form.html'
	permission_required = 'courses.change_course'


class CourseDeleteView(PermissionRequiredMixin,OwnerCourseMixin, DeleteView):
	template_name = 'courses/manage/course/delete.html'
	success_url = reverse_lazy('manage_course_list')
	permission_required = 'courses.delete_course'


class CourseModuleUpdateView(TemplateResponseMixin, View):
	'''TemplateResponseMixin Renders Templates and returns protocol reposnses
	HTTP'''
	template_name = 'courses/manage/module/formset.html'
	course = None

	def get_formset(self, data=None):
		# build the formset
		return ModuleFormSet(instance=self.course, data=data)

	def dispatch(self, request, pk):
		'''Delegates request to right methods. i.r GET to get() 
		and POST to post(). get_object_or_404 returns 404 error
		if page is not found'''
		self.course = get_object_or_404(Course, id=pk, owner=request.user)
		return super(CourseModuleUpdateView,self).dispatch(request, pk)

	def get(self, request, *args, **kwargs):
		'''Responds to GET requests. Builds formset and renders
		a response to template'''
		formset = self.get_formset()
		return self.render_to_response({'course': self.course, 'formset':formset})

	def post(self, request, *args, **kwargs):
		'''Executed for POST requests. Builds a formset object. 
		Checks validity of submitted data(is_valid) and saves it. Then
		redirects to (manage_course_list) url'''
		formset = self.get_formset(data=request.POST)
		if formset.is_valid():
			formset.save()
			return redirect('manage_course_list')
		return self.render_to_response({'course': self.course, 'formset': formset})	


class ContentCreateUpdateView(TemplateResponseMixin, View):
	module = None
	model = None
	obj = None
	template_name = 'courses/manage/content/form.html'

	def get_model(self, model_name):
		'''Check if module name is a content model the uses Django
		app model to get get matching class'''
		if model_name in ['text', 'video', 'image', 'file']:
			return apps.get_model(app_label='courses', model_name=model_name)
		return None	

	def get_form(self, model, *args, **kwargs):
		'''Build form using model_factory function'''
		Form = modelform_factory(model, exclude=['owner','order','created', 'updated'])
		return Form(*args, **kwargs)

	def dispatch(self, request, module_id, model_name, id=None):
		'''It receives the following URL parameters and stores the corresponding module,'''
		self.module = get_object_or_404(Module, id=module_id, course__owner=request.user)
		self.model = self.get_model(model_name)
		if id:
			self.obj = get_object_or_404(self.model, id=id, owner=request.user)
		return super(ContentCreateUpdateView, self).dispatch(request, module_id, model_name, id)	

	def get(self, request, module_id, model_name, id=None):
		'''Responds to GET request by buildiing modelform for content. No new object is created
		as id is set to NONE'''
		form = self.get_form(self.model, instance=self.obj)
		return self.render_to_response({'form': form,'object': self.obj})

	def post(self, request, module_id, model_name, id=None):
		'''Responds to POST. Form built by passing submitted data and files to it
		After form is validated new object is created. If not no id is given
		we know that the user is creating new objecy'''
		form = self.get_form(self.model, instance=self.obj, data=request.POST, files=request.FILES)

		if form.is_valid():
			obj = form.save(commit=False)
			obj.owner = request.user
			obj.save()
			if not id:
				# if new content
				Content.objects.create(module=self.module, item=obj)
				return redirect('module_content_list', self.module.id)
		return self.render_to_response({'form': form, 'object':self.obj})	


class ContentDeleteView(View):
	'''Gets the content object with given Id, deletes related data
	Content object then redirects to module_content_list url'''
	def post(self, request, id):
		content = get_object_or_404(Content,id=id,module__course__owner=request.user)
		module = content.module
		content.item.delete()
		content.delete()
		return redirect('module_content_list', module.id)


class ModuleContentListView(TemplateResponseMixin, View):
	template_name = 'courses/manage/module/content_list.html'

	def get(self, request, module_id):
		module = get_object_or_404(Module, id=module_id, course__owner= request.user)
		return self.render_to_response({'module': module})


class ModuleOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
	'''CsrfExemptMixin avoids checking for token in POST requests
	JsonRequestResponseMixin parses to JSON and returns a JSON response
	as (application/json contentype)'''
	def post(self, request):
		for id, order in self.request_json.items():
			Module.objects.filter(id=id, course__owner=request.user).update(order=order)
		return self.render_json_response({'saved':'OK'})	


class ContentOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
	def post(self, request):
		for id, order in self.request_json.items():
			Content.objects.filter(id=id,module__course__owner=request.user).update(order=order)
		return self.render_json_response({'saved':'OK'})








		



