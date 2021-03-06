import calendar

from django.contrib import messages
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.views.decorators.http import require_http_methods as alowed

from zk.exception import ZKError
from zkcluster.models import Terminal, Attendance

from driji.models import User
from driji.forms import LoginForm, ScanTerminalForm, AddTerminalForm, EditTerminalForm, StudentForm

@alowed(['GET'])
@login_required
def index(request):
    return render(request, 'index.html')

@alowed(['GET', 'POST'])
def login_view(request):
    user = request.user
    if user.is_authenticated():
        next_url = request.GET.get('next')
        if next_url:
            return redirect(next_url)
        return redirect('index')

    form = LoginForm(request.POST or None)
    if request.POST and form.is_valid():
        authenticate_user = form.get_authenticate_user()
        login(request, authenticate_user)
        messages.add_message(request, messages.SUCCESS, "Welcome {} !".format(request.user.username))
        return redirect(request.META.get('HTTP_REFERER'))

    return render(request, 'login.html', {'form': form})

@alowed(['GET'])
def logout_views(request):
    if not request.user.is_authenticated():
        raise Http404()
    logout(request)
    return redirect('index')

@alowed(['GET'])
@login_required
def terminal(request):
    terminals = Terminal.objects.all()
    data = {
        'terminals': terminals
    }
    return render(request, 'terminal.html', data)

@alowed(['POST'])
@login_required
def terminal_add(request):
    connected = request.GET.get('connected')
    if connected:
        form = AddTerminalForm(request.POST or None, {'validate_name': True})
        if form.is_valid():
            try:
                form.save()
                messages.add_message(request, messages.SUCCESS, _('Successfully registering a new terminal'))
                return redirect('terminal')
            except ZKError, e:
                messages.add_message(request, messages.ERROR, str(e))
    else:
        form = AddTerminalForm(request.POST or None)

    data = {
        'form': form
    }
    return render(request, 'terminal_add.html', data)

@alowed(['GET', 'POST'])
@login_required
def terminal_scan(request):
    form = ScanTerminalForm(request.POST or None)
    if request.POST and form.is_valid():
        ip = form.cleaned_data['ip']
        port = form.cleaned_data['port']

        terminal = Terminal(
            ip=ip,
            port=port
        )
        try:
            terminal.zk_connect()
            sn = terminal.zk_getserialnumber()

            # manipulate the POST information
            mutable = request.POST._mutable
            request.POST._mutable = True
            request.POST['serialnumber'] = sn
            request.POST._mutable = mutable

            terminal.zk_disconnect()
            return terminal_add(request)
        except ZKError, e:
            messages.add_message(request, messages.ERROR, str(e))

    data = {
        'form': form
    }

    return render(request, 'terminal_scan.html', data)

