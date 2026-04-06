from django.urls import path
from . import views

urlpatterns = [
    path('',                                    views.home,               name='home'),
    path('dashboard/',                          views.dashboard,          name='dashboard'),
    path('profile/setup/',                      views.profile_setup,      name='profile_setup'),

    # Classroom
    path('classroom/create/',                   views.create_classroom,   name='create_classroom'),
    path('classroom/<int:pk>/',                 views.classroom_detail,   name='classroom_detail'),
    path('classroom/<int:pk>/edit/',            views.edit_classroom,     name='edit_classroom'),
    path('classroom/join/',                     views.join_classroom,     name='join_classroom'),

    # Questions
    path('classroom/<int:classroom_pk>/question/new/', views.post_question,   name='post_question'),
    path('question/<int:pk>/',                  views.question_detail,    name='question_detail'),

    # IDE
    path('api/run/',                            views.run_code,           name='run_code'),
    path('api/submit/<int:question_pk>/',       views.submit_code,        name='submit_code'),
    path('api/stats/<int:pk>/',                 views.question_stats_json, name='question_stats'),

    # Professor views student code
    path('submission/<int:pk>/',                views.view_submission,    name='view_submission'),
]
