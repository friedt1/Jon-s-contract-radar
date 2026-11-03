"""Guard the approved 102-agency roster, not just its row count.

An inventory of 102 distinct names can still replace one target with an
unrelated agency. Any intentional roster change must explicitly update this
baseline and be reviewed; this test does not certify live ingestion.
"""
import json
import unittest
from pathlib import Path

EXPECTED_SOURCE_NAMES = frozenset([

    "Allegany County",
    "Arnot Health",
    "Arnot Realty",
    "Athens Area School District",
    "Athens Borough",
    "Bath Central School District",
    "BidNet NY platform",
    "Binghamton City School District",
    "Bradford County PA",
    "Brixmor Property Group",
    "Broome County",
    "CBRE regional property management",
    "Chemung County bids",
    "Chemung County purchasing",
    "City of Binghamton",
    "City of Corning",
    "City of Cortland",
    "City of Geneva",
    "City of Hornell",
    "City of Ithaca",
    "Clinton County PA",
    "Cornell University",
    "Corning Incorporated",
    "Corning Natural Gas",
    "Corning-Painted Post Area School District",
    "Cortland County",
    "Dandy Mini Marts",
    "Elmira City School District",
    "Elmira City bids",
    "Elmira Next local bids",
    "Elmira-Corning Regional Airport",
    "FirstEnergy Penelec",
    "Guthrie Healthcare",
    "Horseheads Central School District",
    "Ithaca City School District",
    "Ithaca College",
    "JLL regional property management",
    "Kimco Realty",
    "Lackawanna County",
    "Livingston County",
    "Lycoming County bids",
    "Mansfield Borough",
    "Mansfield University",
    "Montrose Borough",
    "NYSEG",
    "New York Power Authority",
    "New York State DOT Region 6",
    "New York State DOT Region 9",
    "Norfolk Southern",
    "Northern Tier Career Center",
    "Ontario County",
    "PA DGS construction bids",
    "PA procurement opportunities",
    "PennBid platform",
    "PennDOT District 3",
    "PennDOT District 4",
    "Pennsylvania American Water",
    "Potter County PA",
    "SUNY Corning Community College",
    "Sayre Area School District",
    "Sayre Borough",
    "Schuyler County purchasing",
    "Seneca County",
    "Steuben County bids",
    "Sullivan County PA",
    "Susquehanna County",
    "Tioga Bradford Housing Authority",
    "Tioga County NY",
    "Tioga County PA",
    "Tompkins County purchasing",
    "Towanda Borough",
    "Town of Ashland NY",
    "Town of Big Flats",
    "Town of Corning",
    "Town of Dryden",
    "Town of Elmira",
    "Town of Erwin",
    "Town of Horseheads",
    "Town of Ithaca",
    "Town of Lansing",
    "Town of Southport",
    "Town of Union NY",
    "Town of Vestal",
    "Troy Borough",
    "UPMC Williamsport",
    "Village of Bath",
    "Village of Horseheads",
    "Village of Montour Falls",
    "Village of Owego",
    "Village of Penn Yan",
    "Village of Watkins Glen",
    "Village of Waverly",
    "Watkins Glen Central School District",
    "Waverly Central School District",
    "Wayne County",
    "Wegmans regional properties",
    "Wellsboro Area School District",
    "Wellsboro Borough",
    "Williamsport City",
    "Wyoming County",
    "Wyoming County PA",
    "Yates County"
])


class SourceRosterRegressionTests(unittest.TestCase):
    def test_named_agency_roster_does_not_silently_change(self):
        path = Path(__file__).with_name("sources.json")
        sources = json.loads(path.read_text(encoding="utf-8"))
        actual = [source.get("name") for source in sources]
        self.assertEqual(len(actual), 102)
        self.assertEqual(len(set(actual)), 102)
        self.assertEqual(set(actual), EXPECTED_SOURCE_NAMES,
                         "Named agency inventory changed: review additions/removals explicitly")


if __name__ == "__main__":
    unittest.main()
