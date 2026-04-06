import json
import subprocess
import tempfile
import os
import random
import string

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Profile, Classroom, Enrollment, Question, Submission
from .forms import ProfileSetupForm, ClassroomForm, JoinClassroomForm, QuestionForm


# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_or_create_profile(user):
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile

def generate_join_code():
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        if not Classroom.objects.filter(join_code=code).exists():
            return code


# ── SECURITY: Block dangerous code patterns ───────────────────────────────────

BLOCKED_PATTERNS = {
    'python': [
        'import os', 'import sys', 'import subprocess', 'import shutil',
        'import socket', 'import urllib', 'import requests', 'import ftplib',
        'import telnetlib', 'import smtplib', '__import__', '__builtins__',
        'open(', 'exec(', 'eval(', 'compile(', 'os.system', 'os.popen',
        'os.remove', 'os.rmdir', 'os.unlink', 'os.listdir', 'os.getcwd',
        'shutil.rmtree', 'subprocess', 'shutdown', 'getattr(', 'setattr(',
        'globals(', 'locals(',
    ],
    'javascript': [
        'require(', 'process.exit', 'process.env', 'process.kill',
        '__dirname', '__filename', 'fs.', 'child_process',
        'exec(', 'eval(', 'spawn(', 'net.', 'http.', 'https.', 'os.',
    ],
    'c': [
        'system(', 'popen(', 'unlink(', 'remove(', 'rmdir(', 'fork(',
        'execvp(', 'execl(', 'execlp(', 'execle(', 'execv(', 'execve(',
        'fopen(', 'freopen(',
    ],
    'cpp': [
        'system(', 'popen(', 'unlink(', 'remove(', 'rmdir(', 'fork(',
        'execvp(', 'execl(', 'execlp(', 'execle(', 'execv(', 'execve(',
        'fopen(', 'freopen(', 'filesystem',
    ],
    'java': [
        'Runtime.getRuntime()', 'ProcessBuilder', 'System.exit',
        'new File(', 'FileWriter', 'FileReader', 'FileInputStream',
        'FileOutputStream', 'exec(', 'ClassLoader', 'java.net',
    ],
}

def is_code_safe(code, language):
    patterns = BLOCKED_PATTERNS.get(language, [])
    for pattern in patterns:
        if pattern.lower() in code.lower():
            return False, f"'{pattern}' is not allowed for security reasons."
    return True, None


# ── HOME / AUTH ───────────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'classroom/home.html')


@login_required
def profile_setup(request):
    profile = get_or_create_profile(request.user)
    if request.method == 'POST':
        form = ProfileSetupForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = ProfileSetupForm(instance=profile)
    return render(request, 'classroom/profile_setup.html', {'form': form})


@login_required
def dashboard(request):
    profile = get_or_create_profile(request.user)
    if not profile.role or profile.role == '':
        return redirect('profile_setup')
    if profile.is_professor():
        classrooms = Classroom.objects.filter(professor=request.user).order_by('-created_at')
        return render(request, 'classroom/professor_dashboard.html', {'classrooms': classrooms})
    else:
        enrollments = Enrollment.objects.filter(student=request.user).select_related('classroom')
        return render(request, 'classroom/student_dashboard.html', {'enrollments': enrollments})


# ── PROFESSOR: CLASSROOM ──────────────────────────────────────────────────────

