"""Structural conformance of a research gate report to a preregistration profile (QUALITY-GATES-02).

check_report(report, profile) compares an in-memory report dict with a profile dict and returns a Result of
sorted, de-duplicated Problems. A PASS means structural conformance only: it does not check that any value was
computed as the preregistration prescribes, or that any label is right (DC14).

Nothing is repaired, defaulted or inferred, and the inputs are never modified. Inputs must be the JSON data model:
exact dict with str keys, list, str, int, float, bool, None. Anything else is QG-T01 and none of its methods is
called; dicts are only read through str-keyed copies, so no foreign __eq__ or __hash__ runs during a lookup.
Messages come only from report_schema.MESSAGES, and field paths only from schema names, profile identifiers that
passed DC3a and integer indices, so no report value reaches the output. No files, network, subprocess or logging."""

import json
import re
from dataclasses import dataclass
from decimal import Context, Decimal, Inexact
from typing import Any

from moneylab.research.report_schema import (
    HYPOTHESIS_BASE_FIELDS,
    IDENTIFIER_PATTERN,
    INCONCLUSIVE,
    KNOWN_PROFILE_SCHEMAS,
    KNOWN_REPORT_SCHEMAS,
    LABELS,
    LEVEL_PATTERN,
    MAX_DEPTH,
    MESSAGES,
    PROFILE_FIELDS,
    REPORT_FIELDS,
    RESULT_SCHEMA,
    TOKEN_PATTERN,
)

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN, re.ASCII)
_LEVEL = re.compile(LEVEL_PATTERN, re.ASCII)
_TOKEN = re.compile(TOKEN_PATTERN, re.ASCII)
_LEAF_TYPES = (str, int, float, bool, type(None))
_MISSING: Any = object()


@dataclass(frozen=True, order=True)
class Problem:
    code: str
    where: str
    message: str


@dataclass(frozen=True)
class Result:
    problems: tuple[Problem, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "problems", tuple(sorted(set(self.problems))))

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def exit_code(self) -> int:
        return 0 if self.ok else 1

    def to_dict(self) -> dict[str, Any]:
        return {"schema": RESULT_SCHEMA, "ok": self.ok, "exit_code": self.exit_code,
                "problems": [{"code": p.code, "where": p.where, "message": p.message} for p in self.problems]}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False) + "\n"


@dataclass(frozen=True)
class _Profile:
    study_id: str
    hypothesis_ids: tuple[str, ...]
    required_fields: tuple[str, ...]
    labels: tuple[str, ...]
    reason_codes: tuple[str, ...]
    evidence_grade: str
    sections: tuple[str, ...]
    supported: tuple[str, str]                # method, fwer
    weakened: tuple[str, str, str]            # method, fwer, per_hypothesis
    union_bound: str
    special: tuple[tuple[str, tuple[tuple[str, str], ...]], ...]   # (hypothesis id, ((component, level), ...))
    forbidden_terms: tuple[str, ...]


def _problem(code: str, where: str) -> Problem:
    return Problem(code, where, MESSAGES[code])


def _view(obj: Any) -> dict[str, Any] | None:
    """A str-keyed copy of an exact dict (None for anything else); non-str keys are reported by _walk."""
    if type(obj) is not dict:
        return None
    return {key: value for key, value in obj.items() if type(key) is str}


def _is_leaf(obj: Any) -> bool:
    kind = type(obj)
    return any(kind is leaf for leaf in _LEAF_TYPES)


def _is_level(value: Any) -> bool:
    return type(value) is str and _LEVEL.fullmatch(value) is not None


def _is_identifier(value: Any) -> bool:
    return type(value) is str and _IDENTIFIER.fullmatch(value) is not None


def _section(key: Any, known: tuple[str, ...], base: str) -> str:
    if type(key) is str and key in known:
        return key if base == "report" else f"{base}.{key}"
    return base


