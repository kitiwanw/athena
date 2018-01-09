from django.contrib import admin
from athena.models import RRFeedback, Subject, Student, Break, Repetition
from athena.models import Question, Vote
from django.http import HttpResponse
from django.db.models import ManyToOneRel

# Here the database objects (tables) are registered to the admin site /admin
# in order to be graphically seen (like in phpmyadmin) and easily handled


def export_as_csv(modeladmin, request, queryset):
    """Export to .csv the current model (table) of the DB."""
    import csv
    response = HttpResponse(content_type='text/csv')
    title = queryset.model._meta.verbose_name_plural.title()
    response['Content-Disposition'] = 'attachment;filename="' + title + '.csv"'
    writer = csv.writer(response, csv.excel)
    response.write(u'\ufeff'.encode('utf8'))
    fields = queryset.model._meta.get_fields()
    header = [field.name for field in fields
              if not isinstance(field, ManyToOneRel)]
    writer.writerow(header)
    for instance in queryset:
        row = [getattr(instance, field)() if callable(getattr(instance, field))
               else getattr(instance, field) for field in header]
        writer.writerow(row)
    return response


export_as_csv.short_description = 'Export selected as CSV'


@admin.register(RRFeedback)
class RRFeedbackAdmin(admin.ModelAdmin):
    """Add ordering and filtering displaying this table on the admin site."""

    list_display = ('session', 'time', 'question', 'answer', 'useful')
    list_filter = ('time', 'session', 'useful')
    actions = [export_as_csv]


@admin.register(Subject)
class Subject(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('id', 'num', 'name')
    actions = [export_as_csv]


@admin.register(Student)
class Student(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('matr_num', 'name', 'mail', 'last_login')
    actions = [export_as_csv]


@admin.register(Break)
class Break(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('id', 'student', 'subject', 'time')
    list_filter = ('time', 'subject')
    actions = [export_as_csv]


@admin.register(Repetition)
class Repetition(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('id', 'student', 'subject', 'time')
    list_filter = ('time', 'subject')
    actions = [export_as_csv]


@admin.register(Question)
class Question(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('time', 'student', 'subject', 'question')
    list_filter = ('time', 'subject')
    actions = [export_as_csv]


@admin.register(Vote)
class Vote(admin.ModelAdmin):
    """Add ordering displaying this table on the admin site."""

    list_display = ('id', 'student', 'subject', 'question', 'time')
    list_filter = ('time', 'subject')
    actions = [export_as_csv]


# admin.site.register(Model) # not needed by registering as a decorator
