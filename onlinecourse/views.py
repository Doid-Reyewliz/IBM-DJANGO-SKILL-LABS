from django.shortcuts import render
from django.http import HttpResponseRedirect
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def submit(request, course_id):
    user = request.user

    enroll = Enrollment.objects.get(user=user, course=course_id)
    sub = Submission.objects.create(enrollment=enroll)
    # sub = [Submission.objects.get(enrollment=enroll)]

    res = show_exam_result(request, enroll.course.id, sub.id)
    return res

def extract_answers(request):
    submitted_anwsers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_anwsers.append(choice_id)
        else:
            return 'empty'
    return submitted_anwsers

def show_exam_result(request, course_id, submission_id):
    que = Question.objects.filter(course=course_id).values()
    que_count = Question.objects.filter(course=course_id).count()
    choice = []
    for i in range(que_count):
        choice.append(Choice.objects.filter(question=que[i]['id'], correct=1).values())

    context = {}
    answers = []

    context['all'] = []

    for i in range(que_count):
        answers.append(choice[i][0]['id'])


    choiced = extract_answers(request)
    total = 0

    print(choiced)

    if choiced != 'empty':
        for i in range(len(choiced)):
            if choiced[i] == answers[i]: 
                total+=1
    
        for i in range(que_count):
            context['all'].append({
                "question": Question.objects.get(id=que[i]['id']),
                "chooced": Choice.objects.get(id=choiced[i]).answers,
                "correct": Choice.objects.get(id=answers[i]).answers
            })
    
    context['grade'] = int(100 * float(total)/float(que_count))
    context['score'] = total
    
    if len(choiced) == total:
        context['message'] = "Congratulations"
    else:
        context['message'] = "Failed"
    
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
    # return HttpResponseRedirect(reverse(viewname='onlinecourse:show_result', args=(course_id, submission_id)))