from enum import Enum


class RoleEnum(str, Enum):
    VENDOR = "vendor"
    PROCUREMENT_OFFICER = "procurement_officer"
    REVIEWER = "reviewer"
    ADMIN = "admin"
