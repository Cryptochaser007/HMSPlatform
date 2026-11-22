"""FHIR R4 resource generators conforming to ABDM national health data profiles."""

import uuid
from datetime import UTC, datetime
from typing import Any


def build_patient_resource(
    patient_id: str,
    name: str,
    gender: str,
    dob: str,
    phone: str | None = None,
    abha_id: str | None = None,
) -> dict[str, Any]:
    """Build FHIR R4 Patient resource under ABDM Patient profile."""
    resource: dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "versionId": "1",
            "lastUpdated": datetime.now(UTC).isoformat(),
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Patient"],
        },
        "identifier": [],
        "name": [
            {
                "text": name,
            }
        ],
        "gender": gender.lower() if gender in ("MALE", "FEMALE", "OTHER") else "unknown",
        "birthDate": dob,
    }

    if abha_id:
        resource["identifier"].append({
            "type": {
                "coding": [
                    {
                        "system": "https://nrces.in/ndhm/fhir/r4/CodeSystem/ndhm-identifier-type-code",
                        "code": "ABHA",
                        "display": "Ayushman Bharat Health Account",
                    }
                ]
            },
            "system": "https://healthid.ndhm.gov.in",
            "value": abha_id,
        })

    if phone:
        resource["telecom"] = [
            {"system": "phone", "value": phone, "use": "mobile"}
        ]

    return resource


