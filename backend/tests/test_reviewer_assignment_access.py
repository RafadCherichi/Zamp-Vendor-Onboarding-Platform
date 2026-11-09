"""A reviewer's assigned work is a permission boundary, not a UI filter."""
import secrets
from app.core.security import create_access_token
from app.models.organization import Organization
from app.models.user import User
from app.models.member import OrganisationMember
from app.models.vendor import Vendor
from app.models.application import Application
from app.models.exception import OnboardingException
from app.models.validation import ValidationRun
from app.models.notification import Notification


def test_assignment_controls_every_case_surface(client, db_session):
    db = db_session
    suffix = secrets.token_hex(4)
    org = Organization(name="Assignment isolation", slug=f"assignment-{suffix}")
    db.add(org)
    db.flush()
    users = []
    for label, role in [("first", "reviewer"), ("second", "reviewer"), ("procurement", "procurement_officer"), ("admin", "admin")]:
        user = User(email=f"{label}-{suffix}@example.com", full_name=label, hashed_password="unused")
        db.add(user)
        db.flush()
        db.add(OrganisationMember(organisation_id=org.id, user_id=user.id, role=role))
        users.append(user)
    vendor = Vendor(organisation_id=org.id, legal_name="Scope supplier", constitution="PROPRIETORSHIP")
    db.add(vendor)
    db.flush()
    cases, issues, runs = [], [], []
    for index, owner in enumerate([users[0].id, users[1].id, None]):
        case = Application(organisation_id=org.id, vendor_id=vendor.id, reference_number=f"SCOPE-{suffix}-{index}", legal_name=f"Supplier {index}", status="UNDER_REVIEW", assigned_reviewer_id=owner)
        db.add(case)
        db.flush()
        issue = OnboardingException(organisation_id=org.id, application_id=case.id, vendor_id=vendor.id, reference_number=f"ISSUE-{suffix}-{index}", title=f"Question {index}", description="Scope test", category="MISSING_INFORMATION", severity="HIGH", status="OPEN", created_by_role="SYSTEM")
        run = ValidationRun(organisation_id=org.id, application_id=case.id, status="COMPLETED", is_current=True)
        db.add_all([issue, run])
        db.flush()
        for entity_type, entity_id in [("APPLICATION", case.id), ("EXCEPTION", issue.id)]:
            db.add(Notification(organisation_id=org.id, recipient_user_id=users[0].id, title="Case update", message="Scope test", notification_type="STATUS_CHANGE", entity_type=entity_type, entity_id=entity_id, is_read=False))
        cases.append(case)
        issues.append(issue)
        runs.append(run)
    db.commit()
    def headers(user):
        return {"Authorization": "Bearer " + create_access_token({"sub": user.id, "org_id": org.id})}
    first = headers(users[0])
    base = "/api/applications"
    # Attempts to request another reviewer or unassigned records cannot expand scope.
    for query in ["", f"?assigned_reviewer_id={users[1].id}", "?unassigned_only=true", "?status=UNASSIGNED"]:
        response = client.get(base + "/queue" + query, headers=first)
        assert response.status_code == 200
        ids = {item["id"] for item in response.json()["items"]}
        assert ids <= {cases[0].id}
    assert {item["id"] for item in client.get(base + "/", headers=first).json()} == {cases[0].id}
    metrics = client.get(base + "/dashboard/metrics", headers=first).json()
    assert metrics["total_applications"] == 1
    assert metrics["open_exceptions_count"] == 1
    assert {item["application_id"] for item in client.get(base + "/runs", headers=first).json()} == {cases[0].id}
    assert {item["id"] for item in client.get("/api/exceptions/", headers=first).json()} == {issues[0].id}
    assert client.get("/api/notifications/count", headers=first).json()["unread_count"] == 2
    assert len(client.get("/api/notifications/", headers=first).json()) == 2
    for case, issue, run in zip(cases[1:], issues[1:], runs[1:]):
        for path in [f"{base}/{case.id}", f"{base}/{case.id}/details", f"{base}/{case.id}/validation", f"{base}/{case.id}/verifications", f"{base}/{case.id}/duplicates", f"{base}/{case.id}/audit-trail", f"{base}/runs/{run.id}", f"/api/exceptions/{issue.id}", f"{base}/{case.id}/documents/PAN_PROOF/processing"]:
            assert client.get(path, headers=first).status_code == 404, path
        assert client.post(f"/api/exceptions/{issue.id}/comments", headers=first, json={"message": "Unauthorised note", "is_internal": True}).status_code == 404
    assert client.get(f"{base}/{cases[0].id}/details", headers=first).status_code == 200
    for user in users[2:]:
        assert client.get(base + "/queue", headers=headers(user)).json()["total"] == 3
        assert client.get(f"{base}/{cases[2].id}/details", headers=headers(user)).status_code == 200
    # Assignment changes take effect on the next request, including old notices.
    cases[0].assigned_reviewer_id = users[1].id
    db.commit()
    assert client.get(f"{base}/{cases[0].id}/details", headers=first).status_code == 404
    assert client.get(base + "/dashboard/metrics", headers=first).json()["total_applications"] == 0
    assert client.get("/api/notifications/count", headers=first).json()["unread_count"] == 0
    assert client.get(f"{base}/{cases[0].id}/details", headers=headers(users[1])).status_code == 200