def _walk(root: dict[Any, Any], known: tuple[str, ...], base: str, terms: tuple[str, ...]) -> list[Problem]:
    """Iterative scan of a whole input: JSON data model (DC10), forbidden terms (DC12), cycles and depth (DC12a).

    A container already on the current path (the root always is) is a cycle: QG-T01 and the branch stops. A shared
    reference that is not on the path is walked again, so the result equals a walk of the fully copied tree (what a
    JSON round trip gives). Each (id, section, depth) is entered at most once: the Problems found below a container
    depend only on those three, so a repeat adds nothing and shared DAGs stay linear instead of exponential."""
    problems: set[Problem] = set()
    folded = [term.casefold() for term in terms]

    def scan(text: str, section: str) -> None:
        for token in _TOKEN.findall(text):
            token = token.casefold()
            for index, term in enumerate(folded):
                if token == term:
                    problems.add(_problem("QG-I01", f"{section}:forbidden_terms[{index}]"))

    exit_marker = object()   # (exit_marker, id, section) closes a container: its id leaves the current path
    active = {id(root)}
    entered: set[tuple[int, str, int]] = set()
    stack: list[tuple[Any, int, str]] = []
    for key, value in root.items():
        section = _section(key, known, base)
        if type(key) is str:
            scan(key, section)
        else:
            problems.add(_problem("QG-T01", base))
        stack.append((value, 2, section))
    while stack:
        obj, depth, section = stack.pop()
        if obj is exit_marker:
            active.discard(depth)
            continue
        kind = type(obj)
        if kind is dict or kind is list:
            ident = id(obj)
            if ident in active or depth > MAX_DEPTH:
                problems.add(_problem("QG-T01", section))
                continue
            mark = (ident, section, depth)
            if mark in entered:
                continue
            entered.add(mark)
            active.add(ident)
            stack.append((exit_marker, ident, section))
            if kind is dict:
                for key, value in obj.items():
                    if type(key) is str:
                        scan(key, section)
                    else:
                        problems.add(_problem("QG-T01", section))
                    stack.append((value, depth + 1, section))
            else:
                stack.extend((value, depth + 1, section) for value in obj)
        elif kind is str:
            scan(obj, section)
        elif not _is_leaf(obj):
            problems.add(_problem("QG-T01", section))
    return sorted(problems)


def _identifier_list(view: dict[str, Any], key: str, out: list[Problem], *, nonempty: bool = False,
                     unique: bool = False) -> tuple[str, ...]:
    where = f"profile.{key}"
    value = view.get(key, _MISSING)
    if value is _MISSING:
        out.append(_problem("QG-P01", where))
        return ()
    if type(value) is not list:
        out.append(_problem("QG-T01", where))
        return ()
    if nonempty and not value:
        out.append(_problem("QG-P01", where))
    items: list[str] = []
    for index, item in enumerate(value):
        if type(item) is not str:
            out.append(_problem("QG-T01", f"{where}[{index}]"))
        elif not _is_identifier(item) or (unique and item in items):
            out.append(_problem("QG-P01", f"{where}[{index}]"))
        else:
            items.append(item)
    return tuple(items)


def _profile_level(view: dict[str, Any] | None, key: str, where: str, out: list[Problem]) -> str:
    value = _MISSING if view is None else view.get(key, _MISSING)
    if value is _MISSING:
        out.append(_problem("QG-P01", where))
        return ""
    if not _is_level(value):
        out.append(_problem("QG-T01", where))
        return ""
    return str(value)


def _profile_text(view: dict[str, Any] | None, key: str, where: str, out: list[Problem]) -> str:
    value = _MISSING if view is None else view.get(key, _MISSING)
    if value is _MISSING:
        out.append(_problem("QG-P01", where))
        return ""
    if type(value) is not str:
        out.append(_problem("QG-T01", where))
        return ""
    if not value:
        out.append(_problem("QG-P01", where))
    return str(value)


def _profile_family(mult: dict[str, Any], name: str, keys: tuple[str, ...], out: list[Problem]) -> list[str]:
    where = f"profile.multiplicity.{name}"
    family = mult.get(name, _MISSING)
    if family is _MISSING:
        out.append(_problem("QG-P01", where))
        return [""] * (1 + len(keys))
    view = _view(family)
    if view is None:
        out.append(_problem("QG-T01", where))
        return [""] * (1 + len(keys))
    return [_profile_text(view, "method", f"{where}.method", out)] + [
        _profile_level(view, key, f"{where}.{key}", out) for key in keys]


