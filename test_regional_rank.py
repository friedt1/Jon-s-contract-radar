import unittest
from regional_rank import classify, build
class RegionalRankTests(unittest.TestCase):
    def test_excludes_unrelated(self):
        self.assertIsNone(classify({"title":"Office chairs","url":"https://example.gov/notice"}))
    def test_excludes_over_twelve_hours(self):
        self.assertIsNone(classify({"title":"Disaster debris removal","url":"https://example.gov/notice","drive_hours":13}))
    def test_missing_travel_not_verified(self):
        x=classify({"title":"State DOT vegetation management","url":"https://example.gov/notice","travel_verified":True})
        self.assertFalse(x["travel_verified"])
    def test_high_priority_large_disaster(self):
        x=classify({"title":"Disaster debris removal","url":"https://example.gov/notice","drive_hours":8,"travel_verified":True,"estimated_value_usd":500000,"estimated_duration_days":30})
        self.assertEqual(x["priority"],"high")
        self.assertTrue(x["travel_verified"])
    def test_nonfinite_or_boolean_drive_times_cannot_be_verified(self):
        for value in ("nan", "NaN", float("nan"), "inf", "-inf", True, False, "unknown"):
            with self.subTest(value=repr(value)):
                x = classify({"title": "Tree removal", "url": "https://example.gov/bid",
                              "drive_hours": value, "travel_verified": True})
                self.assertIsNotNone(x)
                self.assertIsNone(x["drive_hours"])
                self.assertFalse(x["travel_verified"])
                self.assertEqual(x["distance_status"], "unverified")

    def test_truthy_string_is_not_routing_verification(self):
        for flag in ("false", "true", "yes", 1, [], None):
            with self.subTest(flag=flag):
                x = classify({"title": "Vegetation management",
                              "url": "https://example.gov/bid",
                              "drive_hours": 2, "travel_verified": flag})
                self.assertFalse(x["travel_verified"])
                self.assertEqual(x["distance_status"], "unverified")

    def test_finite_route_boundaries_and_negative_hours(self):
        base = {"title": "Storm cleanup", "url": "https://example.gov/bid",
                "travel_verified": True}
        self.assertTrue(classify(dict(base, drive_hours=12))["travel_verified"])
        self.assertIsNone(classify(dict(base, drive_hours=12.01)))
        self.assertIsNone(classify(dict(base, drive_hours=-1)))

    def test_nonfinite_values_cannot_inflate_priority(self):
        base = {"title": "Tree removal", "url": "https://example.gov/bid"}
        for bad in ("inf", float("nan"), True, -100):
            with self.subTest(bad=repr(bad)):
                x = classify(dict(base, estimated_value_usd=bad,
                                  estimated_duration_days=bad))
                self.assertEqual(x["priority_score"], 0)
                self.assertEqual(x["priority"], "review")

    def test_past_deadline_and_closed_publisher_states_are_excluded(self):
        base = {"title": "Tree removal", "url": "https://county.example/bids?bidID=12"}
        today = __import__("datetime").date(2026, 10, 29)
        self.assertIsNone(classify(dict(base, deadline="2026-10-28"), today=today))
        self.assertIsNone(classify(dict(base, deadline="2026-11-30",
                                        open_status="detail_listed_awarded"), today=today))
        self.assertIsNone(classify(dict(base, status="Cancelled"), today=today))
        self.assertIsNone(classify(dict(base, open_status="listing_closed"), today=today))
        # Historical Erie tree/stump example: never treat its expired cutoff as live.
        erie = dict(base, title="Tree & Stump Removal", deadline="2026-10-28")
        self.assertEqual(build([erie], today=today)["opportunities"], [])

    def test_same_day_and_unknown_deadline_are_review_only(self):
        today = __import__("datetime").date(2026, 10, 29)
        base = {"title": "Vegetation management", "url": "https://county.example/bid"}
        same_day = classify(dict(base, deadline="2026-10-29"), today=today)
        self.assertEqual(same_day["deadline_status"], "stated_unverified")
        self.assertEqual(same_day["status"], "review required")
        unknown = classify(base, today=today)
        self.assertEqual(unknown["deadline_status"], "unknown")
        invalid = classify(dict(base, deadline="tomorrow"), today=today)
        self.assertEqual(invalid["deadline_status"], "invalid")
        self.assertEqual(invalid["status"], "review required")

    def test_unrelated_owego_demolition_never_enters_regional_tree_feed(self):
        today = __import__("datetime").date(2026, 10, 29)
        notice = {"title": "67 Central Avenue Demolition Rebid",
                  "summary": "Building demolition and site restoration in Owego",
                  "deadline": "2026-11-13", "url": "https://county.example/bid"}
        self.assertEqual(build([notice], today=today)["opportunities"], [])

    def test_rejects_credentialed_or_malformed_https_urls(self):
        for url in ("https://user:pass@county.example/bid",
                    "https://county.example/bid\\n",
                    "https://[bad/bid", "https://county.example/bid\\\\bad"):
            with self.subTest(url=url):
                self.assertIsNone(classify({"title": "Tree removal", "url": url}))

    def test_tracking_duplicates_collapse_but_distinct_bid_ids_remain(self):
        today = __import__("datetime").date(2026, 10, 29)
        base = {"title": "Storm cleanup", "url": "https://COUNTY.example/bids?bidID=12",
                "summary": "Short description"}
        variant = dict(base, url="https://county.example:443/bids?bidID=12&utm_source=mail",
                       estimated_value_usd=500000)
        distinct = dict(base, url="https://county.example/bids?bidID=13")
        result = build([base, variant, distinct], today=today)["opportunities"]
        self.assertEqual(len(result), 2)
        self.assertEqual(len({x["url"] for x in result}), 2)
        self.assertEqual(next(x for x in result if "bidID=12" in x["url"])["priority_score"], 3)
        self.assertTrue(all(x["status"] == "review required" for x in result))


    def test_same_day_explicit_eastern_cutoff_is_excluded_from_review(self):
        # Synthetic historical Erie-style fixture; never a live contract.
        import datetime as dt
        today = dt.date(2026, 10, 29)
        erie = {"title": "Tree and stump removal", "url": "https://county.example/bids/12",
                "deadline": "2026-10-29", "deadline_time": "9:00 AM",
                "status": "unverified"}
        before = dt.datetime(2026, 10, 29, 12, 59, tzinfo=dt.timezone.utc)
        cutoff = dt.datetime(2026, 10, 29, 13, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(classify(erie, today=today, now=before)["status"], "review required")
        self.assertIsNone(classify(erie, today=today, now=cutoff))
        self.assertEqual(build([erie], today=today, now=cutoff)["opportunities"], [])

    def test_unknown_clock_timezone_or_naive_now_does_not_invent_expiry(self):
        import datetime as dt
        today = dt.date(2026, 10, 29)
        after = dt.datetime(2026, 10, 29, 14, tzinfo=dt.timezone.utc)
        base = {"title": "Tree removal", "url": "https://county.example/bids/13",
                "deadline": "2026-10-29"}
        for field in ({}, {"deadline_time": "time unknown"},
                      {"deadline_time": "9:00 AM", "deadline_timezone": "Pacific"}):
            with self.subTest(field=field):
                item = classify(dict(base, **field), today=today, now=after)
                self.assertEqual(item["deadline_status"], "stated_unverified")
                self.assertEqual(item["status"], "review required")
        naive = dt.datetime(2026, 10, 29, 14)
        self.assertIsNotNone(classify(dict(base, deadline_time="9:00 AM"),
                                      today=today, now=naive))

    def test_future_cutoff_remains_review_only_and_eastern_dst_is_honored(self):
        import datetime as dt
        today = dt.date(2026, 10, 29)
        now = dt.datetime(2026, 10, 29, 20, tzinfo=dt.timezone.utc)
        future = {"title": "Storm cleanup", "url": "https://county.example/bids/14",
                  "deadline": "2026-10-30", "deadline_time": "9:00 AM"}
        self.assertEqual(classify(future, today=today, now=now)["deadline_status"],
                         "stated_unverified")
        # On October 29 EDT, 13:00 UTC is 9:00 AM local; not 8:00 or 10:00.
        local = dt.datetime(2026, 10, 29, 13, tzinfo=dt.timezone.utc)
        same_day = dict(future, deadline="2026-10-29")
        self.assertIsNone(classify(same_day, today=today, now=local))

    def test_stump_removal_wording_is_relevant_but_never_verified(self):
        import datetime as dt
        today = dt.date(2026, 10, 29)
        for title in ("Tree & Stump Removal", "Tree and Stump Removal",
                      "Stump Grinding"):
            with self.subTest(title=title):
                notice = {"title": title, "url": "https://county.example/bids/20",
                          "deadline": "2026-11-01"}
                item = classify(notice, today=today)
                self.assertIsNotNone(item)
                self.assertEqual(item["status"], "review required")
                self.assertEqual(item["deadline_status"], "stated_unverified")
                self.assertIsNone(classify(dict(notice, deadline="2026-10-28"),
                                           today=today))

    def test_publisher_closed_duplicate_withholds_stale_open_copy(self):
        # Synthetic Erie-style tree/stump records, NOT actual live bids.
        import datetime as dt
        today = dt.date(2026, 10, 29)
        open_copy = {"title": "Tree and stump removal",
                     "url": "https://county.example/bids?bidID=12",
                     "deadline": "2026-11-20",
                     "open_status": "listing_open"}
        closed_copy = dict(open_copy,
                           url="https://county.example/bids?utm_source=mail&bidID=12",
                           open_status="detail_listed_awarded")
        for notices in ([open_copy, closed_copy], [closed_copy, open_copy]):
            with self.subTest(order=notices[0]["open_status"]):
                self.assertEqual(build(notices, today=today)["opportunities"], [])
        # An unrelated bid number must not be suppressed by a closure.
        other_bid = dict(open_copy, url="https://county.example/bids?bidID=13")
        retained = build([open_copy, closed_copy, other_bid], today=today)["opportunities"]
        self.assertEqual(len(retained), 1)
        self.assertIn("bidID=13", retained[0]["url"])
        self.assertEqual(retained[0]["status"], "review required")

    def test_expired_duplicate_does_not_override_later_deadline(self):
        # An older deadline alone is not a publisher cancellation or award.
        import datetime as dt
        today = dt.date(2026, 10, 29)
        old = {"title": "Tree removal",
               "url": "https://county.example/bids?bidID=22",
               "deadline": "2026-10-28"}
        amended = dict(old, deadline="2026-11-20")
        retained = build([old, amended], today=today)["opportunities"]
        self.assertEqual(len(retained), 1)
        self.assertEqual(retained[0]["deadline"], "2026-11-20")
        # Owego demolition is unrelated regardless of publisher status.
        owego = {"title": "Owego demolition rebid",
                 "url": "https://county.example/bids?bidID=23",
                 "deadline": "2026-11-13"}
        self.assertEqual(build([owego], today=today)["opportunities"], [])

    def test_duplicate_future_deadlines_are_flagged_not_silently_selected(self):
        # Synthetic Erie-style notices only; these are not real open bids.
        import datetime as dt
        today = dt.date(2026, 10, 29)
        old = {"title": "Tree and stump removal",
               "url": "https://county.example/bids?bidID=91",
               "deadline": "2026-11-05",
               "estimated_value_usd": 500000}
        amended = dict(old, url=old["url"] + "&utm_source=mail",
                       deadline="2026-11-20", estimated_value_usd=0)
        for notices in ([old, amended], [amended, old]):
            with self.subTest(first=notices[0]["deadline"]):
                items = build(notices, today=today)["opportunities"]
                self.assertEqual(len(items), 1)
                item = items[0]
                self.assertEqual(item["deadline_status"], "conflicting_unverified")
                self.assertEqual(item["deadline"], "")
                self.assertEqual(item["deadline_time"], "")
                self.assertEqual(item["deadline_conflict"],
                                 ["2026-11-05", "2026-11-20"])
                self.assertEqual(item["status"], "review required")

    def test_duplicate_same_day_clock_conflict_is_review_only(self):
        import datetime as dt
        today = dt.date(2026, 10, 29)
        before = dt.datetime(2026, 10, 29, 12, tzinfo=dt.timezone.utc)
        first = {"title": "Vegetation management",
                 "url": "https://county.example/bids?bidID=92",
                 "deadline": "2026-10-29", "deadline_time": "9:00 AM"}
        second = dict(first, deadline_time="2:00 PM")
        items = build([first, second], today=today, now=before)["opportunities"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["deadline"], "2026-10-29")
        self.assertEqual(items[0]["deadline_time"], "")
        self.assertEqual(items[0]["deadline_status"], "conflicting_unverified")
        self.assertEqual(items[0]["deadline_conflict"], ["2:00 pm", "9:00 am"])
        self.assertEqual(items[0]["status"], "review required")

    def test_distinct_bid_ids_do_not_create_false_deadline_conflicts(self):
        import datetime as dt
        today = dt.date(2026, 10, 29)
        first = {"title": "Tree removal", "deadline": "2026-11-05",
                 "url": "https://county.example/bids?bidID=93"}
        second = dict(first, deadline="2026-11-20",
                      url="https://county.example/bids?bidID=94")
        items = build([first, second], today=today)["opportunities"]
        self.assertEqual(len(items), 2)
        self.assertTrue(all(x["deadline_status"] == "stated_unverified" for x in items))
        self.assertTrue(all("deadline_conflict" not in x for x in items))
        owego = {"title": "Owego demolition rebid",
                 "url": "https://county.example/bids?bidID=95",
                 "deadline": "2026-11-13"}
        self.assertEqual(build([owego], today=today)["opportunities"], [])

    def test_permuted_query_keys_cannot_leave_stale_open_bid_in_review(self):
        # Synthetic Erie-style tree/stump notices; not live opportunities.
        import datetime as dt
        today = dt.date(2026, 10, 29)
        open_copy = {"title": "Tree and stump removal",
                     "url": "https://county.example/bids?bidID=12&ref=vendor",
                     "deadline": "2026-11-20", "open_status": "listing_open"}
        closed_copy = dict(open_copy,
                           url="https://county.example/bids?ref=vendor&bidID=12&utm_source=mail",
                           open_status="detail_listed_awarded")
        for pair in ([open_copy, closed_copy], [closed_copy, open_copy]):
            self.assertEqual(build(pair, today=today)["opportunities"], [])
        distinct = dict(open_copy, url="https://county.example/bids?bidID=13&ref=vendor")
        self.assertEqual(len(build([open_copy, closed_copy, distinct],
                                   today=today)["opportunities"]), 1)
        owego = {"title": "Owego demolition rebid",
                 "url": "https://county.example/bids?bidID=14&ref=vendor",
                 "deadline": "2026-11-13"}
        self.assertEqual(build([owego], today=today)["opportunities"], [])

    def test_no_invented_notices(self):
        self.assertEqual(build([])["opportunities"],[])
if __name__ == "__main__": unittest.main()