@login_required
def create_classroom(request):
    profile = get_or_create_profile(request.user)
    if not profile.is_professor():
        messages.error(request, "Only professors can create classrooms.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = ClassroomForm(request.POST)
        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.professor = request.user
            classroom.join_code = generate_join_code()
            classroom.save()
            messages.success(request, f"Classroom created! Share code: {classroom.join_code}")
            return redirect('classroom_detail', pk=classroom.pk)
    else:
        form = ClassroomForm()
    return render(request, 'classroom/create_classroom.html', {'form': form})


@login_required
def classroom_detail(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk)
    profile = get_or_create_profile(request.user)
    if profile.is_professor():
        if classroom.professor != request.user:
            messages.error(request, "Access denied.")
            return redirect('dashboard')
    else:
        if not Enrollment.objects.filter(student=request.user, classroom=classroom).exists():
            messages.error(request, "You are not enrolled in this classroom.")
            return redirect('dashboard')
    questions = classroom.questions.order_by('-posted_at')
    enrollments = classroom.enrollments.select_related('student')
    return render(request, 'classroom/classroom_detail.html', {
        'classroom': classroom,
        'questions': questions,
        'enrollments': enrollments,
        'profile': profile,
        'now': timezone.now(),
    })


@login_required
def edit_classroom(request, pk):
    classroom = get_object_or_404(Classroom, pk=pk, professor=request.user)
    if request.method == 'POST':
        form = ClassroomForm(request.POST, instance=classroom)
        if form.is_valid():
            form.save()
            messages.success(request, "Classroom updated.")
            return redirect('classroom_detail', pk=pk)
    else:
        form = ClassroomForm(instance=classroom)
    return render(request, 'classroom/create_classroom.html', {'form': form, 'edit': True})


# ── STUDENT: JOIN CLASSROOM ───────────────────────────────────────────────────

@login_required
def join_classroom(request):
    profile = get_or_create_profile(request.user)
    if profile.is_professor():
        messages.error(request, "Professors cannot join classrooms as students.")
        return redirect('dashboard')
    if request.method == 'POST':
        form = JoinClassroomForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['join_code'].upper()
            try:
                classroom = Classroom.objects.get(join_code=code)
            except Classroom.DoesNotExist:
                messages.error(request, "Invalid join code.")
                return render(request, 'classroom/join_classroom.html', {'form': form})
            user_email = request.user.email.lower()
            allowed = classroom.get_allowed_email_list()
            if allowed and user_email not in allowed:
                messages.error(request, "Your email is not allowed in this classroom. Contact the professor.")
                return render(request, 'classroom/join_classroom.html', {'form': form})
            enrollment, created = Enrollment.objects.get_or_create(
                student=request.user, classroom=classroom
            )
            if created:
                messages.success(request, f"Joined {classroom.name}!")
            else:
                messages.info(request, "You are already enrolled.")
            return redirect('classroom_detail', pk=classroom.pk)
    else:
        form = JoinClassroomForm()
    return render(request, 'classroom/join_classroom.html', {'form': form})


# ── QUESTIONS ─────────────────────────────────────────────────────────────────

@login_required
def post_question(request, classroom_pk):
    classroom = get_object_or_404(Classroom, pk=classroom_pk, professor=request.user)
    if request.method == 'POST':
        form = QuestionForm(request.POST)
        if form.is_valid():
            q = form.save(commit=False)
            q.classroom = classroom
            q.posted_by = request.user
            q.save()
            messages.success(request, "Question posted!")
            return redirect('classroom_detail', pk=classroom_pk)
    else:
        form = QuestionForm()
    return render(request, 'classroom/post_question.html', {
        'form': form, 'classroom': classroom
    })


@login_required
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)
    profile = get_or_create_profile(request.user)
    classroom = question.classroom
    if profile.is_professor():
        if classroom.professor != request.user:
            return redirect('dashboard')
        submissions = question.submissions.select_related('student').order_by('-submitted_at')
        return render(request, 'classroom/question_professor.html', {
            'question': question,
            'submissions': submissions,
            'on_time': question.on_time_count(),
            'late': question.late_count(),
            'total': question.total_submissions(),
            'enrolled': classroom.enrollments.count(),
        })
    else:
        if not Enrollment.objects.filter(student=request.user, classroom=classroom).exists():
            return redirect('dashboard')
        try:
            submission = Submission.objects.get(question=question, student=request.user)
        except Submission.DoesNotExist:
            submission = None
        return render(request, 'classroom/question_student.html', {
            'question': question,
            'submission': submission,
            'now': timezone.now(),
        })


# ── IDE: RUN CODE ─────────────────────────────────────────────────────────────