def _profile_special(mult: dict[str, Any], hypothesis_ids: tuple[str, ...], out: list[Problem]
                     ) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    where = "profile.multiplicity.special"
    special = mult.get("special", _MISSING)
    if special is _MISSING:
        out.append(_problem("QG-P01", where))
        return ()
    view = _view(special)
    if view is None:
        out.append(_problem("QG-T01", where))
        return ()
    rules: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    for hid, entry in view.items():
        if not _is_identifier(hid) or hid not in hypothesis_ids:
            out.append(_problem("QG-P01", where))
            continue
        at = f"{where}.{hid}"
        entry_view = _view(entry)
        if entry_view is None:
            out.append(_problem("QG-T01", at))
            continue
        components = entry_view.get("components", _MISSING)
        if components is _MISSING:
            out.append(_problem("QG-P01", f"{at}.components"))
            continue
        components_view = _view(components)
        if components_view is None:
            out.append(_problem("QG-T01", f"{at}.components"))
            continue
        levels: list[tuple[str, str]] = []
        for name in components_view:
            if not _is_identifier(name):
                out.append(_problem("QG-P01", f"{at}.components"))
                continue
            levels.append((name, _profile_level(components_view, name, f"{at}.components.{name}", out)))
        rules.append((hid, tuple(levels)))
    return tuple(rules)


def _parse_profile(profile: dict[Any, Any], view: dict[str, Any]) -> tuple[_Profile | None, list[Problem]]:
    """Profile structure, identifiers (DC3, DC3a) and internal consistency (DC5). Any Problem rejects the profile."""
    out = _walk(profile, PROFILE_FIELDS, "profile", ())
    study_id = _profile_text(view, "study_id", "profile.study_id", out)
    hypothesis_ids = _identifier_list(view, "hypothesis_ids", out, nonempty=True, unique=True)
    required_fields = _identifier_list(view, "required_hypothesis_fields", out)
    reason_codes = _identifier_list(view, "reason_codes", out)
    sections = _identifier_list(view, "required_sections", out)
    evidence_grade = _profile_text(view, "evidence_grade", "profile.evidence_grade", out)

    labels: list[str] = []
    raw_labels = view.get("labels", _MISSING)
    if raw_labels is _MISSING:
        out.append(_problem("QG-P01", "profile.labels"))
    elif type(raw_labels) is not list:
        out.append(_problem("QG-T01", "profile.labels"))
    else:
        for index, label in enumerate(raw_labels):
            if type(label) is not str:
                out.append(_problem("QG-T01", f"profile.labels[{index}]"))
            elif label not in LABELS:
                out.append(_problem("QG-P01", f"profile.labels[{index}]"))
            else:
                labels.append(label)

    terms: list[str] = []
    raw_terms = view.get("forbidden_terms", _MISSING)
    if raw_terms is _MISSING:
        out.append(_problem("QG-P01", "profile.forbidden_terms"))
    elif type(raw_terms) is not list:
        out.append(_problem("QG-T01", "profile.forbidden_terms"))
    else:
        if not raw_terms:
            out.append(_problem("QG-P01", "profile.forbidden_terms"))
        for index, term in enumerate(raw_terms):
            if type(term) is not str:
                out.append(_problem("QG-T01", f"profile.forbidden_terms[{index}]"))
            elif not term:
                out.append(_problem("QG-P01", f"profile.forbidden_terms[{index}]"))
            else:
                terms.append(term)

    supported = weakened = [""]
    union_bound = ""
    special: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()
    raw_mult = view.get("multiplicity", _MISSING)
    mult = _view(raw_mult)
    if raw_mult is _MISSING:
        out.append(_problem("QG-P01", "profile.multiplicity"))
    elif mult is None:
        out.append(_problem("QG-T01", "profile.multiplicity"))
    else:
        supported = _profile_family(mult, "SUPPORTED", ("fwer",), out)
        weakened = _profile_family(mult, "WEAKENED", ("fwer", "per_hypothesis"), out)
        union_bound = _profile_level(mult, "union_bound", "profile.multiplicity.union_bound", out)
        special = _profile_special(mult, hypothesis_ids, out)
    if out:
        return None, out

    # All levels are canonical here. An explicit context keeps the sums exact and independent of global state.
    levels = [supported[1], weakened[1], weakened[2], union_bound] + [lv for _, comps in special for _, lv in comps]
    context = Context(prec=max(28, sum(len(level) for level in levels) + 2), traps=[Inexact])
    if context.add(Decimal(supported[1]), Decimal(weakened[1])) != Decimal(union_bound):
        out.append(_problem("QG-F03", "profile.multiplicity.union_bound"))
    for hid, components in special:
        total = Decimal(0)
        for _, level in components:
            total = context.add(total, Decimal(level))
        if total != Decimal(weakened[2]):
            out.append(_problem("QG-G03", f"profile.multiplicity.special.{hid}"))
    if out:
        return None, out
    return _Profile(study_id, hypothesis_ids, required_fields, tuple(labels), reason_codes, evidence_grade,
                    sections, (supported[0], supported[1]), (weakened[0], weakened[1], weakened[2]),
                    union_bound, special, tuple(terms)), []


