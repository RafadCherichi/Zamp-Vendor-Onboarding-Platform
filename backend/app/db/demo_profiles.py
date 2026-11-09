"""Stable identities for the synthetic practice account; never inferred from form text."""
def demo_profile_id(application):
    if (application.id == "app-apex-base-01" and application.vendor_id == "vnd-apex-base-01" and application.created_by_user_id == "usr-vendor-apex-01" and application.vendor.created_by_user_id == "usr-vendor-apex-01"):
        return "apex-components"
    return None


def initial_demo_identity(application):
    if demo_profile_id(application):
        return {"legal_name": "Apex Components & Fasteners", "trade_name": "Apex Fasteners", "constitution": "PROPRIETORSHIP", "pan": None}
    return {"legal_name": application.vendor.legal_name, "trade_name": application.vendor.trade_name, "constitution": application.vendor.constitution, "pan": application.vendor.pan}