@alowed(['GET', 'POST'])
@login_required
def terminal_edit(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    form = EditTerminalForm(request.POST or None, instance=terminal)
    if request.POST and form.is_valid():
        try:
            form.save()
            messages.add_message(request, messages.SUCCESS, _('Successfully updating a terminal'))
        except ZKError, e:
            messages.add_message(request, messages.ERROR, str(e))
        return redirect('terminal')
    data = {
        'terminal': terminal,
        'form': form
    }
    return render(request, 'terminal_edit.html', data)

@alowed(['POST'])
@login_required
def terminal_restart(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    try:
        terminal.zk_connect()
        terminal.zk_restart()
        messages.add_message(request, messages.SUCCESS, _('%(terminal)s has restarted') % {'terminal': terminal})
    except ZKError, e:
        messages.add_message(request, messages.ERROR, str(e))

    return redirect('terminal')

@alowed(['POST'])
@login_required
def terminal_poweroff(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    try:
        terminal.zk_connect()
        terminal.zk_poweroff()
        terminal.zk_disconnect()
        messages.add_message(request, messages.SUCCESS, _('%(terminal)s has shutdown') % {'terminal': terminal})
    except ZKError, e:
        messages.add_message(request, messages.ERROR, str(e))

    return redirect('terminal')

@alowed(['POST'])
@login_required
def terminal_voice(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    try:
        terminal.zk_connect()
        terminal.zk_voice()
        terminal.zk_disconnect()
    except ZKError, e:
        messages.add_message(request, messages.ERROR, str(e))

    return redirect('terminal')

@alowed(['POST'])
@login_required
def terminal_format(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    try:
        terminal.format()
        messages.add_message(request, messages.SUCCESS, _('%(terminal)s has formated') % {'terminal': terminal})
    except ZKError, e:
        messages.add_message(request, messages.ERROR, str(e))

    return redirect('terminal')

@alowed(['POST'])
@login_required
def terminal_delete(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    try:
        terminal.delete()
        messages.add_message(request, messages.SUCCESS, _('%(terminal)s has deleted') % {'terminal': terminal})
    except ZKError, e:
        messages.add_message(request, messages.ERROR, str(e))

    return redirect('terminal')

@alowed(['GET', 'POST'])
@login_required
def terminal_action(request, action, terminal_id):
    if action == 'edit':
        return terminal_edit(request, terminal_id)
    elif action == 'restart':
        return terminal_restart(request, terminal_id)
    elif action == 'poweroff':
        return terminal_poweroff(request, terminal_id)
    elif action == 'voice':
        return terminal_voice(request, terminal_id)
    elif action == 'format':
        return terminal_format(request, terminal_id)
    elif action == 'delete':
        return terminal_delete(request, terminal_id)
    else:
        raise Http404("Action doest not allowed")

@alowed(['GET'])
@login_required
def terminal_detail(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    users = terminal.user_set.all()

    # generate days number
    days = []
    now = timezone.now()
    cal = calendar.monthrange(now.year, now.month)
    for d in range (cal[0]-1, cal[1]+1):
        days.append(d)

    data = {
        'terminal': terminal,
        'users': users,
        'days': days
    }
    return render(request, 'terminal_detail.html', data)

@alowed(['GET'])
@login_required
def student(request):
    students = User.objects.filter(user_type=User.USER_STUDENT)
    data = {
        'students': students
    }
    return render(request, 'student.html', data)

@alowed(['GET', 'POST'])
@login_required
def student_add(request):
    form = StudentForm(request.POST or None)
    if request.POST and form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS, _('Successfully registering a new student'))
        return redirect('student')
    data = {
        'form': form
    }
    return render(request, 'student_add.html', data)

@alowed(['GET'])
@login_required
def attendance(request, terminal_id):
    terminal = get_object_or_404(Terminal, pk=terminal_id)
    users = terminal.user_set.all()

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    midnight = (today + timezone.timedelta(days=1))
    first_date = timezone.make_aware(timezone.datetime(today.year, today.month, 1))

    attendances = terminal.attendances.filter(
        timestamp__range=(first_date, midnight),
        summary__isnull=False
    ).values(
        'summary__driji_user_id',
        'summary__date',
        'summary__status'
    )
    summary = {}
    for att in attendances:
        key = str(att['summary__driji_user_id'])
        if not summary.get(key):
            summary[key] = {}
        key_day = att['summary__date'].strftime('%Y%m%d')
        summary[key][key_day] = att['summary__status']

    # generate days number
    days = []
    cal = calendar.monthrange(today.year, today.month)
    for d in range (cal[0]-1, cal[1]+1):
        date = today.replace(day=d).date()
        days.append(date)
        if date < midnight.date():
            for user in users:
                key = str(user.id)
                day_key = date.strftime('%Y%m%d')
                if date.isoweekday() != 7:
                    if summary.get(key):
                        if not summary.get(key).get(date.strftime('%Y%m%d')):
                            summary[key][day_key] = 'a'
                    else:
                        summary[key] = {}
                        summary[key][day_key] = 'a'
                else:
                    if summary.get(key):
                        if not summary.get(key).get(date.strftime('%Y%m%d')):
                            summary[key][day_key] = 'w'
                    else:
                        summary[key] = {}
                        summary[key][day_key] = 'w'

    data = {
        'terminal': terminal,
        'users': users,
        'days': days,
        'today': today,
        'summary': summary
    }
    return render(request, 'attendance.html', data)

# @alowed(['GET'])
# @login_required
# def settings_grade(request):
#     grade_list = Grade.objects.all()
#     data = {
#         'grade_list': grade_list
#     }
#     return render(request, 'settings_grade.html', data)
#
# @alowed(['GET', 'POST'])
# @login_required
# def settings_grade_add(request):
#     form = GradeForm(request.POST or None)
#     if request.POST and form.is_valid():
#         form.save()
#         messages.add_message(request, messages.SUCCESS, _('Successfully adding a new grade'))
#         return redirect('settings_grade')
#     data = {
#         'form': form
#     }
#     return render(request, 'settings_grade_add.html', data)
