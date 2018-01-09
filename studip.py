import requests
import time
url = 'https://studip.uni-osnabrueck.de/plugins.php/restipplugin/api/'

class Studip:

    def __init__(self, username, password):
        self._username = username
        self._password = password

    def get_response(self, key):
        response = requests.get(url + key, auth=(self._username,
                                                 self._password))
        return response.json()[key]

    def get_name_email(self):
        user = self.get_response('user')
        name = user['forename'] + ' ' + user['lastname']
        email = user['email']
        return name, email

    def get_semester_id(self):
        semester_name = "SS 2017"  # this could be passed as an input
        semesters = self.get_response('semesters')
        for k in range(len(semesters)):
            if semesters[k]['title'] == semester_name:
                return semesters[k]['semester_id']
        raise ValueError('Wrong Semester Name') # for when the name is passed as input

    def get_semester_courses(self):
        semester_id = self.get_semester_id()
        all_cs = self.get_response('courses')
        courses = {}
        print
        for c in range(len(all_cs)):
            if all_cs[c]['semester_id'] == semester_id:
                if str(all_cs[c]['number'])[:1] == '8':  # only cogsci courses
                    id = all_cs[c]['course_id']
                    num = all_cs[c]['number']
                    name = all_cs[c]['title']
                    courses[id] = list([num, name])
        return courses

    def get_course_schedule(self, course_response):
        schedule = []
        for session in range(len(course_response)):
            current_session = course_response[session]['iso_start']
            schedule.append(current_session[:current_session.index('T')])
        return schedule

    def get_course_timing(self, dateNtime):
        return dateNtime[(dateNtime.index('T')+1):]

    def get_course_info(self, course_name):
        course_name = course_name.strip()
        semester_id = self.get_semester_id()
        courses = self.get_semester_courses()
        course_id = next(key for key in courses if courses[key][1] == course_name)

        course_response = requests.get(url + 'courses/' + course_id + '/events',
                                         auth=(self._username, self._password))
        course_response = course_response.json()['events']
        course_info = {}
        if course_response:   # some of the courses does not have this information
            #course_info['location'] = course_response[0]['room']
            course_info['schedule'] = self.get_course_schedule(course_response)
            course_info['timing'] = self.get_course_timing(course_response[0]['iso_start'])
        return course_info

    def isToday(self, course_name):
        course_name = course_name.strip()
        istoday = False
        currentDate = time.strftime("%Y-%m-%d")
        course_info = self.get_course_info(course_name)
        if course_info and currentDate in course_info['schedule']: istoday = True
        return istoday, course_info

    def isNow(self, course_name):
        course_name = course_name.strip()
        isnow = False
        istoday, course_info = self.isToday(course_name)
        if istoday:
            current_time = time.strftime("%H%M")  # change this to check!
            course_time = course_info['timing'][0:2] + '00'
            isnow = int(course_time) <= int(current_time) < (int(course_time) + 200)
        return isnow

    def whichToday(self):
        semester_courses = self.get_semester_courses()
        today_courses = {}
        for key in semester_courses:
            if self.isToday(semester_courses[key][1])[0]:
                today_courses[key] = semester_courses[key]
        return today_courses

    def whichNow(self):
        semester_courses = self.get_semester_courses()
        current_courses = {}
        for key in semester_courses:
            if self.isNow(semester_courses[key][1]):  # if there are two courses hapening in the same time, both will be added
                current_courses[key] = semester_courses[key]
        return current_courses
