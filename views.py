from django.shortcuts import render, redirect
from athena.models import RRFeedback, Subject, Student, Break, Repetition
from athena.models import Question, Vote
from ldap3 import Server, Connection, SIMPLE, SYNC, ALL
from django.utils import timezone
from datetime import timedelta
import json
import requests
from athena.studip import Studip
from athena.conversation import Conversation_Service
import re
from django.http import HttpResponse,Http404
from django.http import HttpResponseRedirect
from django.template import RequestContext, loader
from django.urls import reverse
from django.views.generic import View
from django.contrib.auth import REDIRECT_FIELD_NAME,login,logout 
from django.views.generic import FormView, RedirectView, TemplateView
from django.core.urlresolvers import reverse
# They could be further used:
# from django import form
# from django.http import HttpResponse
# from django.db.models import F

# IMPORTANT: If any import from ldap3 is not working, check the CHANGELOG
# from its site. The may have changed some class names. For example SIMPLE was
# AUTH_SIMPLE before

# Basically the views are used for defining how the site displays content,
# retrieving and managing the db, user interaction, etc. And so how the html
# template is gonna receive info from the backend.

# University host addresses for using LDAP protocol
HOST1 = 'ldaps://ldap-01.uos.de'
HOST2 = 'ldaps://ldap-02.uos.de'
# Server object connection with all required parameters
S = Server(HOST1, port=636, use_ssl=True,
		   allowed_referral_hosts=[(HOST2, True)], get_info=ALL)
# only needed attributes
ATTRS = ['cn', 'givenname', 'hismatriculationnumber', 'mail']

# Watson Conversation
last_answer_id = 0
# chat_history = []
rr = False
courses = {}
# Current subject
curr_subject = 0
context = {}


def index(request):
	"""Index page rendering.
	Load all info if the studendt is in, initialize the conversation
	instance with the service credentials above.
	"""
	try:
		request.session['chat_history']
	except Exception:
		request.session['chat_history'] = []
	if request.session.get('logged_in', False):
		updateBreaks()
		updateRepeats()
		questions = Question.objects.filter(subject=curr_subject)
		stud = loggedinStudent(request)
		repeats = Repetition.objects.filter(subject=curr_subject).count()
		breaks = Break.objects.filter(subject=curr_subject).count()
		req_break = Break.objects.filter(student=stud, subject=curr_subject)
		ask_repeat = Repetition.objects.filter(student=stud,
											   subject=curr_subject)
		return render(
			request,
			'index.html',
			{
				# defines the templte variables used and their assigned values
				'questions': questions,
				'nbreaks': breaks,
				'req_break': req_break,
				'nrepetitions': repeats,
				'ask_repeat': ask_repeat,
				'qlist': checkVotes(request),
				'cvotes': countVotes(),
				'chat_history': request.session['chat_history'],
				'courses': courses,
				'curr_subject': curr_subject
			}
		)
	else:
		return render(
			request,
			'index.html',
			{
				'chat_history': request.session['chat_history'],
			}
		)

