from django.contrib import admin
from .models import Profile, Classroom, Enrollment, Question, Submission

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)

@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'professor', 'join_code', 'created_at')
    search_fields = ('name', 'join_code')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'classroom', 'joined_at')

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'classroom', 'language', 'due_date', 'posted_at')
    list_filter = ('language', 'classroom')

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'question', 'submitted_at')
