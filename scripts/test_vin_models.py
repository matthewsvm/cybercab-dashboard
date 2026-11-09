"""VIN decoding and the rule that model sources are not added together."""
import csv
import unittest
from pathlib import Path

from ca_activity import activity_rows, operator_name, sum_activity
from service_areas import feature_collection
from txmccs import collect_vins
from vin_models import (
    choose_vin_counts,
    count_vins,
    decode_vin,
    select_model_rows,
    texas_registered_total,
)
from collect import assemble


def vin(prefix, n=0):
    # 17-character stand-in. decode_vin only reads the prefix; the suffix keeps them unique.
    return f"{prefix}{'A' * (12 - len(str(n)))}{n}"[:17].ljust(17, "0")


class DecodeTests(unittest.TestCase):
    def test_verified_prefixes(self):
        cases = {
            "5YJAJEEU7TA004222": "Cybercab",
            "7SAYGDEE0TF587335": "Model Y",
            "SADHW2S1XR1637900": "Jaguar I-PACE",
            "L6TZB1G17TU026499": "Zeekr RT",
            "7YAKN4DA0TY066728": "Hyundai Ioniq 5",
            "KM8KN4AE1PU161113": "Hyundai Ioniq 5",
            "5TDDGRFH5HS026312": "Toyota Highlander",
            "7Z00XVHX3VC000252": "Zoox",
            "7UUG1GHJ0TA040336": "Lucid Gravity",
            "JTDKAMFU9N3167356": "Toyota Prius",
            "5TDYRKEC9MS054357": "Toyota Sienna",
        }
        for sample, model in cases.items():
            self.assertEqual(decode_vin(sample), model, sample)

    def test_unknown_prefix_is_not_guessed(self):
        self.assertIsNone(decode_vin("1HGCM82633A004352"))
        self.assertIsNone(decode_vin(""))
        self.assertIsNone(decode_vin("5YJ"))  # shorter than a real VIN

    def test_two_ioniq_prefixes_add_within_the_vin_census_only(self):
        vins = [vin("7YAK", i) for i in range(334)] + [vin("KM8K", i) for i in range(10)]
        summary = count_vins(vins)
        self.assertEqual(summary["counts"], {"Hyundai Ioniq 5": 344})
        self.assertEqual(summary["total"], 344)
        self.assertEqual(summary["unrecognized"], 0)

    def test_duplicate_vins_are_counted_once(self):
        sample = "7SAYGDEE0TF587335"
        summary = count_vins([sample, sample.lower(), "5YJAJEEU7TA004222"])
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["duplicates"], 1)
        self.assertEqual(summary["counts"], {"Model Y": 1, "Cybercab": 1})