def build_encounter_resource(
    encounter_id: str,
    patient_id: str,
    doctor_id: str,
    status: str,
    encounter_type: str,
    start_time: str,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Build FHIR R4 Encounter resource."""
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Encounter"]
        },
        "status": "finished" if status == "COMPLETED" else "in-progress",
        "class": {
            "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
            "code": "AMB" if encounter_type == "OPD" else "IMP",
            "display": "ambulatory" if encounter_type == "OPD" else "inpatient encounter",
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "participant": [
            {
                "individual": {"reference": f"Practitioner/{doctor_id}"}
            }
        ],
        "period": {
            "start": start_time,
            "end": end_time or start_time,
        },
    }


def build_condition_resource(
    condition_id: str,
    patient_id: str,
    encounter_id: str,
    icd_code: str,
    display_name: str,
) -> dict[str, Any]:
    """Build FHIR R4 Condition resource for diagnosis with ICD-10."""
    return {
        "resourceType": "Condition",
        "id": condition_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Condition"]
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                    "display": "Active",
                }
            ]
        },
        "code": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/icd-10",
                    "code": icd_code,
                    "display": display_name,
                }
            ],
            "text": display_name,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "recordedDate": datetime.now(UTC).isoformat(),
    }


def build_observation_resource(
    observation_id: str,
    patient_id: str,
    encounter_id: str,
    code: str,
    display: str,
    value: float,
    unit: str,
) -> dict[str, Any]:
    """Build FHIR R4 Observation resource (e.g. LOINC coded vitals)."""
    return {
        "resourceType": "Observation",
        "id": observation_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Observation"]
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": code,
                    "display": display,
                }
            ],
            "text": display,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "effectiveDateTime": datetime.now(UTC).isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": unit,
        },
    }


def build_medication_request(
    med_id: str,
    patient_id: str,
    doctor_id: str,
    encounter_id: str,
    medication_name: str,
    dosage: str,
    frequency: str,
    duration_days: int,
) -> dict[str, Any]:
    """Build FHIR R4 MedicationRequest resource."""
    return {
        "resourceType": "MedicationRequest",
        "id": med_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/MedicationRequest"]
        },
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "text": medication_name,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "authoredOn": datetime.now(UTC).isoformat(),
        "requester": {"reference": f"Practitioner/{doctor_id}"},
        "dosageInstruction": [
            {
                "text": f"{dosage} {frequency} for {duration_days} days",
                "timing": {"code": {"text": frequency}},
            }
        ],
    }


def build_composition(
    composition_id: str,
    patient_id: str,
    encounter_id: str,
    doctor_id: str,
    title: str,
    section_entries: list[dict[str, str]],
) -> dict[str, Any]:
    """Build FHIR R4 Composition resource organizing clinical document sections."""
    return {
        "resourceType": "Composition",
        "id": composition_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/OPConsultRecord"]
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "371530004",
                    "display": "Clinical consultation report",
                }
            ],
            "text": title,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "date": datetime.now(UTC).isoformat(),
        "author": [{"reference": f"Practitioner/{doctor_id}"}],
        "title": title,
        "section": [
            {
                "title": entry["title"],
                "entry": [{"reference": entry["reference"]}],
            }
            for entry in section_entries
        ],
    }


def build_bundle(resources: list[dict[str, Any]], bundle_type: str = "document") -> dict[str, Any]:
    """Assemble a standard FHIR R4 Bundle containing given resources."""
    bundle_id = str(uuid.uuid4())
    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {
            "versionId": "1",
            "lastUpdated": datetime.now(UTC).isoformat(),
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"],
        },
        "identifier": {
            "system": "https://hms.local/bundle",
            "value": bundle_id,
        },
        "type": bundle_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{r.get('id', str(uuid.uuid4()))}",
                "resource": r,
            }
            for r in resources
        ],
    }


def build_practitioner_resource(
    practitioner_id: str,
    name: str,
    registration_number: str | None = None,
) -> dict[str, Any]:
    """Build NRCeS FHIR R4 Practitioner resource."""
    resource: dict[str, Any] = {
        "resourceType": "Practitioner",
        "id": practitioner_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Practitioner"]
        },
        "name": [{"text": name}],
    }
    if registration_number:
        resource["identifier"] = [
            {
                "system": "https://doctor.ndhm.gov.in",
                "value": registration_number,
            }
        ]
    return resource


def build_organization_resource(
    org_id: str,
    name: str,
    hfr_id: str | None = None,
) -> dict[str, Any]:
    """Build NRCeS FHIR R4 Organization resource."""
    return {
        "resourceType": "Organization",
        "id": org_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/Organization"]
        },
        "identifier": [
            {
                "system": "https://facility.ndhm.gov.in",
                "value": hfr_id or org_id,
            }
        ],
        "name": name,
    }


def build_diagnostic_report_resource(
    report_id: str,
    patient_id: str,
    encounter_id: str,
    title: str,
    conclusion: str,
    observation_ids: list[str],
    issued: str | None = None,
) -> dict[str, Any]:
    """Build NRCeS FHIR R4 DiagnosticReportLab resource."""
    return {
        "resourceType": "DiagnosticReport",
        "id": report_id,
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReportLab"]
        },
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "4241000179101",
                        "display": "Laboratory report",
                    }
                ]
            }
        ],
        "code": {"text": title},
        "subject": {"reference": f"Patient/{patient_id}"},
        "encounter": {"reference": f"Encounter/{encounter_id}"},
        "issued": issued or datetime.now(UTC).isoformat(),
        "result": [{"reference": f"Observation/{oid}"} for oid in observation_ids],
        "conclusion": conclusion,
    }


def build_op_consult_bundle(
    *,
    patient: dict[str, Any],
    practitioner: dict[str, Any],
    organization: dict[str, Any],
    encounter: dict[str, Any],
    conditions: list[dict[str, Any]] | None = None,
    observations: list[dict[str, Any]] | None = None,
    medications: list[dict[str, Any]] | None = None,
    chief_complaint: str | None = None,
) -> dict[str, Any]:
    """Assemble an NRCeS-compliant FHIR R4 OPConsultRecord Document Bundle."""
    conditions = conditions or []
    observations = observations or []
    medications = medications or []

    sections: list[dict[str, Any]] = []
    if conditions:
        sections.append(
            {
                "title": "Chief complaints and Diagnosis",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "422843007",
                            "display": "Chief complaint section",
                        }
                    ]
                },
                "entry": [{"reference": f"Condition/{c['id']}"} for c in conditions],
            }
        )
    if observations:
        sections.append(
            {
                "title": "Physical Examination & Vitals",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "425044008",
                            "display": "Physical exam section",
                        }
                    ]
                },
                "entry": [{"reference": f"Observation/{o['id']}"} for o in observations],
            }
        )
    if medications:
        sections.append(
            {
                "title": "Medications",
                "code": {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "721912009",
                            "display": "Medication summary document",
                        }
                    ]
                },
                "entry": [{"reference": f"MedicationRequest/{m['id']}"} for m in medications],
            }
        )

    composition = {
        "resourceType": "Composition",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/OPConsultRecord"]
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "371530004",
                    "display": "Clinical consultation report",
                }
            ],
            "text": chief_complaint or "OP Consultation Record",
        },
        "subject": {"reference": f"Patient/{patient['id']}"},
        "encounter": {"reference": f"Encounter/{encounter['id']}"},
        "date": datetime.now(UTC).isoformat(),
        "author": [{"reference": f"Practitioner/{practitioner['id']}"}],
        "custodian": {"reference": f"Organization/{organization['id']}"},
        "title": "OP Consultation Record",
        "section": sections,
    }

    resources = [
        composition,
        patient,
        practitioner,
        organization,
        encounter,
        *conditions,
        *observations,
        *medications,
    ]
    return build_bundle(resources, bundle_type="document")


def build_prescription_bundle(
    *,
    patient: dict[str, Any],
    practitioner: dict[str, Any],
    organization: dict[str, Any],
    encounter: dict[str, Any],
    medications: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble an NRCeS-compliant FHIR R4 PrescriptionRecord Document Bundle."""
    composition = {
        "resourceType": "Composition",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/PrescriptionRecord"]
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "440545006",
                    "display": "Prescription record",
                }
            ],
            "text": "Prescription Record",
        },
        "subject": {"reference": f"Patient/{patient['id']}"},
        "encounter": {"reference": f"Encounter/{encounter['id']}"},
        "date": datetime.now(UTC).isoformat(),
        "author": [{"reference": f"Practitioner/{practitioner['id']}"}],
        "custodian": {"reference": f"Organization/{organization['id']}"},
        "title": "Prescription Record",
        "section": [
            {
                "title": "Prescription",
                "entry": [{"reference": f"MedicationRequest/{m['id']}"} for m in medications],
            }
        ],
    }
    return build_bundle(
        [composition, patient, practitioner, organization, encounter, *medications],
        bundle_type="document",
    )