def _compare_level(view: dict[str, Any], key: str, expected: str, where: str, missing: str, mismatch: str,
                   out: list[Problem]) -> None:
    value = view.get(key, _MISSING)
    if value is _MISSING:
        out.append(_problem(missing, where))
    elif not _is_level(value):
        out.append(_problem("QG-T01", where))
    elif value != expected:
        out.append(_problem(mismatch, where))


def _check_family(mult: dict[str, Any], name: str, expected_method: str, levels: tuple[tuple[str, str, str], ...],
                  missing: str, method_code: str, out: list[Problem]) -> None:
    where = f"multiplicity.{name}"
    family = mult.get(name, _MISSING)
    if family is _MISSING:
        out.append(_problem(missing, where))
        return
    view = _view(family)
    if view is None:
        out.append(_problem("QG-T01", where))
        return
    method = view.get("method", _MISSING)
    if method is _MISSING:
        out.append(_problem(method_code, f"{where}.method"))
    elif type(method) is not str:
        out.append(_problem("QG-T01", f"{where}.method"))
    elif method != expected_method:
        out.append(_problem(method_code, f"{where}.method"))
    for key, expected, code in levels:
        _compare_level(view, key, expected, f"{where}.{key}", code, code, out)


def _check_hypotheses(view: dict[str, Any], prof: _Profile, out: list[Problem]) -> None:
    hypotheses = view.get("hypotheses", _MISSING)
    if hypotheses is _MISSING:
        out.append(_problem("QG-B01", "hypotheses"))
        out.extend(_problem("QG-B02", f"hypotheses.{hid}") for hid in prof.hypothesis_ids)
        return
    if type(hypotheses) is not list:
        out.append(_problem("QG-T01", "hypotheses"))
        return
    if len(hypotheses) != len(prof.hypothesis_ids):
        out.append(_problem("QG-B01", "hypotheses"))
    required = tuple(dict.fromkeys(HYPOTHESIS_BASE_FIELDS + prof.required_fields))
    seen: set[str] = set()
    for index, item in enumerate(hypotheses):
        at = f"hypotheses[{index}]"
        entry = _view(item)
        if entry is None:
            out.append(_problem("QG-T01", at))
            continue
        out.extend(_problem("QG-C01", f"{at}.{field}") for field in required if field not in entry)

        hid = entry.get("id", _MISSING)
        if hid is not _MISSING:
            if type(hid) is not str:
                out.append(_problem("QG-T01", f"{at}.id"))
            elif hid in seen:
                out.append(_problem("QG-B04", f"{at}.id"))
            else:
                seen.add(hid)
                if hid not in prof.hypothesis_ids:
                    out.append(_problem("QG-B03", f"{at}.id"))

        label = entry.get("label", _MISSING)
        if label is _MISSING:
            continue
        if type(label) is not str:
            out.append(_problem("QG-T01", f"{at}.label"))
            continue
        if label not in prof.labels:
            out.append(_problem("QG-C02", f"{at}.label"))
            continue
        reason = entry.get("reason", _MISSING)
        if reason is _MISSING:
            continue
        if label == INCONCLUSIVE:
            if reason is None:
                out.append(_problem("QG-C03", f"{at}.reason"))
            elif type(reason) is not str:
                out.append(_problem("QG-T01", f"{at}.reason"))
            elif reason not in prof.reason_codes:
                out.append(_problem("QG-C04", f"{at}.reason"))
        elif reason is not None:
            out.append(_problem("QG-C04", f"{at}.reason"))
    out.extend(_problem("QG-B02", f"hypotheses.{hid}") for hid in prof.hypothesis_ids if hid not in seen)


