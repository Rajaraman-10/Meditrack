# MediTrack Security Review

**Review date:** 2026-10-07  
**Scope:** Authentication, role authorization, appointment and clinical workflows,
document access, billing, notifications, dashboards, and audit logging.  
**Result:** One medium-severity finding, now remediated.

## Findings

### MEDIUM — Patient registration does not verify email ownership

**Locations:** [RegistrationView](./backend/apps/accounts/views.py#L22) and
[RegistrationSerializer](./backend/apps/accounts/serializers.py#L41)

The public registration endpoint creates an active patient account and profile
immediately, without confirming that the registrant controls the submitted email
address. An attacker who registers first using another person's unregistered email
can claim that account identity. If clinic staff later associate appointments or
clinical records with the profile selected by that email, the registrant can access
those records through patient-scoped APIs.

This does not let an attacker take over an already registered account. The risk is
claiming an unregistered identity before clinic records are associated with it.

**Confidence:** 8/10  
**Recommended remediation:** Require email ownership verification before enabling
patient access, or use a trusted invitation/account-linking process before attaching
clinical records to a self-registered account.

**Current status:** Email verification has been disabled at the project owner's
request. Patient registration creates an immediately usable account, and the app no
longer confirms ownership of the submitted email address. The original risk above
therefore remains. Before using real patient data, restore email verification or use
a trusted invitation/account-linking process before attaching clinical records.

## Review notes

- The fix has been implemented and locally validated; this review document was not
  independently re-reviewed after the change.
- The review did not identify additional reportable exploitable vulnerabilities in
  the reviewed scope.
- Re-run the review after changing registration and before deploying with real
  patient data.