def login(request):
	"""Log in the student if the credentials are correct."""
	global courses
	global curr_subject

	request.session['wrong_user_passwd'] = False
	if request.POST.get('logout'):
		request.session['logged_in'] = False
		# c.unbind()
		# c.close()
		return redirect('home')
	if request.session.get('logged_in', False):
		return redirect('home')
	else:
		USERNAME = request.POST.get('username')
		if '@' in USERNAME:
			# filters the username, allowing @uos.de and @uni-osnabrueck.de too
			domain_match = re.search(
				'(\W|^)[\w.+\-]*@(uos|uni-osnabrueck)\.de(\W|$)', USERNAME)
			if domain_match:
				USERNAME = USERNAME.split('@')
				USERNAME = USERNAME[0]
			else:
				request.session['wrong_user_passwd'] = True
				return redirect('home')
		PASSWORD = request.POST.get('password')
		username_dn = 'uid=' + str(USERNAME) + (',ou=people,'
												'dc=uni-osnabrueck,dc=de'
												)
		search_filter = '(uid=' + str(USERNAME) + ')'
		# defines a LDAP connection using user credentials and server params
		c = Connection(S, authentication=SIMPLE, user=username_dn,
					   password=PASSWORD, check_names=True, lazy=False,
					   client_strategy=SYNC, raise_exceptions=False)
		try:
			c.open()
		except Exception:
			request.session['wrong_user_passwd'] = True
			return redirect('home')
		if not c.bind():
			request.session['wrong_user_passwd'] = True
			return redirect('home')
		else:# in case of a successful login retrieves some user information
			c.search(username_dn, search_filter, attributes=ATTRS)
			user = c.entries[0]
			request.session['full_name'] = user['cn'].value
			request.session['name'] = user['givenname'].value
			request.session['email'] = user['mail'].value
			request.session['matr_num'] = user['hismatriculationnumber'].value
			request.session['logged_in'] = True
			stud = loggedinStudent(request)
			st = Student()
			stip = Studip(USERNAME, PASSWORD)
			courses = stip.get_semester_courses()
			curr_subject = list(courses.keys())[0]
			store_courses(courses)
			request.session['courses'] = courses
			request.session['curr_subject'] = curr_subject

			if not stud:  # for 1st login stores the user info into the db
				st.name = request.session['full_name']
				st.mail = request.session['email']
				st.matr_num = request.session['matr_num']
				st.save()
			else:  # for a further login it updates the current login timestamp
				stud.last_login = timezone.now()
				stud.save(update_fields=['last_login'])

		#url = reverse('course', kwargs={'courses': courses,
			#'curr_subject':curr_subject})
		#return HttpResponseRedirect(url)
		#return HttpResponseRedirect(reverse('course', args=(courses,curr_subject, )))	
		return HttpResponseRedirect('course')


		#return render(request,'course.html',{
			#'courses':courses,
			#'curr_subject':curr_subject
			#})
	#return redirect('course')



def updateBreaks():
	"""Check, and if so delete, the expired breaks."""
	# <-- __lte for less than and __gte for greater than
	expired_breaks = Break.objects.filter(time__lte=(timezone.now() -
													 timedelta(minutes=10)),
										  subject=curr_subject)
	expired_breaks.delete()


def updateRepeats():
	"""Check, and if so delete, the expired repetitions."""
	expired_repetitions = Repetition.objects.filter(time__lte=(timezone.now() -
															   timedelta
															   (minutes=10)),
													subject=curr_subject)
	expired_repetitions.delete()


def loggedinStudent(request):
	"""Return the student db object from its matriculation number."""
	# IMPORTANT: if the student does not exist it uses .filter, if it does .get
	stud = Student.objects.filter(matr_num=request.session['matr_num'])
	if stud:
		return Student.objects.get(matr_num=request.session['matr_num'])
	else:
		return stud


def checkVotes(request):
	"""Return a dict with the voted (or not) questions."""
	qlist = {}
	stud = loggedinStudent(request)
	for ident in Question.objects.values_list('id', flat=True):
		if Vote.objects.filter(question=ident, student=stud):
			qlist[ident] = True
		else:
			qlist[ident] = False
	return qlist


def countVotes():
	"""Return a dictionary with the number of votes per question."""
	vcount = {}
	for ident in Question.objects.values_list('id', flat=True):
		vcount[ident] = Vote.objects.filter(question=ident).count()
	return vcount


	

def store_courses(courses):

	"""Store courses in case they are not in the Subject table."""
	for course in courses:
		if not Subject.objects.filter(id=course):
			sb = Subject(id=course,
						 num=courses[course][0],
						 name=courses[course][1])
			sb.save()





#def change_subject(request):
	"""Change the current course."""
	
	#global curr_subject
	
	#courses = Subject.objects.all()
	#curr_subject = request.POST['subject']
	#curr_subject = request.POST.get('subject', False);
	#request.session['courses'] = courses
	#request.session['curr_subject'] = curr_subject
	#return HttpResponse('subject')

	#return HttpResponse('subject')

	#return redirect('subject')

	#return render(request,'course.html',
		#{
		#'courses':courses,
		#'curr_subject': curr_subject
		#})


