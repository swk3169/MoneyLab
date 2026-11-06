"""Constants for research gate report conformance (QUALITY-GATES-02 DC2, DC7, DC13).

Data only: schema identifiers, the allowed labels, field names, patterns and the fixed code -> message table.
report_conformance builds every Problem message from MESSAGES and never from input."""

REPORT_SCHEMA = "moneylab.research.gate_report/1"
PROFILE_SCHEMA = "moneylab.research.report_profile/1"
RESULT_SCHEMA = "moneylab.research.report_conformance/1"
KNOWN_REPORT_SCHEMAS = (REPORT_SCHEMA,)
KNOWN_PROFILE_SCHEMAS = (PROFILE_SCHEMA,)

LABELS = ("SUPPORTED", "WEAKENED", "INCONCLUSIVE")
INCONCLUSIVE = "INCONCLUSIVE"

# Top-level keys. A forbidden-term or type Problem names one of these as its section, never an input key.
REPORT_FIELDS = ("schema", "study_id", "evidence_grade", "sections", "hypotheses", "multiplicity")
PROFILE_FIELDS = ("schema", "study_id", "hypothesis_ids", "required_hypothesis_fields", "labels", "reason_codes",
                  "evidence_grade", "required_sections", "multiplicity", "forbidden_terms")
HYPOTHESIS_BASE_FIELDS = ("id", "label", "reason")

# Matched with re.fullmatch and re.ASCII. IDENTIFIER (DC3a) has no ".", so no decimal value can become a path.
IDENTIFIER_PATTERN = r"^[A-Za-z][A-Za-z0-9_-]{0,31}$"
LEVEL_PATTERN = r"^0\.[0-9]*[1-9]$|^1$"
TOKEN_PATTERN = r"[A-Za-z0-9_]+"
# Containers nested deeper than this, counting the report or profile dict itself as depth 1, are QG-T01 (DC12a).
MAX_DEPTH = 64

MESSAGES = {
    "QG-T01": "value is not of the required JSON data model type",
    "QG-X01": "internal error while checking; no detail is reported",
    "QG-P01": "profile is structurally invalid",
    "QG-A01": "report schema is missing",
    "QG-A02": "report schema is not a known version",
    "QG-A03": "profile schema is missing or not a known version",
    "QG-A04": "report study_id is missing or does not match the profile",
    "QG-B01": "number of hypotheses differs from the profile",
    "QG-B02": "hypothesis declared by the profile is missing from the report",
    "QG-B03": "hypothesis id is not declared by the profile",
    "QG-B04": "hypothesis id occurs more than once",
    "QG-C01": "required hypothesis field is missing",
    "QG-C02": "hypothesis label is not allowed by the profile",
    "QG-C03": "INCONCLUSIVE hypothesis has no reason",
    "QG-C04": "hypothesis reason is not allowed for its label",
    "QG-D01": "SUPPORTED multiplicity family is missing",
    "QG-D02": "SUPPORTED method is missing or differs from the profile",
    "QG-D03": "SUPPORTED family level is missing or differs from the profile",
    "QG-E01": "WEAKENED multiplicity family is missing",
    "QG-E02": "WEAKENED method is missing or differs from the profile",
    "QG-E03": "WEAKENED family level is missing or differs from the profile",
    "QG-E04": "WEAKENED per-hypothesis level is missing or differs from the profile",
    "QG-F01": "union bound is missing",
    "QG-F02": "union bound differs from the profile",
    "QG-F03": "profile family levels do not sum to its union bound",
    "QG-G01": "special-hypothesis rule or component is missing",
    "QG-G02": "special-hypothesis component level differs from the profile",
    "QG-G03": "profile special components do not sum to the WEAKENED per-hypothesis level",
    "QG-H01": "evidence grade is missing",
    "QG-H02": "evidence grade differs from the profile",
    "QG-I01": "forbidden term found",
    "QG-J01": "required report section is missing",
}