@login_required
@require_POST
def run_code(request):
    try:
        data     = json.loads(request.body)
        code     = data.get('code', '')
        stdin    = data.get('stdin', '')
        language = data.get('language', 'python').lower()
    except Exception:
        return JsonResponse({'output': '', 'error': 'Invalid request.'})

    # ── SECURITY CHECK ────────────────────────────────────────────
    safe, reason = is_code_safe(code, language)
    if not safe:
        return JsonResponse({
            'output': '',
            'error': f'SECURITY ERROR: {reason}\n\nThis code contains a restricted command and cannot be executed.'
        })
    # ──────────────────────────────────────────────────────────────

    TIMEOUT = 10

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output = ''
            error  = ''

            if language == 'python':
                filepath = os.path.join(tmpdir, 'main.py')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['python', filepath],
                    input=stdin, capture_output=True, text=True, timeout=TIMEOUT
                )
                output = result.stdout
                error  = result.stderr

            elif language == 'javascript':
                filepath = os.path.join(tmpdir, 'main.js')
                with open(filepath, 'w') as f:
                    f.write(code)
                result = subprocess.run(
                    ['node', filepath],
                    input=stdin, capture_output=True, text=True, timeout=TIMEOUT
                )
                output = result.stdout
                error  = result.stderr

            elif language == 'c':
                src = os.path.join(tmpdir, 'main.c')
                exe = os.path.join(tmpdir, 'main.exe')
                with open(src, 'w') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    ['gcc', src, '-o', exe],
                    capture_output=True, text=True, timeout=TIMEOUT
                )
                if compile_result.returncode != 0:
                    return JsonResponse({'output': '', 'error': compile_result.stderr})
                result = subprocess.run(
                    [exe], input=stdin, capture_output=True, text=True, timeout=TIMEOUT
                )
                output = result.stdout
                error  = result.stderr

            elif language == 'cpp':
                src = os.path.join(tmpdir, 'main.cpp')
                exe = os.path.join(tmpdir, 'main.exe')
                with open(src, 'w') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    ['g++', src, '-o', exe],
                    capture_output=True, text=True, timeout=TIMEOUT
                )
                if compile_result.returncode != 0:
                    return JsonResponse({'output': '', 'error': compile_result.stderr})
                result = subprocess.run(
                    [exe], input=stdin, capture_output=True, text=True, timeout=TIMEOUT
                )
                output = result.stdout
                error  = result.stderr

            elif language == 'java':
                src = os.path.join(tmpdir, 'Main.java')
                with open(src, 'w') as f:
                    f.write(code)
                compile_result = subprocess.run(
                    ['javac', src],
                    capture_output=True, text=True, timeout=TIMEOUT, cwd=tmpdir
                )
                if compile_result.returncode != 0:
                    return JsonResponse({'output': '', 'error': compile_result.stderr})
                result = subprocess.run(
                    ['java', 'Main'],
                    input=stdin, capture_output=True, text=True, timeout=TIMEOUT, cwd=tmpdir
                )
                output = result.stdout
                error  = result.stderr

            else:
                return JsonResponse({'output': '', 'error': f'Language "{language}" is not supported.'})

            return JsonResponse({'output': output, 'error': error})

    except subprocess.TimeoutExpired:
        return JsonResponse({'output': '', 'error': 'Time limit exceeded (10 seconds). Check for infinite loops.'})
    except FileNotFoundError as e:
        return JsonResponse({'output': '', 'error': f'Runtime not found: {e}\nMake sure the language is installed on the server.'})
    except Exception as e:
        return JsonResponse({'output': '', 'error': str(e)})


# ── SUBMIT CODE ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def submit_code(request, question_pk):
    question = get_object_or_404(Question, pk=question_pk)
    if not Enrollment.objects.filter(student=request.user, classroom=question.classroom).exists():
        return JsonResponse({'success': False, 'error': 'Not enrolled.'})
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        last_output = data.get('last_output', '')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid data.'})

    # Security check on submission too
    safe, reason = is_code_safe(code, question.language)
    if not safe:
        return JsonResponse({'success': False, 'error': f'Security Error: {reason}'})

    submission, created = Submission.objects.update_or_create(
        question=question,
        student=request.user,
        defaults={
            'code': code,
            'language': question.language,
            'last_output': last_output,
        }
    )
    on_time = submission.is_on_time()
    return JsonResponse({
        'success': True,
        'created': created,
        'on_time': on_time,
        'submitted_at': submission.submitted_at.strftime('%b %d, %Y %I:%M %p'),
    })


# ── PROFESSOR VIEW STUDENT CODE ───────────────────────────────────────────────

@login_required
def view_submission(request, pk):
    submission = get_object_or_404(Submission, pk=pk)
    if submission.question.classroom.professor != request.user:
        return redirect('dashboard')
    return render(request, 'classroom/view_submission.html', {'submission': submission})


# ── STATS API ─────────────────────────────────────────────────────────────────

@login_required
def question_stats_json(request, pk):
    question = get_object_or_404(Question, pk=pk)
    if question.classroom.professor != request.user:
        return JsonResponse({'error': 'Forbidden'}, status=403)
    enrolled = question.classroom.enrollments.count()
    on_time  = question.on_time_count()
    late     = question.late_count()
    not_submitted = enrolled - on_time - late
    return JsonResponse({
        'labels': ['On Time', 'Late', 'Not Submitted'],
        'data':   [on_time, late, not_submitted],
        'colors': ['#22c55e', '#f59e0b', '#ef4444'],
    })