def _check_multiplicity(view: dict[str, Any], prof: _Profile, out: list[Problem]) -> None:
    raw = view.get("multiplicity", _MISSING)
    mult = {} if raw is _MISSING else _view(raw)
    if mult is None:
        out.append(_problem("QG-T01", "multiplicity"))
        return
    _check_family(mult, "SUPPORTED", prof.supported[0], (("fwer", prof.supported[1], "QG-D03"),),
                  "QG-D01", "QG-D02", out)
    _check_family(mult, "WEAKENED", prof.weakened[0],
                  (("fwer", prof.weakened[1], "QG-E03"), ("per_hypothesis", prof.weakened[2], "QG-E04")),
                  "QG-E01", "QG-E02", out)
    _compare_level(mult, "union_bound", prof.union_bound, "multiplicity.union_bound", "QG-F01", "QG-F02", out)
    if not prof.special:
        return
    raw_special = mult.get("special", _MISSING)
    if raw_special is _MISSING:
        out.extend(_problem("QG-G01", f"multiplicity.special.{hid}") for hid, _ in prof.special)
        return
    special = _view(raw_special)
    if special is None:
        out.append(_problem("QG-T01", "multiplicity.special"))
        return
    for hid, components in prof.special:
        at = f"multiplicity.special.{hid}"
        if hid not in special:
            out.append(_problem("QG-G01", at))
            continue
        entry = _view(special[hid])
        if entry is None:
            out.append(_problem("QG-T01", at))
            continue
        raw_components = entry.get("components", _MISSING)
        if raw_components is _MISSING:
            out.append(_problem("QG-G01", f"{at}.components"))
            continue
        levels = _view(raw_components)
        if levels is None:
            out.append(_problem("QG-T01", f"{at}.components"))
            continue
        for name, expected in components:
            _compare_level(levels, name, expected, f"{at}.components.{name}", "QG-G01", "QG-G02", out)


def _check_report_fields(report: dict[Any, Any], view: dict[str, Any], prof: _Profile) -> list[Problem]:
    """DC6 step (5): every report violation against an accepted profile (A04, B–J and QG-T01)."""
    out = _walk(report, REPORT_FIELDS, "report", prof.forbidden_terms)

    study_id = view.get("study_id", _MISSING)
    if study_id is not _MISSING and type(study_id) is not str:
        out.append(_problem("QG-T01", "study_id"))
    elif study_id is _MISSING or study_id != prof.study_id:
        out.append(_problem("QG-A04", "study_id"))

    grade = view.get("evidence_grade", _MISSING)
    if grade is _MISSING:
        out.append(_problem("QG-H01", "evidence_grade"))
    elif type(grade) is not str:
        out.append(_problem("QG-T01", "evidence_grade"))
    elif grade != prof.evidence_grade:
        out.append(_problem("QG-H02", "evidence_grade"))

    sections = view.get("sections", _MISSING)
    present: set[str] = set()
    if sections is not _MISSING and type(sections) is not list:
        out.append(_problem("QG-T01", "sections"))
    else:
        if sections is not _MISSING:
            for index, name in enumerate(sections):
                if type(name) is str:
                    present.add(name)
                else:
                    out.append(_problem("QG-T01", f"sections[{index}]"))
        out.extend(_problem("QG-J01", f"sections.{name}") for name in prof.sections if name not in present)

    _check_hypotheses(view, prof, out)
    _check_multiplicity(view, prof, out)
    return out


def _check(report: dict[Any, Any], profile: dict[Any, Any]) -> list[Problem]:
    profile_view = _view(profile)
    report_view = _view(report)
    assert profile_view is not None and report_view is not None
    profile_schema = profile_view.get("schema", _MISSING)
    if type(profile_schema) is not str or profile_schema not in KNOWN_PROFILE_SCHEMAS:
        return [_problem("QG-A03", "profile.schema")]
    report_schema = report_view.get("schema", _MISSING)
    if report_schema is _MISSING:
        return [_problem("QG-A01", "schema")]
    if type(report_schema) is not str or report_schema not in KNOWN_REPORT_SCHEMAS:
        return [_problem("QG-A02", "schema")]
    prof, problems = _parse_profile(profile, profile_view)
    if prof is None:
        return problems
    return _check_report_fields(report, report_view, prof)


def check_report(report: dict[str, Any], profile: dict[str, Any]) -> Result:
    """Check one report against one profile (DC6). Raises TypeError only when an argument is not exactly a dict."""
    if type(report) is not dict:
        raise TypeError("report must be a dict")
    if type(profile) is not dict:
        raise TypeError("profile must be a dict")
    try:
        problems: tuple[Problem, ...] | None = tuple(_check(report, profile))
    except Exception:
        problems = None
    if problems is None:
        return Result((_problem("QG-X01", "check_report"),))
    return Result(problems)
