from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Count
from apps.departments.models import Department
from apps.audit.models import log_audit

def is_admin(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profile') and user.profile.is_admin_user))

@login_required
def department_list_view(request):
    departments = Department.objects.annotate(
        members_count=Count('users', distinct=True),
        bookings_count=Count('bookings', distinct=True)
    ).order_by('name')

    return render(request, 'departments/list.html', {
        'departments': departments,
        'is_admin': is_admin(request.user)
    })

@login_required
@user_passes_test(is_admin)
def department_create_view(request):
    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        hod_name = request.POST.get('hod_name', '').strip()
        contact_email = request.POST.get('contact_email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if not code or not name:
            messages.error(request, "Department Code and Name are required.")
            return render(request, 'departments/form.html', {'action': 'Create'})

        if Department.objects.filter(code=code).exists():
            messages.error(request, f"Department code '{code}' already exists.")
            return render(request, 'departments/form.html', {'action': 'Create'})

        dept = Department.objects.create(
            code=code,
            name=name,
            hod_name=hod_name,
            contact_email=contact_email,
            phone=phone,
            is_active=True
        )

        log_audit(
            request=request,
            action='SETTINGS_UPDATE',
            model_name='Department',
            object_id=dept.id,
            updated_value=f"Created department: {dept.code} - {dept.name}"
        )

        messages.success(request, f"Department '{dept.name}' added successfully.")
        return redirect('departments:list')

    return render(request, 'departments/form.html', {'action': 'Create'})

@login_required
@user_passes_test(is_admin)
def department_edit_view(request, dept_id):
    dept = get_object_or_404(Department, id=dept_id)

    if request.method == 'POST':
        code = request.POST.get('code', '').strip().upper()
        name = request.POST.get('name', '').strip()
        dept.hod_name = request.POST.get('hod_name', '').strip()
        dept.contact_email = request.POST.get('contact_email', '').strip()
        dept.phone = request.POST.get('phone', '').strip()
        dept.is_active = 'is_active' in request.POST

        if not code or not name:
            messages.error(request, "Department Code and Name are required.")
            return render(request, 'departments/form.html', {'dept': dept, 'action': 'Edit'})

        dept.code = code
        dept.name = name
        dept.save()

        log_audit(
            request=request,
            action='SETTINGS_UPDATE',
            model_name='Department',
            object_id=dept.id,
            updated_value=f"Updated department: {dept.code}"
        )

        messages.success(request, f"Department '{dept.name}' updated successfully.")
        return redirect('departments:list')

    return render(request, 'departments/form.html', {'dept': dept, 'action': 'Edit'})
