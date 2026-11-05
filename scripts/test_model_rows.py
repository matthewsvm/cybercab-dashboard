"""Behavior tests for placeholder model names. No network."""
import csv
import unittest
from pathlib import Path

from model_rows import resolve_model_rows
from collect import assemble, check_totals

ROOT = Path(__file__).resolve().parent.parent
SOURCE = "fsddb.com/robotaxi.json (mirrors TxDMV TxMCCS)"


def row(date, operator, model, count, total, quality="exact"):
    return {
        "date": date, "operator": operator, "model": model, "count": count,
        "operator_total": total, "source": SOURCE, "quality": quality,
    }


class ResolveTests(unittest.TestCase):
    def test_same_total_reuses_previous_counts(self):
        rows = [
            row("2026-11-04", "Tesla Robotaxi", "Model Y", 671, 1244),
            row("2026-11-04", "Tesla Robotaxi", "Cybercab", 573, 1244),
            row("2026-11-05", "Tesla Robotaxi", "Unknown model", 1244, 1244),
        ]
        out = [r for r in resolve_model_rows(rows) if r["date"] == "2026-11-05"]
        self.assertEqual(
            sorted((r["model"], r["count"], r["operator_total"], r["quality"]) for r in out),
            [("Cybercab", 573, 1244, "carried_forward"), ("Model Y", 671, 1244, "carried_forward")],
        )

    def test_changed_total_records_total_only(self):
        rows = [
            row("2026-11-04", "Waymo", "Jaguar I-PACE", 863, 1259),
            row("2026-11-04", "Waymo", "Zeekr RT", 396, 1259),
            row("2026-11-05", "Waymo", "Unknown model", 1300, 1300),
        ]
        out = [r for r in resolve_model_rows(rows) if r["date"] == "2026-11-05"]
        self.assertEqual([(r["model"], r["count"], r["quality"]) for r in out], [("(all models)", 1300, "exact")])

    def test_total_returning_to_an_older_value_does_not_resurrect_old_mix(self):
        rows = [
            row("2026-11-01", "Tesla Robotaxi", "Model Y", 10, 10),
            row("2026-11-02", "Tesla Robotaxi", "Unknown model", 12, 12),
            row("2026-11-03", "Tesla Robotaxi", "Unknown model", 10, 10),
        ]
        by_date = {}
        for r in resolve_model_rows(rows):
            by_date.setdefault(r["date"], []).append((r["model"], r["count"]))
        self.assertEqual(by_date["2026-11-02"], [("(all models)", 12)])
        self.assertEqual(by_date["2026-11-03"], [("(all models)", 10)])

    def test_unchanged_total_carries_forward_again(self):
        rows = [
            row("2026-11-01", "Tesla Robotaxi", "Model Y", 10, 15),
            row("2026-11-01", "Tesla Robotaxi", "Cybercab", 5, 15),
            row("2026-11-02", "Tesla Robotaxi", "Unknown model", 15, 15),
            row("2026-11-03", "Tesla Robotaxi", "", 15, 15),
        ]
        nov3 = [r for r in resolve_model_rows(rows) if r["date"] == "2026-11-03"]
        self.assertEqual(sorted((r["model"], r["count"]) for r in nov3), [("Cybercab", 5), ("Model Y", 10)])
        self.assertTrue(all(r["quality"] == "carried_forward" for r in nov3))

    def test_placeholder_variants_and_canonical_names(self):
        rows = [
            row("2026-11-04", "Tesla Robotaxi", "modey y", 2, 5),
            row("2026-11-04", "Tesla Robotaxi", "cybercab", 3, 5),
            row("2026-11-05", "Tesla Robotaxi", " Unknown Model ", 5, 5),
        ]
        out = [r for r in resolve_model_rows(rows) if r["date"] == "2026-11-05"]
        self.assertEqual(sorted((r["model"], r["count"]) for r in out), [("Cybercab", 3), ("Model Y", 2)])

    def test_mixed_placeholder_keeps_published_counts_only(self):
        rows = [row("2026-11-05", "Tesla Robotaxi", "Model Y", 100, 150),
                row("2026-11-05", "Tesla Robotaxi", "Unknown model", 50, 150)]
        out = resolve_model_rows(rows)
        self.assertEqual([(r["model"], r["count"], r["operator_total"]) for r in out], [("Model Y", 100, 150)])

    def test_approximate_total_only_history_is_unchanged(self):
        rows = [row("2026-07-30", "Tesla Robotaxi", "(all models)", 175, 175, "approximate")]
        out = resolve_model_rows(rows)
        self.assertEqual(out[0]["model"], "(all models)")
        self.assertEqual(out[0]["count"], 175)
        self.assertEqual(out[0]["quality"], "approximate")

    def test_assemble_matches_fleet_size_and_nov4_split(self):
        with (ROOT / "data" / "history.csv").open() as fh:
            existing = list(csv.DictReader(fh))
        existing = [r for r in existing if r["date"] != "2026-11-05"]
        totals = {
            "Waymo": 1259, "Tesla Robotaxi": 1244, "Avride": 344,
            "Zoox": 63, "Nuro": 47, "May Mobility": 22,
        }
        data = {"operators": [
            {"name": name, "fleet_size": total, "models": {"Unknown model": total}}
            for name, total in totals.items()
        ]}
        out = assemble(existing, data, "2026-11-05")
        check_totals(out, data, "2026-11-05")
        nov4 = sorted((r["operator"], r["model"], int(r["count"])) for r in out if r["date"] == "2026-11-04")
        nov5 = sorted((r["operator"], r["model"], int(r["count"])) for r in out if r["date"] == "2026-11-05")
        self.assertEqual(nov5, nov4)
        tesla = [r for r in out if r["date"] == "2026-11-05" and r["operator"] == "Tesla Robotaxi"]
        self.assertEqual(sorted((r["model"], r["count"]) for r in tesla), [("Cybercab", 573), ("Model Y", 671)])
        self.assertTrue(all(r["quality"] == "carried_forward" for r in tesla))
        self.assertNotIn("Unknown model", {r["model"] for r in out})

    def test_committed_nov5_rows_restore_nov4_split(self):
        with (ROOT / "data" / "history.csv").open() as fh:
            rows = list(csv.DictReader(fh))
        self.assertNotIn("Unknown model", {r["model"] for r in rows})
        nov5 = [r for r in rows if r["date"] == "2026-11-05"]
        tesla = sorted((r["model"], int(r["count"]), int(r["operator_total"]), r["quality"])
                       for r in nov5 if r["operator"] == "Tesla Robotaxi")
        self.assertEqual(tesla, [
            ("Cybercab", 573, 1244, "carried_forward"),
            ("Model Y", 671, 1244, "carried_forward"),
        ])
        totals = {}
        sums = {}
        for r in nov5:
            totals[r["operator"]] = int(r["operator_total"])
            sums[r["operator"]] = sums.get(r["operator"], 0) + int(r["count"])
        self.assertEqual(totals, {
            "Waymo": 1259, "Tesla Robotaxi": 1244, "Avride": 344,
            "Zoox": 63, "Nuro": 47, "May Mobility": 22,
        })
        self.assertEqual(sums, totals)

    def test_non_dict_models_do_not_invent_a_split(self):
        existing = [row("2026-11-04", "Zoox", "Zoox", 17, 63), row("2026-11-04", "Zoox", "Toyota Highlander", 46, 63)]
        data = {"operators": [{"name": "Zoox", "fleet_size": 70, "models": ["Zoox", "Toyota Highlander"]}]}
        out = [r for r in assemble(existing, data, "2026-11-05") if r["date"] == "2026-11-05"]
        self.assertEqual([(r["model"], r["count"]) for r in out], [("(all models)", 70)])


if __name__ == "__main__":
    unittest.main()
