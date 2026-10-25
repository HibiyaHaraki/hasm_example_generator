"""Offline regression tests for HASM URL fields and collaboration relationships."""

from __future__ import annotations

import copy
import json
import logging
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from generate_haraki_hibiya import build
from generate_hasm_folder import _generate_combined_model, _generate_model
from generate_hololive_jp import (
    HOLOLIVE_JP_MEMBERS,
    YOUTUBE_WATCH_BASE,
    add_collaboration_fact_mirrors,
    build_member_payload,
    revise_existing_payloads,
    write_payload,
)
from validate_hasm_examples import validate_file


class HasmExamplesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.members = HOLOLIVE_JP_MEMBERS[:3]
        self.video = {
            "id": "testVideo01",
            "snippet": {
                "title": "Sora, Roboco and Miko collaboration",
                "description": "A shared video.",
                "publishedAt": "2026-01-01T00:00:00Z",
            },
        }
        self.payloads = {
            member.slug: build_member_payload(
                member, self.members, [self.video] if index == 0 else []
            )
            for index, member in enumerate(self.members)
        }
        self.logger = logging.getLogger("hasm-tests")

    def validate(self, payload: dict) -> list:
        path = self.root / "input.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return validate_file(path)

    def test_solo_video_has_url_without_collaboration(self) -> None:
        video = copy.deepcopy(self.video)
        video["snippet"]["title"] = "Solo stream"
        payload = build_member_payload(self.members[0], self.members, [video])
        self.assertEqual(payload["facts"][0]["link"], [YOUTUBE_WATCH_BASE + video["id"]])
        self.assertEqual(payload["facts"][0]["link_ids"], [])
        self.assertEqual(
            payload["facts"][0]["experience_ids"],
            [payload["experiences"][0]["experience_id"]],
        )
        self.assertEqual(len(payload["experiences"]), 2)
        self.assertEqual(payload["links"], [])
        self.assertEqual(self.validate(payload), [])

    def test_collaboration_urls_and_relationships_survive_mirroring(self) -> None:
        self.payloads[self.members[1].slug] = build_member_payload(
            self.members[1], self.members, [self.video]
        )
        add_collaboration_fact_mirrors(self.payloads, self.members)
        link_ids = set()
        fact_ids = set()
        participant_ids = set()
        for payload in self.payloads.values():
            self.assertEqual(len(payload["facts"]), 1)
            self.assertEqual(len(payload["experiences"]), 2)
            fact = payload["facts"][0]
            fact_ids.add(fact["fact_id"])
            participant_ids.update(fact["person_ids"])
            self.assertEqual(fact["link"], [YOUTUBE_WATCH_BASE + self.video["id"]])
            self.assertEqual(
                fact["experience_ids"],
                [payload["experiences"][1]["experience_id"]],
            )
            self.assertEqual(len(fact["link_ids"]), 1)
            link = payload["links"][0]
            link_ids.add(link["link_id"])
            self.assertEqual(fact["link_ids"], [link["link_id"]])
            self.assertIn(link["link_id"], payload["person"]["link_ids"])
            self.assertEqual(link["link"], fact["link"])
            self.assertEqual(self.validate(payload), [])
        self.assertEqual(len(link_ids), 1)
        for payload in self.payloads.values():
            self.assertTrue(fact_ids.issubset(payload["links"][0]["related_ids"]))
            self.assertTrue(participant_ids.issubset(payload["links"][0]["related_ids"]))
        before = copy.deepcopy(self.payloads)
        add_collaboration_fact_mirrors(self.payloads, self.members)
        self.assertEqual(self.payloads, before)

    def test_all_entity_url_fields_round_trip_to_sqlite(self) -> None:
        source = self.payloads[self.members[0].slug]
        source["person"]["link"] = ["https://example.org/profile"]
        source["experiences"][0]["link"] = ["http://example.org/activity"]
        add_collaboration_fact_mirrors(self.payloads, self.members)
        output = self.root / "model"
        self.assertTrue(_generate_combined_model(list(self.payloads.values()), output, self.logger))
        with closing(sqlite3.connect(output / "hasm.db")) as conn:
            for table, expected in [("person", 3), ("experience", 6), ("fact", 3), ("link", 1)]:
                rows = conn.execute(f"SELECT link FROM {table}").fetchall()
                self.assertEqual(len(rows), expected)
                self.assertTrue(all(isinstance(json.loads(row[0]), list) for row in rows))
            self.assertEqual(
                json.loads(conn.execute("SELECT link FROM person WHERE person_id = ?",
                                       (source["person"]["person_id"],)).fetchone()[0]),
                source["person"]["link"],
            )
            self.assertEqual(
                json.loads(conn.execute("SELECT link FROM experience WHERE experience_id = ?",
                                       (source["experiences"][0]["experience_id"],)).fetchone()[0]),
                source["experiences"][0]["link"],
            )
            for table in ("fact", "link"):
                for row in conn.execute(f"SELECT link FROM {table}"):
                    self.assertEqual(json.loads(row[0]), [YOUTUBE_WATCH_BASE + self.video["id"]])
        for payload in self.payloads.values():
            self.assertTrue((output / payload["facts"][0]["fact_description_path"]).is_file())

    def test_legacy_json_without_url_fields_still_generates(self) -> None:
        payload = build()
        for entity in [payload["person"], *payload["experiences"], *payload["facts"]]:
            entity.pop("link")
        self.assertEqual(self.validate(payload), [])
        output = self.root / "legacy"
        self.assertTrue(_generate_model(payload, output, self.logger))
        with closing(sqlite3.connect(output / "hasm.db")) as conn:
            for table in ("person", "experience", "fact"):
                self.assertEqual(conn.execute(f"SELECT DISTINCT link FROM {table}").fetchall(), [("[]",)])

    def test_url_validation_on_every_entity_type(self) -> None:
        payload = self.payloads[self.members[0].slug]
        entities = [payload["person"], payload["experiences"][0], payload["facts"][0], payload["links"][0]]
        for entity in entities:
            for invalid in [
                None, "https://example.org", [None], [""], ["example.org"],
                ["https:example.org"], ["file:///C:/secret"], ["https://user:pass@example.org"],
                ["https://example.org/has space"], [" https://example.org"],
                ["https://example.org:99999"], ["https://[broken"],
            ]:
                with self.subTest(invalid=invalid):
                    entity["link"] = invalid
                    self.assertTrue(self.validate(payload))
            entity["link"] = ["https://example.org/path?q=hello%20world#part"]
            self.assertEqual(self.validate(payload), [])
            entity["link"] = []

    def test_revise_existing_is_offline_and_idempotent(self) -> None:
        source = self.payloads[self.members[0].slug]
        source["links"] = []
        source["person"]["link_ids"] = []
        source["facts"][0]["link_ids"] = []
        for payload in self.payloads.values():
            for entity in [payload["person"], *payload["experiences"], *payload["facts"]]:
                entity.pop("link", None)
        for member in self.members:
            write_payload(self.root, member, self.payloads[member.slug])
        self.assertEqual(revise_existing_payloads(self.root, self.members), 3)
        first = {path.name: path.read_bytes() for path in self.root.glob("*.json")}
        for path in self.root.glob("*.json"):
            self.assertEqual(validate_file(path), [])
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["facts"]), 1)
            self.assertTrue(payload["facts"][0]["link_ids"])
            self.assertEqual(payload["facts"][0]["link"], [YOUTUBE_WATCH_BASE + self.video["id"]])
        self.assertEqual(revise_existing_payloads(self.root, self.members), 3)
        self.assertEqual({path.name: path.read_bytes() for path in self.root.glob("*.json")}, first)

    def test_conflicting_shared_links_fail_generation(self) -> None:
        add_collaboration_fact_mirrors(self.payloads, self.members)
        payloads = [copy.deepcopy(payload) for payload in self.payloads.values()]
        payloads[1]["links"][0]["link_name"] = "Conflicting name"
        with self.assertLogs(self.logger, level="ERROR"):
            self.assertFalse(_generate_combined_model(payloads, self.root / "conflict", self.logger))

    def test_haraki_generator_emits_url_arrays(self) -> None:
        payload = build()
        for entity in [payload["person"], *payload["experiences"], *payload["facts"]]:
            self.assertEqual(entity["link"], [])
        self.assertEqual(self.validate(payload), [])


if __name__ == "__main__":
    unittest.main()
