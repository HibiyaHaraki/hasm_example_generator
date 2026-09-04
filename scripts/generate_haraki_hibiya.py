#!/usr/bin/env python3
"""Generate data/persons/haraki_hibiya.json from a curated activity timeline.

Source of truth for the timeline entries is hibiya-app's Record_data.js.
Re-run this script (and update RECORDS below) whenever Record_data.js changes.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://hasm.example/haraki_hibiya")

PERSON_NAME = "Haraki Hibiya"
BIRTHDAY = "1997-10-21T00:00:00+09:00"
DIE = ""  # blank: living person

MONTH_NUMBER = {
    "January": 1,
    "February": 2,
    "Feburuary": 2,  # typo present in source data
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "Octorber": 10,  # typo present in source data
    "November": 11,
    "December": 12,
}

# One EXPERIENCE branch per Record_data.js "type", all rooted under a single
# life-stream EXPERIENCE.
TYPE_EXPERIENCE_NAMES = {
    "academic": "Academic Path",
    "work": "Work Experiences",
    "research": "Research Activities",
    "international": "International Experiences",
    "artifact": "Artifact Creation",
    "qualification": "Qualifications",
    "award": "Awards",
    "other": "Other Milestones",
}

# (year, month, type, english summary) transcribed from hibiya-app Record_data.js
RECORDS: list[tuple[int, str, str, str]] = [
    (2013, "March", "academic", "Graduate Akemi Junior High School in Urayastu, Chiba, Japan"),
    (2013, "April", "academic", "Enter Toshima Gakuin High School in Tokyo, Japan"),
    (2014, "August", "international", "Trip to Manila, Philippine"),
    (2016, "March", "academic", "Graduate Toshima Gakuin High School in Tokyo, Japan"),
    (2016, "April", "academic", "Start to study for entering university"),
    (2017, "April", "academic", "Enter University of Electro-Communications in Tokyo (UEC)"),
    (2017, "August", "international", "Enter University of British-Columbia English Language Institute in Canada (UBC)"),
    (2017, "September", "international", "Trip to Banff (Canadian Rockies)"),
    (2017, "September", "international", "Graduate UBC English Language Institute in Canada"),
    (2018, "August", "other", 'Create "ASTEROID 1st Gen"'),
    (2019, "February", "qualification", "Get driver's license"),
    (2019, "August", "international", "Enter Blekinge Institute of Technology in Sweden (BTH) by exchange program"),
    (2019, "September", "international", "Trip to Zermatt (Switzerland)"),
    (2019, "November", "international", "Trip to Viena and Butapest (Austria, Hungary)"),
    (2020, "January", "international", "Trip to Southern Iceland"),
    (2020, "Feburuary", "international", "Trip to Stockhorm and Copenhagen (Sweden, Denmark)"),
    (2020, "Feburuary", "artifact", 'Create "Airport Quiz"'),
    (2020, "March", "international", "Emergency return from Sweden because of COVID-19"),
    (2020, "April", "artifact", 'Create "DENSO Rugby Web-Site"'),
    (2020, "May", "international", "Finish Exchange Program at BTH in Sweden"),
    (2020, "August", "artifact", 'Create "Displacement Lab"'),
    (2020, "December", "qualification", "Passed Applied Information Technology Engineer Examination"),
    (2020, "December", "research", "Join to Yusa-lab"),
    (2021, "March", "work", "Start MATLAB Student Ambassador at UEC"),
    (2021, "March", "research", "Start to research of deformation analysis with point cloud data"),
    (2021, "June", "international", "Join the IE-IE Letter Discussion"),
    (2021, "June", "work", "Start to work as a Teaching Assistant (TA) in Numerical Analysis class in UEC (~ August)"),
    (2021, "September", "research", "Presentation at the 34th Computational Mechanics Conference (CMD2021)"),
    (2021, "Octorber", "qualification", "Take TOEIC Listening & Reading Test. Score is 790."),
    (2021, "November", "award", "Got the Japan Society of Mechanical Engineering (JSME) Young Fellow Medals"),
    (2021, "December", "work", "Hold 1th MATLAB Onramp Seminar in UEC"),
    (2021, "December", "work", "Start Technical Assistant of International Education Working Group in UEC (~ March, 2022)"),
    (2021, "December", "work", "Join the interview of UEC International Education WG Magazine"),
    (2021, "December", "other", 'Purchase "Analysis"'),
    (2022, "February", "research", "Presentation of graduate research"),
    (2022, "March", "work", "Start Working as Part-time staff in UEC"),
    (2022, "March", "academic", "Graduate School of Informatics and Engineering in UEC"),
    (2022, "March", "award", "Got student award in UEC"),
    (2022, "March", "work", "Help sorting documents of the spring conference of the Japan Society for Technology of Plasticity in 2023"),
    (2022, "April", "academic", "Enter Graduate School of Informatics and Engineering in UEC"),
    (2022, "May", "work", "Presentation at graduation-alumni cross-cultural talk event in UEC"),
    (2022, "May", "work", "Hold 2nd MATLAB Onramp Seminar in UEC"),
    (2022, "May", "work", "Presentation at MATLAB EXPO 2022 Lightning Talk"),
    (2022, "May", "research", "Start to help analyzing fluid dynamics experiment of Uemi by creating MATLAB script"),
    (2022, "July", "research", "Help fluid dynamics experiment by developing MATLAB script"),
    (2022, "August", "research", "Presentation at WCCM-APCOM 2022"),
    (2022, "August", "other", 'Create "ASTEROID 2nd Gen"'),
    (2022, "August", "artifact", 'Create "sudoku_help"'),
    (2022, "August", "international", "Start Internship at GrandM in FPT Virtual University (Online, Vietnam)"),
    (2022, "September", "work", "Help sorting documents of the 73th coalition conference of the Japan Society for Technology of Plasticity in 2023"),
    (2022, "September", "international", "Finish Internship at GrandM in FPT Virtual University (Online, Vietnam)"),
    (2022, "September", "artifact", "Create hibiya-app"),
    (2022, "Octorber", "work", "Hold 3rd MATLAB Onramp Seminar in UEC"),
    (2022, "Octorber", "work", "Help for Sakura science program"),
    (2022, "November", "research", "Presentation at the 35th Computational Mechanics Conference (CMD2022)"),
    (2022, "November", "work", "Help MATLAB Student Ambassadors in the University of Tokyo in Komaba festival"),
    (2022, "December", "work", "Host MATLAB Onramp seminar"),
    (2022, "December", "international", "Trip to Philippine"),
    (2023, "January", "work", "Internship at TOYOTA Motor Corporation"),
    (2023, "February", "work", "Start job hunting"),
    (2023, "February", "work", "Create app for cutting PDF by Python"),
    (2023, "March", "work", "TOYOTA Motor Company gave me the job offer in Vehicle Technology Development / Control Electronics Platform Development"),
    (2023, "March", "work", "Bosch gave me the job offer in Cross-domain Computing department (XC)"),
    (2023, "April", "work", "Hold 4th MATLAB Onramp Seminar in UEC"),
    (2023, "May", "work", "Join MATLAB EXPO 2023"),
    (2023, "October", "work", "Start to work as a Teaching Assistant (TA) in Mechanical Engineering and Intelligent Systems Laboratory, Advanced II class in UEC (~ Jan. 2024)"),
]


def entity_id(kind: str, key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}"))


def build() -> dict:
    person_id = entity_id("person", "haraki_hibiya")

    root_id = entity_id("experience", "root")
    experiences = [
        {
            "experience_id": root_id,
            "person_id": person_id,
            "experience_name": "Life of Haraki Hibiya",
            "experience_description_path": f"EXPERIENCE/{root_id}/main.md",
            "parent_experience_ids": [],
            "link_ids": [],
        }
    ]

    experience_id_by_type: dict[str, str] = {}
    for type_key, name in TYPE_EXPERIENCE_NAMES.items():
        exp_id = entity_id("experience", type_key)
        experience_id_by_type[type_key] = exp_id
        experiences.append(
            {
                "experience_id": exp_id,
                "person_id": person_id,
                "experience_name": name,
                "experience_description_path": f"EXPERIENCE/{exp_id}/main.md",
                "parent_experience_ids": [root_id],
                "link_ids": [],
            }
        )

    facts = []
    for index, (year, month, type_key, summary) in enumerate(RECORDS):
        occurred_at = f"{year:04d}-{MONTH_NUMBER[month]:02d}-01T00:00:00+09:00"
        fact_id = entity_id("fact", f"{index:03d}")
        facts.append(
            {
                "fact_id": fact_id,
                "fact_name": summary,
                "occurred_at": occurred_at,
                "fact_description_path": f"FACT/{fact_id}/main.md",
                "experience_ids": [experience_id_by_type[type_key]],
                "person_ids": [person_id],
                "link_ids": [],
            }
        )

    person = {
        "person_id": person_id,
        "person_name": PERSON_NAME,
        "person_description_path": f"PERSON/{person_id}/main.md",
        "birthday": BIRTHDAY,
        "die": DIE,
        "link_ids": [],
    }

    return {"person": person, "experiences": experiences, "facts": facts, "links": []}


def main() -> int:
    data = build()
    out_path = Path(__file__).resolve().parent.parent / "data" / "persons" / "haraki_hibiya.json"
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(data['experiences'])} experiences, {len(data['facts'])} facts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
