"""FHIR R4 resource generators conforming to ABDM national health data profiles."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def build_patient_resource(
    patient_id: str,
    name: str,
    gender: str,
    dob: str,
    phone: Optional[str] = None,
    abha_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build FHIR R4 Patient resource under ABDM Patient profile."""
    resource: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": patient_id,
        "meta": {
            "versionId": "1",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
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
    end_time: Optional[str] = None,
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
        "recordedDate": datetime.now(timezone.utc).isoformat(),
    }


def build_observation_resource(
    observation_id: str,
    patient_id: str,
    encounter_id: str,
    code: str,
    display: str,
    value: float,
    unit: str,
) -> Dict[str, Any]:
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
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(),
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
) -> Dict[str, Any]:
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
        "authoredOn": datetime.now(timezone.utc).isoformat(),
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
    section_entries: List[Dict[str, str]],
) -> Dict[str, Any]:
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
        "date": datetime.now(timezone.utc).isoformat(),
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


def build_bundle(resources: List[Dict[str, Any]], bundle_type: str = "document") -> Dict[str, Any]:
    """Assemble a standard FHIR R4 Bundle containing given resources."""
    bundle_id = str(uuid.uuid4())
    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {
            "versionId": "1",
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
            "profile": ["https://nrces.in/ndhm/fhir/r4/StructureDefinition/DocumentBundle"],
        },
        "identifier": {
            "system": "https://hms.local/bundle",
            "value": bundle_id,
        },
        "type": bundle_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "entry": [
            {
                "fullUrl": f"urn:uuid:{r.get('id', str(uuid.uuid4()))}",
                "resource": r,
            }
            for r in resources
        ],
    }

