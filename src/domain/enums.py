from enum import StrEnum


class ImagingModality(StrEnum):
    MRI = "mri"
    CT = "ct"
    XRAY = "xray"
    ULTRASOUND = "ultrasound"
    PET = "pet"
    NM = "nuclear_medicine"
    OTHER = "other"


class BodyRegion(StrEnum):
    KNEE = "knee"
    LUMBAR_SPINE = "lumbar_spine"
    CERVICAL_SPINE = "cervical_spine"
    THORACIC_SPINE = "thoracic_spine"
    SHOULDER = "shoulder"
    HIP = "hip"
    ABDOMEN = "abdomen"
    PELVIS = "pelvis"
    HEAD = "head"
    CHEST = "chest"
    OTHER = "other"


class Laterality(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    BILATERAL = "bilateral"
    MIDLINE = "midline"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class PayerId(StrEnum):
    AETNA = "aetna"
    CIGNA = "cigna"
    MEDADV = "medadv"
    OTHER = "other"


class ClinicalStatus(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class CriterionStatus(StrEnum):
    MET = "met"
    NOT_MET = "not_met"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class RecommendationSignal(StrEnum):
    LIKELY_APPROVE = "likely_approve"
    LIKELY_DENY = "likely_deny"
    NEEDS_MORE_INFO = "needs_more_info"
    UNCLEAR = "unclear"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    READY_FOR_SUBMISSION = "ready_for_submission"
    BLOCKED = "blocked"


class OrderingSpecialty(StrEnum):
    PRIMARY_CARE = "primary_care"
    ORTHOPEDICS = "orthopedics"
    SPORTS_MEDICINE = "sports_medicine"
    PHYSICAL_MEDICINE = "physical_medicine"
    EMERGENCY_MEDICINE = "emergency_medicine"
    OTHER = "other"
