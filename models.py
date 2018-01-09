from django.db import models
import uuid
from django.utils import timezone
from django.forms import ModelForm,ChoiceField

# Here is where the database objects (tables) are defined


class Student(models.Model):
    """Table containing students' info and its last login timestamp."""

    matr_num = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    mail = models.EmailField()
    last_login = models.DateTimeField(default=timezone.now, editable=True)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return str(self.matr_num)


class Subject(models.Model):
    """Table containing the subjets, aka lectures and seminars."""

    id = models.CharField(primary_key=True, max_length=32)
    num = models.CharField(max_length=6)
    name = models.CharField(max_length=200)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return str(self.num) + ' - ' + self.name



class RRFeedback(models.Model):
    """Table containing the Conversation and R&R services feedback."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    time = models.DateTimeField(default=timezone.now, editable=True)
    session = models.CharField(max_length=64)
    question = models.CharField(max_length=200,blank=True, null=True)
    answer = models.CharField(max_length=650)
    useful = models.BooleanField(default=True)

    class Meta(object):
        """Ordering of the table records based on the time field ascending."""

        ordering = ('time',)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return 'User: ' + str(self.question) + ' - Pepper: ' + self.answer


class Break(models.Model):
    """Table containing the break requests during class."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now, editable=True)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return str(self.student.matr_num)




class Repetition(models.Model):
    """Table containing the topic repetition requests during class."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now, editable=True)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return str(self.student.matr_num)


class Question(models.Model):
    """Table containing the questions for a specific lecture."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    question = models.CharField(max_length=200)
    time = models.DateTimeField(default=timezone.now, editable=True)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return self.question


class Vote(models.Model):
    """Table containing the votes with its related question and student."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    time = models.DateTimeField(default=timezone.now, editable=True)

    def __str__(self):
        """Rewrites how the table records are shown on the admin site."""
        return str(self.student.matr_num) + ': ' + self.question.question
