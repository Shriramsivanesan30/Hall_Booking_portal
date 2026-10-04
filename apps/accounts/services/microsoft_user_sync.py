"""
Microsoft User Synchronization & Department Mapping Service.

Takes the normalized Microsoft Graph profile from MicrosoftGraphService and
synchronizes it with existing Django User and UserProfile models.

Enforces:
- Strict matching priority: Microsoft Object ID (oid) first, normalized email/UPN fallback second.
- Account collision and conflict protection (never overwrites conflicting Microsoft IDs).
- Complete role, approval, password, and username immutability.
- Safe department resolution (no inference or automatic creation).
- Atomic database transactions.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User
from apps.accounts.models import UserProfile
from apps.departments.models import Department

logger = logging.getLogger(__name__)


class UserSyncError(Exception):
    """Raised when user synchronization fails due to database or validation errors."""
    pass


@dataclass
class SyncResult:
    """
    Structured outcome of a Microsoft profile synchronization attempt.
    """
    status: str  # 'linked', 'existing', 'user_not_found', 'identity_conflict', 'invalid_profile'
    user: Optional[User] = None
    profile: Optional[UserProfile] = None
    department_status: Optional[str] = None  # 'matched', 'department_none', 'department_not_found'
    message: str = ''

    @property
    def is_success(self) -> bool:
        return self.status in ('linked', 'existing')


class MicrosoftUserSyncService:
    """
    Isolated service for matching and synchronizing Microsoft Graph identities with Django users.
    """

    def sync_user(self, profile_data: Dict[str, Any]) -> SyncResult:
        """
        Synchronize a verified Microsoft Graph profile with the existing Django database.

        Args:
            profile_data: Normalized dictionary produced by MicrosoftGraphService.

        Returns:
            SyncResult with status, user, profile, and department status.
        """
        if not profile_data or not isinstance(profile_data, dict):
            logger.warning("Microsoft user sync received invalid profile data.")
            return SyncResult(status='invalid_profile', message='Profile data is empty or invalid.')

        ms_uid = str(profile_data.get('microsoft_user_id') or '').strip()
        raw_email = str(profile_data.get('email') or '').strip().lower()
        raw_upn = str(profile_data.get('user_principal_name') or '').strip().lower()

        if not ms_uid:
            logger.error("Microsoft profile is missing required 'microsoft_user_id' (oid).")
            return SyncResult(status='invalid_profile', message="Missing Microsoft Object ID ('microsoft_user_id').")

        # ── 1. Priority 1: Match by Microsoft Object ID ──────────────────────
        profile_by_msid = UserProfile.objects.select_related('user', 'department').filter(
            microsoft_user_id=ms_uid
        ).first()

        if profile_by_msid:
            # Collision Check: Does incoming email/UPN belong to a DIFFERENT existing user in Django?
            other_user = None
            for ident in [raw_email, raw_upn]:
                if ident:
                    other_user = (
                        User.objects.filter(username__iexact=ident).exclude(id=profile_by_msid.user_id).first()
                        or User.objects.filter(email__iexact=ident).exclude(id=profile_by_msid.user_id).first()
                    )
                    if other_user:
                        break

            if other_user:
                logger.warning(
                    "Identity conflict: Microsoft ID %s belongs to %s, but incoming profile email '%s' matches different user %s.",
                    ms_uid, profile_by_msid.user.username, raw_email, other_user.username
                )
                return SyncResult(
                    status='identity_conflict',
                    user=profile_by_msid.user,
                    profile=profile_by_msid,
                    message='Identity conflict: Microsoft ID is already linked to another user account.'
                )

            user = profile_by_msid.user
            logger.info("Matched existing user by Microsoft Object ID: user_id=%s, ms_uid=%s", user.id, ms_uid)

            # Synchronize safe non-privileged details atomically
            with transaction.atomic():
                dept_status = self._sync_department(profile_by_msid, profile_data.get('department'))
                # Ensure UPN is populated if not yet stored
                if raw_upn and not profile_by_msid.user_principal_name:
                    profile_by_msid.user_principal_name = raw_upn
                    profile_by_msid.save(update_fields=['user_principal_name'])

            return SyncResult(
                status='existing',
                user=user,
                profile=profile_by_msid,
                department_status=dept_status,
                message='User successfully matched by Microsoft Object ID.'
            )

        # ── 2. Priority 2: Fallback Match by Normalized Email / UPN ──────────
        user_by_email = None
        search_identifiers = [id_str for id_str in [raw_email, raw_upn] if id_str]

        for ident in search_identifiers:
            user_by_email = (
                User.objects.filter(username__iexact=ident).first()
                or User.objects.filter(email__iexact=ident).first()
            )
            if user_by_email:
                break

        if user_by_email:
            # Check for profile
            profile, _ = UserProfile.objects.get_or_create(user=user_by_email)

            # Identity Conflict Check 1: Does this user already have a DIFFERENT Microsoft ID?
            if profile.microsoft_user_id and profile.microsoft_user_id != ms_uid:
                logger.warning(
                    "Identity conflict for user %s: profile has ms_uid=%s but incoming is %s",
                    user_by_email.username, profile.microsoft_user_id, ms_uid
                )
                return SyncResult(
                    status='identity_conflict',
                    user=user_by_email,
                    profile=profile,
                    message='Identity conflict: Account is already linked to a different Microsoft identity.'
                )

            # Identity Conflict Check 2: Is incoming ms_uid already linked to another user?
            other_profile = UserProfile.objects.filter(microsoft_user_id=ms_uid).exclude(id=profile.id).first()
            if other_profile:
                logger.warning(
                    "Collision: Microsoft ID %s is already assigned to user %s. Cannot link to %s.",
                    ms_uid, other_profile.user.username, user_by_email.username
                )
                return SyncResult(
                    status='identity_conflict',
                    user=user_by_email,
                    profile=profile,
                    message='Identity conflict: Microsoft identity is already associated with another account.'
                )

            # Link Microsoft Identity atomically
            with transaction.atomic():
                profile.microsoft_user_id = ms_uid
                if raw_upn:
                    profile.user_principal_name = raw_upn
                elif raw_email:
                    profile.user_principal_name = raw_email

                profile.auth_provider = 'microsoft'
                dept_status = self._sync_department(profile, profile_data.get('department'))
                profile.save()

            logger.info("Successfully linked Microsoft ID %s to existing user %s", ms_uid, user_by_email.username)
            return SyncResult(
                status='linked',
                user=user_by_email,
                profile=profile,
                department_status=dept_status,
                message='Microsoft identity successfully linked to existing user.'
            )

        # ── 3. Priority 3: No existing user found ────────────────────────────
        logger.warning("Microsoft authentication succeeded but no matching Django user found for email=%s, ms_uid=%s", raw_email, ms_uid)
        return SyncResult(
            status='user_not_found',
            user=None,
            profile=None,
            department_status=None,
            message='No existing institution account matches this Microsoft identity.'
        )

    def _sync_department(self, profile: UserProfile, raw_department: Optional[str]) -> str:
        """
        Safely maps a department string from Microsoft Graph to the Django Department model.

        Returns:
            'matched' if existing department was matched and assigned,
            'department_none' if Graph returned null/empty (profile department left unchanged),
            'department_not_found' if Graph returned a name that does not exist in DB (no department created).
        """
        if not raw_department or not isinstance(raw_department, str) or not raw_department.strip():
            # If Graph department is None or empty, do NOT guess or infer. Leave existing department intact.
            return 'department_none'

        cleaned_dept_name = raw_department.strip()

        # Attempt safe match by name (e.g. "Information Technology") or code (e.g. "IT")
        dept = (
            Department.objects.filter(name__iexact=cleaned_dept_name).first()
            or Department.objects.filter(code__iexact=cleaned_dept_name).first()
        )

        if dept:
            profile.department = dept
            profile.save(update_fields=['department'])
            logger.info("Mapped department '%s' to Department ID %s (%s)", cleaned_dept_name, dept.id, dept.code)
            return 'matched'

        logger.warning(
            "Microsoft Graph department '%s' not found in Department master. No department was modified.",
            cleaned_dept_name
        )
        return 'department_not_found'