def change_subject(request):
	"""Change the current course."""
	global curr_subject
	#curr_subject = request.POST['subject']
	curr_subject = request.POST.get('subject', False);
	request.session['curr_subject'] = request.POST.get('subject', False);
	updateBreaks()
	updateRepeats()
	questions = Question.objects.filter(subject=curr_subject)
	stud = loggedinStudent(request)
	repeats = Repetition.objects.filter(subject=curr_subject).count()
	breaks = Break.objects.filter(subject=curr_subject).count()
	req_break = Break.objects.filter(student=stud, subject=curr_subject)
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject)
	return render(request,'course.html',{
		'curr_subject':curr_subject,
		'questions': questions,
		'nbreaks': breaks,
		'req_break': req_break,
		'nrepetitions': repeats,
		'ask_repeat': ask_repeat,
		'qlist': checkVotes(request),
		'cvotes': countVotes(),		
		'courses': courses,
		})



def breakrequest(request):
	"""Store a break in the db and reloads the site."""
	updateBreaks()
	stud = loggedinStudent(request)
	# !! use of .get instead of .filter throws error if no object is found
	req_break = Break.objects.filter(student=stud,
									 subject=curr_subject).count()
	if not req_break:
		subject = Subject.objects.get(id=curr_subject)
		b = Break(student=stud, subject=subject)
		b.save()
	questions = Question.objects.filter(subject=curr_subject)
	breaks = Break.objects.filter(subject=curr_subject).count()
	req_break = Break.objects.filter(student=stud, subject=curr_subject)
	repeats = Repetition.objects.filter(subject=curr_subject).count()
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject)

	#return redirect('course')

	return render(request,'course.html',
		{
		'curr_subject':curr_subject,
		'questions':questions,
		'nbreaks': breaks,
		'req_break': req_break,
		'nrepetitions': repeats,
		'ask_repeat': ask_repeat,
		})


def repetition(request):
	"""Store a repetition in the db and reload the site."""
	updateRepeats()
	
	stud = loggedinStudent(request)
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject).count()
	if not ask_repeat:
		subject = Subject.objects.get(id=curr_subject)
		r = Repetition(student=stud, subject=subject)
		r.save()
	questions = Question.objects.filter(subject=curr_subject)
	breaks = Break.objects.filter(subject=curr_subject).count()
	req_break = Break.objects.filter(student=stud, subject=curr_subject)
	repeats = Repetition.objects.filter(subject=curr_subject).count()
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject)

	#return redirect('course')
	return render(request,'course.html',{
		'curr_subject':curr_subject,
		'questions':questions,
		'nbreaks': breaks,
		'req_break': req_break,
		'nrepetitions': repeats,
		'ask_repeat': ask_repeat,
		})


def postquestion(request):
	"""Store a question into db and reload the site."""
	stud = loggedinStudent(request)
	subject = Subject.objects.get(id=curr_subject)
	q = Question(student=stud, subject=subject)
	q.question = request.POST.get('question', False);
	#question = request.POST.get('question', False);
	#questions = Question.objects.filter(question=question)
	q.save()
	questions = Question.objects.filter(subject=curr_subject)
	repeats = Repetition.objects.filter(subject=curr_subject).count()
	breaks = Break.objects.filter(subject=curr_subject).count()
	req_break = Break.objects.filter(student=stud, subject=curr_subject)
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject)
	qlist=checkVotes(request)
	cvotes=countVotes()

	#return redirect('course')
	return render(request,'course.html',{
		'curr_subject':curr_subject,
		'questions':questions,
		'qlist': qlist,
		'cvotes': cvotes,
		'nbreaks': breaks,
		'req_break': req_break,
		'nrepetitions': repeats,
		'ask_repeat': ask_repeat,
		})


def votequestion(request):
	"""Store a vote for a question and reloads the site."""
	stud = loggedinStudent(request)  # only matr_num needed, can be done easier
	quest = Question.objects.get(id=request.POST['id'])
	questions = Question.objects.filter(subject=curr_subject)
	if request.session.get(request.POST['id'], False):
		return redirect('course')
	subject = Subject.objects.get(id=curr_subject)
	v = Vote(student=stud, question=quest, subject=subject)
	v.save()
	repeats = Repetition.objects.filter(subject=curr_subject).count()
	breaks = Break.objects.filter(subject=curr_subject).count()
	req_break = Break.objects.filter(student=stud, subject=curr_subject)
	ask_repeat = Repetition.objects.filter(student=stud,
										   subject=curr_subject)
	qlist=checkVotes(request)
	cvotes=countVotes()
	return render(request,'course.html',{
		'curr_subject':curr_subject,
		'qlist': qlist,
		'cvotes': cvotes,
		'questions':questions,
		'nbreaks': breaks,
		'req_break': req_break,
		'nrepetitions': repeats,
		'ask_repeat': ask_repeat,
		})
 