def build_diagnostic_report_bundle(
    *,
    patient: dict[str, Any],
    practitioner: dict[str, Any],
    organization: dict[str, Any],
    encounter: dict[str, Any],
    report: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assemble an NRCeS-compliant FHIR R4 DiagnosticReportRecord Document Bundle."""
    composition = {
        "resourceType": "Composition",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DiagnosticReportRecord"]
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "721981007",
                    "display": "Diagnostic studies report",
                }
            ],
            "text": "Diagnostic Report",
        },
        "subject": {"reference": f"Patient/{patient['id']}"},
        "encounter": {"reference": f"Encounter/{encounter['id']}"},
        "date": datetime.now(UTC).isoformat(),
        "author": [{"reference": f"Practitioner/{practitioner['id']}"}],
        "custodian": {"reference": f"Organization/{organization['id']}"},
        "title": "Diagnostic Report",
        "section": [
            {
                "title": "Diagnostic Reports",
                "entry": [{"reference": f"DiagnosticReport/{report['id']}"}],
            }
        ],
    }
    return build_bundle(
        [composition, patient, practitioner, organization, encounter, report, *observations],
        bundle_type="document",
    )


def build_discharge_summary_bundle(
    *,
    patient: dict[str, Any],
    practitioner: dict[str, Any],
    organization: dict[str, Any],
    encounter: dict[str, Any],
    conditions: list[dict[str, Any]] | None = None,
    medications: list[dict[str, Any]] | None = None,
    summary_text: str = "Patient discharged in stable condition.",
) -> dict[str, Any]:
    """Assemble an NRCeS-compliant FHIR R4 DischargeSummaryRecord Document Bundle."""
    conditions = conditions or []
    medications = medications or []

    composition = {
        "resourceType": "Composition",
        "id": str(uuid.uuid4()),
        "meta": {
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DischargeSummaryRecord"]
        },
        "status": "final",
        "type": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "373942005",
                    "display": "Discharge summary",
                }
            ],
            "text": "Discharge Summary",
        },
        "subject": {"reference": f"Patient/{patient['id']}"},
        "encounter": {"reference": f"Encounter/{encounter['id']}"},
        "date": datetime.now(UTC).isoformat(),
        "author": [{"reference": f"Practitioner/{practitioner['id']}"}],
        "custodian": {"reference": f"Organization/{organization['id']}"},
        "title": "Discharge Summary",
        "section": [
            {
                "title": "Hospital Course & Summary",
                "text": {"status": "generated", "div": f"<div>{summary_text}</div>"},
                "entry": [{"reference": f"Condition/{c['id']}"} for c in conditions],
            },
            {
                "title": "Discharge Medications",
                "entry": [{"reference": f"MedicationRequest/{m['id']}"} for m in medications],
            },
        ],
    }
    return build_bundle(
        [composition, patient, practitioner, organization, encounter, *conditions, *medications],
        bundle_type="document",
    )


def parse_fhir_bundle_to_timeline(bundle: dict[str, Any]) -> dict[str, Any]:
    """Extract a structured clinical timeline entry from a decrypted FHIR R4 Document Bundle."""
    entries = bundle.get("entry") or []
    resources = [e.get("resource", {}) for e in entries if isinstance(e, dict)]

    comp: dict[str, Any] = next((r for r in resources if r.get("resourceType") == "Composition"), {})
    org: dict[str, Any] = next((r for r in resources if r.get("resourceType") == "Organization"), {})
    prac: dict[str, Any] = next((r for r in resources if r.get("resourceType") == "Practitioner"), {})
    conditions = [r for r in resources if r.get("resourceType") == "Condition"]
    observations = [r for r in resources if r.get("resourceType") == "Observation"]
    meds = [r for r in resources if r.get("resourceType") == "MedicationRequest"]
    reports = [r for r in resources if r.get("resourceType") == "DiagnosticReport"]

    practitioner_name = "Consulting Physician"
    if prac.get("name") and isinstance(prac["name"], list):
        practitioner_name = prac["name"][0].get("text") or practitioner_name

    return {
        "bundle_id": bundle.get("id", str(uuid.uuid4())),
        "document_type": comp.get("title") or comp.get("type", {}).get("text") or "Clinical Document",
        "date": comp.get("date") or bundle.get("timestamp") or datetime.now(UTC).isoformat(),
        "facility_name": org.get("name") or "External ABDM Facility",
        "practitioner_name": practitioner_name,
        "diagnoses": [
            c.get("code", {}).get("text")
            or (c.get("code", {}).get("coding", [{}])[0].get("display") if c.get("code", {}).get("coding") else "Condition")
            for c in conditions
        ],
        "medications": [
            {
                "name": m.get("medicationCodeableConcept", {}).get("text", "Medication"),
                "dosage": (
                    m.get("dosageInstruction", [{}])[0].get("text", "")
                    if m.get("dosageInstruction")
                    else ""
                ),
            }
            for m in meds
        ],
        "observations": [
            {
                "name": o.get("code", {}).get("text", "Observation"),
                "value": o.get("valueQuantity", {}).get("value"),
                "unit": o.get("valueQuantity", {}).get("unit", ""),
            }
            for o in observations
        ],
        "diagnostic_reports": [
            {
                "title": r.get("code", {}).get("text", "Diagnostic Report"),
                "conclusion": r.get("conclusion", ""),
            }
            for r in reports
        ],
    }


