"""Athena URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import url,include
from django.contrib import admin
from athena import views
from django.views.generic.base import TemplateView
from django.views.generic import View
# Here urls are defined, also urls for the form actions (login, vote...)
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    #url(r'^$', views.IndexView.as_view(), name='home'),
    #url(r'^$', LoginView.as_view(template_name='index.html'), name="index"),
    #url(r'^$', views.HomePageView.as_view(), name='home'),home
    url(r'^$', views.index, name='home'),
    #url(r'^$', TemplateView.as_view(template_name='index.html'),name="home"),
    #url(r'^course/$', CourseView.as_view(), name='course'),
    url(r'^login/$', views.login, name='login'), 
    #url(r'^logout/$', LogoutView.as_view(), name='logout'),
    #url(r'^logout/$', views.logout, name='logout'),  
    url(r'^login/course/subject/break$', views.breakrequest, name='break'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    #url(r'^login/course/subject/break_and_repeat$', views.break_and_repeat, name='breakandrepeat'),
    url(r'^login/course/subject/repetition$', views.repetition, name='repetition'),
    url(r'^login/course/subject/question$', views.postquestion, name='question'),
    url(r'^login/course/subject/vote$', views.votequestion, name='vote'),
    url(r'^ava/$', views.conversation, name='conversation'),
    url(r'^login/course/subject/$', views.change_subject, name='subject'),
    #url(r'^login/course/subject/details/$', views.subject_details, name='details'),
    #url(r'^login/course/subject=(?P<modelname>\w+)/$',views.change_subject, 
    #name='subject'),
    url(r'^game/$', TemplateView.as_view(template_name='game.html')),
    url(r'^login/course/$', TemplateView.as_view(template_name='course.html'),name='course'),
    #url(r'^ava/$', TemplateView.as_view(template_name='ava.html'),name='ava'),
]
urlpatterns += staticfiles_urlpatterns()