def getemoji(request, emojiname):
	"""Return an emoji file from an emoji input code."""
	image_path = 'emoji/' + str(emojiname) + '.png'
	return render(request, 'index.html', {"image_path": image_path})

def conversation(request):
	try:
		request.session['chat_history']
	except Exception:
		request.session['chat_history'] = []
	# ------------------------------------------------------------
	"""Deal with the conversation service."""
	settings = dict(
		username='9b01abb8-3a96-4e16-beb1-60c366185e5e',
		password='JSywMubw6obe',
		version='2017-05-26',
		workspace_id='984cf8c4-393a-4786-a327-90bf8232f79a'
	)

	# ------------------------------------------------------------
	# for removing not used variables anymore
	def cleanse_context(context):
		# keys that can stay the in context
		stay = ['conversation_id', 'system']

		for key in list(context):
			# in case we want to delete the key...
			if not(key in stay):
				del context[key]
		return context
	# ------------------------------------------------------------

	# global variables
	# global chat_history
	global rr
	global service
	global context
	chat_history = request.session['chat_history']

	# ------------------------------------------------------------
	# create object and start up conversation
	# get input from the input field on the webpage
	query = request.POST.get('conv_question')

	# check if conversation is initialized. if not, do so
	try:
		service
	except Exception:
		service = Conversation_Service(settings)
		context = service.conversation_init()

	# ------------------------------------------------------------
	# in case rr is true, a question is incoming
	# in this case, instead of sending the query to conversation,
	# we send it to rank and retrieve
	if rr:
		output = rank_and_retrieve(query) + '\n\nWas that answer useful?'
		# false, until again set to true
		rr = False

	# standard way: send query to conversation
	else:
		output, intent, entities = service.talk(query, context)

		# in case he wants answers
		if 'rank_retrieve' in context.keys():
			# set rr to true, next input is going to be a question
			# and is sent to rank and retrieve
			rr = True

		if 'inst_rank_retrieve' in context.keys():
			output = rank_and_retrieve(query) + '\n\nWas that answer useful?'
	# ------------------------------------------------------------
	# save output and display it
	if 'useful' in context.keys():
		if not context['useful']:
			rr_feedback(request, question=query, answer=output, useful=False)
		else:
			rr_feedback(request, question=query, answer=output)
	else:
		rr_feedback(request, question=query, answer=output)
	chat_history.append(list([query, output]))
	request.session['chat_history'] = chat_history
	print(context)
	# ------------------------------------------------------------
	# cleanse context at the end
	context = cleanse_context(context)

	# ------------------------------------------------------------
	return render(request,'ava.html',{
		'chat_history': request.session['chat_history'],
		})


def rank_and_retrieve(query):
	"""Send the query  to the R & R."""
	user = 'd29cd5aa-148b-440c-b260-379b696439f8'
	passwd = 'L6lou1y3Wsdg'
	url = ('https://gateway.watsonplatform.net/retrieve-and-rank/api/v1/'
		   'solr_clusters/sc57cbf3ee_2d6f_4868_b622_604855deab65/solr/'
		   'Pepper_May17/fcselect?ranker_id=27be5bx32-rank-5980&q=' + query +
		   '&wt=json&fl=body&rows=1'
		   )
	rank_request = requests.get(url, auth=(user, passwd))
	rank_answer = json.loads(rank_request.text)
	# cut out the relevant part of the response, cast it to string
	try:
		# just "saying" the first 200 characters of the response in order to
		# not have to wait so long in general the whole answer should be used
		# of course:
		# ans_short = ans[:200]
		ans = rank_answer['response']['docs'][0]['body']
	except Exception:  # find a better way to handle exceptions
		ans = 'I am sorry. I did not find an answer.'
	return ans


def rr_feedback(request, answer, question='no question', useful=True):
	"""Store the conversation feedback."""
	global last_answer_id
	if useful:
		rr = RRFeedback(question=question, answer=answer, useful=useful,
						session=request.COOKIES['csrftoken'])
		last_answer_id = rr.id
		rr.save()
	else:
		rr = RRFeedback.objects.get(id=last_answer_id)
		rr.useful = False
		rr.save(update_fields=['useful'])



