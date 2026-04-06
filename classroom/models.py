from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Profile(models.Model):
    """Extra info attached to every User."""
    ROLE_CHOICES = [('professor', 'Professor'), ('student', 'Student')]
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='', blank=True)
    avatar     = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} ({self.role})"

    def is_professor(self):
        return self.role == 'professor'


class Classroom(models.Model):
    """A classroom created by a professor."""
    name        = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    professor   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='classrooms')
    join_code   = models.CharField(max_length=10, unique=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    # Students allowed by email
    allowed_emails = models.TextField(
        blank=True,
        help_text="Comma-separated Gmail addresses allowed to join"
    )

    def __str__(self):
        return self.name

    def get_allowed_email_list(self):
        return [e.strip().lower() for e in self.allowed_emails.split(',') if e.strip()]


class Enrollment(models.Model):
    """A student enrolled in a classroom."""
    student    = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    classroom  = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='enrollments')
    joined_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'classroom')

    def __str__(self):
        return f"{self.student.email} in {self.classroom.name}"


class Question(models.Model):
    """A weekly coding question posted by professor."""
    LANGUAGE_CHOICES = [
        ('python', 'Python'),
        ('javascript', 'JavaScript'),
        ('cpp', 'C++'),
        ('c', 'C'),
        ('java', 'Java'),
    ]
    classroom    = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='questions')
    title        = models.CharField(max_length=300)
    description  = models.TextField()
    language     = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='python')
    starter_code = models.TextField(blank=True, help_text="Optional starter code for students")
    due_date     = models.DateTimeField()
    posted_at    = models.DateTimeField(auto_now_add=True)
    posted_by    = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    def is_past_due(self):
        return timezone.now() > self.due_date

    def on_time_count(self):
        return self.submissions.filter(submitted_at__lte=self.due_date).count()

    def late_count(self):
        return self.submissions.filter(submitted_at__gt=self.due_date).count()

    def total_submissions(self):
        return self.submissions.count()


class Submission(models.Model):
    """A student's code submission for a question."""
    question     = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='submissions')
    student      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    code         = models.TextField()
    language     = models.CharField(max_length=20)
    submitted_at = models.DateTimeField(auto_now_add=True)
    last_output  = models.TextField(blank=True, help_text="Last terminal output")

    class Meta:
        unique_together = ('question', 'student')  # one submission per student per question

    def __str__(self):
        return f"{self.student.email} → {self.question.title}"

    def is_on_time(self):
        return self.submitted_at <= self.question.due_date
