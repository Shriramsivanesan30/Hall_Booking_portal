from django.utils import timezone
from apps.bookings.models import Booking
from apps.approvals.models import ApprovalHistory
from apps.notifications.services import send_booking_notification
from apps.audit.models import log_audit

def process_approval_action(request, booking, action, remarks='', new_allocated_hall_id=None):
    """
    Executes a multi-level approval step.
    Actions supported:
    - 'APPROVE': moves to next stage or confirms booking
    - 'REJECT': marks booking as rejected with required reason
    - 'REQUEST_MODIFICATION': returns booking to draft/submitted state for faculty revision
    """
    user = request.user
    prev_status = booking.status
    prev_stage = booking.current_approval_stage

    # 1. Rejection
    if action == 'REJECT':
        if not remarks.strip():
            return False, "Rejection requires a documented reason."

        booking.status = Booking.STATUS_REJECTED
        booking.current_approval_stage = Booking.STAGE_REJECTED
        booking.rejection_reason = remarks
        booking.rejected_by = user
        booking.save()

        # Record Approval History
        ApprovalHistory.objects.create(
            booking=booking,
            stage=prev_stage,
            action=ApprovalHistory.ACTION_HOD_REJECTED if prev_stage == Booking.STAGE_HOD else (
                ApprovalHistory.ACTION_COORDINATOR_REJECTED if prev_stage == Booking.STAGE_COORDINATOR else ApprovalHistory.ACTION_PRINCIPAL_REJECTED
            ),
            user=user,
            previous_status=prev_status,
            new_status=booking.status,
            remarks=remarks
        )

        # Audit Log
        log_audit(
            request=request,
            action='BOOKING_REJECT',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            previous_value=f"Status: {prev_status}, Stage: {prev_stage}",
            updated_value=f"Status: {booking.status}, Remarks: {remarks}"
        )

        # Notify requester
        send_booking_notification(
            booking=booking,
            notification_type='REJECTION',
            title=f"Booking Request Rejected – {booking.booking_id}",
            recipient=booking.user,
            remarks=remarks
        )

        return True, "Booking request has been rejected."

    # 2. Request Modification
    if action == 'REQUEST_MODIFICATION':
        if not remarks.strip():
            return False, "Please provide feedback or required modifications in the remarks."

        booking.status = Booking.STATUS_DRAFT
        booking.current_approval_stage = Booking.STAGE_DRAFT
        booking.save()

        ApprovalHistory.objects.create(
            booking=booking,
            stage=prev_stage,
            action=ApprovalHistory.ACTION_MODIFICATION_REQUESTED,
            user=user,
            previous_status=prev_status,
            new_status=booking.status,
            remarks=remarks
        )

        log_audit(
            request=request,
            action='BOOKING_UPDATE',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            previous_value=prev_status,
            updated_value=booking.status
        )

        send_booking_notification(
            booking=booking,
            notification_type='SYSTEM',
            title=f"Modifications Requested – {booking.booking_id}",
            recipient=booking.user,
            remarks=remarks
        )

        return True, "Requested modifications have been sent to the requester."

    # 3. Approval progression
    if action == 'APPROVE':
        if prev_stage == Booking.STAGE_HOD:
            # HOD approved -> move to Coordinator
            booking.status = Booking.STATUS_HOD_APPROVED
            booking.current_approval_stage = Booking.STAGE_COORDINATOR
            history_action = ApprovalHistory.ACTION_HOD_APPROVED
            stage_name = "HOD Verification"
            notif_title = f"HOD Approved – {booking.booking_id} forwarded to Coordinator"

        elif prev_stage == Booking.STAGE_COORDINATOR:
            # Coordinator approved -> move to Principal
            booking.status = Booking.STATUS_COORDINATOR_APPROVED
            booking.current_approval_stage = Booking.STAGE_PRINCIPAL
            history_action = ApprovalHistory.ACTION_COORDINATOR_APPROVED
            stage_name = "Coordinator Verification"
            notif_title = f"Coordinator Approved – {booking.booking_id} forwarded to Principal"

            if new_allocated_hall_id:
                from apps.halls.models import Hall
                try:
                    booking.allocated_hall = Hall.objects.get(id=new_allocated_hall_id)
                except Hall.DoesNotExist:
                    pass

        elif prev_stage == Booking.STAGE_PRINCIPAL:
            # Principal approved -> Final Confirmed!
            booking.status = Booking.STATUS_APPROVED
            booking.current_approval_stage = Booking.STAGE_COMPLETED
            history_action = ApprovalHistory.ACTION_PRINCIPAL_APPROVED
            stage_name = "Principal Final Approval"
            notif_title = f"Booking Confirmed – {booking.booking_id}"

        elif user.profile.is_admin_user:
            # Admin can confirm directly
            booking.status = Booking.STATUS_APPROVED
            booking.current_approval_stage = Booking.STAGE_COMPLETED
            history_action = ApprovalHistory.ACTION_PRINCIPAL_APPROVED
            stage_name = "Administrator Direct Approval"
            notif_title = f"Booking Confirmed by Admin – {booking.booking_id}"

        else:
            return False, "Invalid stage transition for your role."

        booking.save()

        ApprovalHistory.objects.create(
            booking=booking,
            stage=stage_name,
            action=history_action,
            user=user,
            previous_status=prev_status,
            new_status=booking.status,
            remarks=remarks
        )

        log_audit(
            request=request,
            action='BOOKING_APPROVE',
            booking_id=booking.booking_id,
            model_name='Booking',
            object_id=booking.id,
            previous_value=f"Status: {prev_status}, Stage: {prev_stage}",
            updated_value=f"Status: {booking.status}, Stage: {booking.current_approval_stage}"
        )

        send_booking_notification(
            booking=booking,
            notification_type='APPROVAL' if booking.status != Booking.STATUS_APPROVED else 'FINAL_APPROVAL',
            title=notif_title,
            recipient=booking.user,
            remarks=remarks
        )

        return True, "Booking approved successfully."

    return False, "Unknown action."