class SourceChoiceTests(unittest.TestCase):
    def test_vin_census_replaces_fsddb_models_instead_of_adding(self):
        fleet = 1282
        fsddb = {"Unknown model": 1282, "Model Y": 671}
        vin_split = {"total": 1282, "counts": {"Model Y": 709, "Cybercab": 573}, "unrecognized": 0}
        counts, quality, origin = select_model_rows(fleet, fsddb, vin_split)
        self.assertEqual(origin, "vin")
        self.assertEqual(quality, "exact")
        self.assertEqual(counts, {"Model Y": 709, "Cybercab": 573})
        self.assertEqual(sum(counts.values()), fleet)

    def test_disagreement_keeps_fsddb_only(self):
        counts, quality, origin = select_model_rows(
            1282,
            {"Model Y": 400, "Cybercab": 882},
            {"total": 1200, "counts": {"Model Y": 700, "Cybercab": 500}, "unrecognized": 0},
        )
        self.assertEqual(origin, "fsddb")
        self.assertEqual(counts, {"Model Y": 400, "Cybercab": 882})
        self.assertNotIn(700, counts.values())

    def test_failed_census_with_placeholder_models_defers_to_fallback(self):
        self.assertIsNone(select_model_rows(1282, {"Unknown model": 1282}, None))
        self.assertIsNone(choose_vin_counts(1282, None))

    def test_unrecognized_vins_stay_unnamed_and_keep_the_total(self):
        counts, quality = choose_vin_counts(10, {
            "total": 10,
            "counts": {"Model Y": 8},
            "unrecognized": 2,
        })
        self.assertEqual(quality, "partial")
        self.assertEqual(counts["Model Y"], 8)
        self.assertEqual(counts["(unrecognized VIN)"], 2)
        self.assertEqual(sum(counts.values()), 10)

    def test_pages_that_overlap_do_not_double_count(self):
        pages = [
            {"total": 3, "vehicles": [{"vin": vin("7SAY", 1)}, {"vin": vin("5YJA", 1)}]},
            {"total": 3, "vehicles": [{"vin": vin("7SAY", 1)}, {"vin": vin("5YJA", 2)}]},
        ]
        vins = collect_vins(lambda offset: pages[0] if offset == 0 else pages[1], pause=0, sleep=lambda _seconds: None)
        summary = count_vins(vins)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["counts"], {"Model Y": 1, "Cybercab": 2})

    def test_short_census_is_rejected(self):
        pages = [{"total": 3, "vehicles": [{"vin": vin("7SAY", 1)}]}]
        self.assertIsNone(collect_vins(lambda offset: pages[0] if offset == 0 else {"total": 3, "vehicles": []}, pause=0, sleep=lambda _s: None))

    def test_assemble_uses_vin_split_for_changed_tesla_total(self):
        existing = [
            {"date": "2026-11-08", "operator": "Tesla Robotaxi", "model": "Model Y", "count": 671,
             "operator_total": 1244, "source": "s", "quality": "carried_forward"},
            {"date": "2026-11-08", "operator": "Tesla Robotaxi", "model": "Cybercab", "count": 573,
             "operator_total": 1244, "source": "s", "quality": "carried_forward"},
        ]
        data = {"operators": [{
            "name": "Tesla Robotaxi", "fleet_size": 1282, "models": {"Unknown model": 1282},
        }]}
        vin = {"Tesla Robotaxi": {"total": 1282, "counts": {"Model Y": 709, "Cybercab": 573}, "unrecognized": 0}}
        out = [row for row in assemble(existing, data, "2026-11-09", vin) if row["date"] == "2026-11-09"]
        self.assertEqual(
            sorted((row["model"], row["count"], row["quality"]) for row in out),
            [("Cybercab", 573, "exact"), ("Model Y", 709, "exact")],
        )
        self.assertEqual(texas_registered_total(out), 1282)
        self.assertEqual(sum(row["count"] for row in out), 1282)
        self.assertNotIn("(all models)", {row["model"] for row in out})

    def test_history_nov9_tesla_split_matches_the_vin_census(self):
        path = Path(__file__).resolve().parent.parent / "data" / "history.csv"
        with path.open() as handle:
            rows = [row for row in csv.DictReader(handle) if row["date"] == "2026-11-09"]
        tesla = sorted((row["model"], int(row["count"]), int(row["operator_total"]), row["quality"])
                       for row in rows if row["operator"] == "Tesla Robotaxi")
        self.assertEqual(tesla, [
            ("Cybercab", 573, 1282, "exact"),
            ("Model Y", 709, 1282, "exact"),
        ])
        self.assertEqual(texas_registered_total(rows), 3055)
        self.assertEqual(sum(int(row["count"]) for row in rows), 3055)
        self.assertTrue(all("VIN prefixes" in row["source"] for row in rows))

    def test_headline_total_is_not_model_counts_plus_operator_total(self):
        rows = [
            {"operator": "Tesla Robotaxi", "count": 709, "operator_total": 1282},
            {"operator": "Tesla Robotaxi", "count": 573, "operator_total": 1282},
            {"operator": "Waymo", "count": 874, "operator_total": 1297},
            {"operator": "Waymo", "count": 423, "operator_total": 1297},
        ]
        self.assertEqual(texas_registered_total(rows), 1282 + 1297)


class OtherFeedsTests(unittest.TestCase):
    def test_service_area_table_has_no_vehicle_counts(self):
        document = {"areas": [{
            "key": "waymo:austin",
            "provider": "waymo",
            "name": "Austin",
            "isTestRegion": False,
            "boundary": {"geometry": {"type": "Polygon", "coordinates": []}},
            "vehicles": 999,
        }]}
        _features, rows = feature_collection(document)
        self.assertEqual(rows, [{"key": "waymo:austin", "provider": "Waymo", "city": "Austin", "test_region": False}])
        self.assertNotIn("vehicles", rows[0])
        self.assertNotIn("count", rows[0])

    def test_california_activity_is_trips_and_miles(self):
        self.assertEqual(operator_name("PSG0038152"), "Waymo")
        self.assertEqual(operator_name("PSG0039080"), "Cruise")
        self.assertEqual(operator_name("0038380-P"), "Zoox")
        document = {"data": [
            {"operator_tcpid": "PSG0038152", "program": "driverless", "calendar_year": 2026,
             "calendar_month": 4, "total_trips": 10, "total_vmt_all_periods": 100},
            {"operator_tcpid": "PSG0038152", "program": "drivered_pilot", "calendar_year": 2026,
             "calendar_month": 4, "total_trips": 5, "total_vmt_all_periods": 40},
        ]}
        monthly = sum_activity(activity_rows(document), "period", "operator")
        self.assertEqual(len(monthly), 1)
        self.assertEqual(monthly[0]["operator"], "Waymo")
        self.assertEqual(monthly[0]["trips"], 15)
        self.assertEqual(monthly[0]["vmt"], 140)
        self.assertNotIn("operator_total", monthly[0])
        self.assertNotIn("fleet_size", monthly[0])


if __name__ == "__main__":
    unittest.main()
