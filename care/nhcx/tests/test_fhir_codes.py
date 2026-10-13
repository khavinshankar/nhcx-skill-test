from django.test import SimpleTestCase

from care.nhcx.fhir import codes


class CodesTests(SimpleTestCase):
    def test_profile_urls(self):
        self.assertEqual(
            codes.profile("Claim"),
            "https://nrces.in/ndhm/fhir/r4/StructureDefinition/Claim",
        )
        for name in (
            "ClaimBundle",
            "TaskBundle",
            "CoverageEligibilityRequestBundle",
            "Patient",
            "Coverage",
            "Organization",
            "Practitioner",
            "Task",
            "Communication",
        ):
            self.assertTrue(codes.PROFILES[name].startswith(codes.PROFILE_BASE))

    def test_coding_leaves_out_empty_parts(self):
        self.assertEqual(codes.coding(None, "x"), {"code": "x"})
        self.assertEqual(
            codes.coding(codes.SNOMED, "1", "One"),
            {"system": codes.SNOMED, "code": "1", "display": "One"},
        )

    def test_identifier_type(self):
        concept = codes.identifier_type("CLN")
        self.assertEqual(concept["coding"][0]["code"], "CLN")
        self.assertEqual(concept["coding"][0]["system"], codes.NDHM_IDENTIFIER_TYPE)
        self.assertEqual(
            codes.identifier_type("MB")["coding"][0]["system"], codes.V2_0203
        )

    def test_gender(self):
        self.assertEqual(codes.gender("M"), "male")
        self.assertEqual(codes.gender("Female"), "female")
        self.assertEqual(codes.gender(""), "")

    def test_degree_codes(self):
        cases = {
            "BSc Nursing": "RN",
            "PhD Pharmacology": "PHD",
            "MBBS, MS (Ortho)": "MS",
            "MCh Neurosurgery": "MS",
            "DO": "DO",
            "BDS": "DDS",
            "GNM": "RN",
            "MBBS": "MD",
            "": "MD",
        }
        for text, code in cases.items():
            with self.subTest(text=text):
                self.assertEqual(codes.degree_code(text)[0], code)
        self.assertEqual(codes.degree_code("MBBS")[1], "Doctor of Medicine")

    def test_reason_word(self):
        self.assertEqual(
            codes.reason_word("additionalinfo"), "Additional information request"
        )
        self.assertEqual(codes.reason_word("oddcode"), "oddcode")

    def test_lookups(self):
        tables = codes.lookups()
        for key in (
            "identifier_types",
            "degrees",
            "eligibility_purposes",
            "cancel_reasons",
            "reprocess_reasons",
            "query_reasons",
            "profiles",
        ):
            self.assertIn(key, tables)
        self.assertIn("auth-requirements", tables["eligibility_purposes"])
