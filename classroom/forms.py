from django import forms
from .models import Classroom, Question, Submission, Profile


class ProfileSetupForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role']
        widgets = {
            'role': forms.RadioSelect
        }


class ClassroomForm(forms.ModelForm):
    class Meta:
        model = Classroom
        fields = ['name', 'description', 'allowed_emails']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. CS101 - Data Structures'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Short description...'}),
            'allowed_emails': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'student1@gmail.com, student2@gmail.com, ...'
            }),
        }
        help_texts = {
            'allowed_emails': 'Enter Gmail addresses separated by commas. Only these students can join.'
        }


class JoinClassroomForm(forms.Form):
    join_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'placeholder': 'Enter 6-digit class code', 'class': 'form-control'})
    )


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['title', 'description', 'language', 'starter_code', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Question title...'}),
            'description': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe the problem...'}),
            'starter_code': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Optional starter code...', 'class': 'code-textarea'}),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']


class CodeRunForm(forms.Form):
    code  = forms.CharField(widget=forms.Textarea)
    stdin = forms.CharField(required=False, widget=forms.Textarea)
    language = forms.CharField()
