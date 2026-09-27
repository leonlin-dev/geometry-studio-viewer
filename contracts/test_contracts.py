"""Tests for the contract validators.

Run: python -m unittest contracts.test_contracts contracts.test_protocol_v1
     (`discover -s contracts` does not work here: these modules use
      relative imports, so they must be named as package modules.)
or:  python -m contracts validate tests/good/manifest.json (CLI smoke).
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from . import validate_manifest_v1, validate_case_v1, ContractError
from .case_v1 import SUPPORTED_CASE_VERSIONS
from .manifest_v1 import MANIFEST_V1
from .case_v1 import CASE_V1
from .__main__ import _classify
from .manifest_v1 import MANIFEST_V1
from .case_v1 import CASE_V1


# ---------- Test fixtures -------------------------------------------------

def _make_manifest():
    return {
        "schema_version": MANIFEST_V1,
        "version": "1.0",
        "count": 1,
        "cases": [
            {
                "file": "gallery_outputs/case_xyz.json",
                "id": "case_xyz",
                "name": "Sample Case",
                "tags": ["profile:open", "scheme:analytic-cp"],
                "type": "LoftedSurface",
                "version": "1.0",
            }
        ],
    }


def _make_case():
    return {
        "schema_version": CASE_V1,
        "caseName": "Sample Case",
        "curves": [
            {
                "control_points": [
                    {"x": 0.0, "y": 0.0, "z": 0.0},
                    {"x": 1.0, "y": 0.0, "z": 0.0},
                    {"x": 1.0, "y": 1.0, "z": 0.0},
                    {"x": 0.0, "y": 1.0, "z": 0.0},
                ],
                "is_periodic": False,
                "knots": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                "label": "section_0",
                "p": 2,
                "t_max": 1.0,
                "t_min": 0.0,
                "type": "section",
            }
        ],
        "geometry": {
            "type": "LoftedSurface",
            "mesh": {
                "vertices": [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0],
                "normals":  [0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0],
                "indices":  [0, 1, 2],
            },
            "nurbs": {
                "curves": [],
                "surfaces": [],
                "support_surfaces": [],
                "constraint_visualizations": [],
            },
            "debugMarkers": {"singularities": []},
        },
    }


# ---------- Manifest tests ------------------------------------------------

class ManifestV1Tests(unittest.TestCase):

    def test_accepts_canonical(self):
        validate_manifest_v1(_make_manifest())  # no raise

    def test_rejects_wrong_schema_version(self):
        m = _make_manifest()
        m["schema_version"] = "2.0"
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_SCHEMA_VERSION")

    def test_rejects_missing_schema_version(self):
        m = _make_manifest()
        del m["schema_version"]
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "MISSING_KEY")

    def test_rejects_count_mismatch(self):
        m = _make_manifest()
        m["count"] = 99
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "COUNT_MISMATCH")

    def test_rejects_empty_cases(self):
        m = _make_manifest()
        m["cases"] = []
        m["count"] = 0
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "LIST_TOO_SHORT")

    def test_rejects_duplicate_ids(self):
        m = _make_manifest()
        m["cases"].append(dict(m["cases"][0]))
        m["count"] = 2
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "DUPLICATE_ID")

    def test_rejects_non_json_extension(self):
        m = _make_manifest()
        m["cases"][0]["file"] = "no_extension"
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "BAD_FILE_EXT")

    def test_rejects_absolute_path(self):
        m = _make_manifest()
        m["cases"][0]["file"] = "/abs/path.json"
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "BAD_FILE_PATH")

    def test_rejects_undeclared_tag_prefix(self):
        m = _make_manifest()
        m["cases"][0]["tags"].append("garbage:tag")
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "TAG_PREFIX_UNKNOWN")

    def test_rejects_invalid_case_type(self):
        m = _make_manifest()
        m["cases"][0]["type"] = "MysteryMesh"
        with self.assertRaises(ContractError) as ctx:
            validate_manifest_v1(m)
        self.assertEqual(ctx.exception.code, "ENUM_VIOLATION")


# ---------- Case tests ---------------------------------------------------

class CaseV1Tests(unittest.TestCase):

    def test_accepts_canonical(self):
        validate_case_v1(_make_case())

    def test_rejects_wrong_schema_version(self):
        c = _make_case()
        c["schema_version"] = "9.9"
        with self.assertRaises(ContractError) as ctx:
            validate_case_v1(c)
        self.assertEqual(ctx.exception.code, "UNSUPPORTED_SCHEMA_VERSION")

    def test_rejects_mesh_length_mismatch(self):
        c = _make_case()
        c["geometry"]["mesh"]["vertices"] = [0.0, 0.0, 0.0]  # only 1 vertex
        with self.assertRaises(ContractError) as ctx:
            validate_case_v1(c)
        # normals has 3, mismatch -> MESH_LENGTH_MISMATCH (or LENGTH_INVALID)
        self.assertIn(ctx.exception.code,
                      ("MESH_LENGTH_MISMATCH", "MESH_LENGTH_INVALID"))

    def test_rejects_knots_too_short(self):
        c = _make_case()
        c["curves"][0]["knots"] = [0.0, 0.0]  # way short
        with self.assertRaises(ContractError) as ctx:
            validate_case_v1(c)
        self.assertEqual(ctx.exception.code, "KNOTS_TOO_SHORT")

    def test_rejects_t_range_inverted(self):
        c = _make_case()
        c["curves"][0]["t_min"] = 1.0
        c["curves"][0]["t_max"] = 0.0
        with self.assertRaises(ContractError) as ctx:
            validate_case_v1(c)
        self.assertEqual(ctx.exception.code, "T_RANGE_INVALID")

    def test_rejects_point3_missing_component(self):
        c = _make_case()
        del c["curves"][0]["control_points"][0]["z"]
        with self.assertRaises(ContractError) as ctx:
            validate_case_v1(c)
        self.assertEqual(ctx.exception.code, "MISSING_KEY")


if __name__ == "__main__":
    unittest.main()


class CaseVersionAcceptanceTests(unittest.TestCase):
    """The envelope versions the corpus actually emits must validate.

    The validator's allowlist and the CLI's dispatch had drifted apart
    silently: the allowlist said {1.0, 1.1} while the dispatch tested
    sv == "1.0" exactly, and neither mentioned 1.2, which 30-data had been
    emitting for some time. Nothing ran the CLI over the corpus, so the gap
    went unnoticed. These tests pin the two together.
    """

    @staticmethod
    def _case(schema_version: str) -> dict:
        # Every key validate_case_v1 requires, with the types it requires.
        # Only schema_version varies between subtests -- if accepting a
        # version needed anything else relaxed, these tests would say so.
        return {
            "schema_version": schema_version,
            "caseName": "version-acceptance",
            "curves": [],
            "surfaces": [],
            "support_surfaces": [],
            "constraint_visualizations": [],
            "expected_metrics": {"tolerance": 1e-6},
            # Mirrors the v1.0 skeleton documented at the top of case_v1.py.
            # mesh and debugMarkers are both required, and mesh carries its own
            # invariants (vertices == normals, each a multiple of 3; indices a
            # multiple of 3), so empty lists are the smallest legal values
            # rather than an oversight.
            "geometry": {
                "type": "LoftedSurface",
                "mesh": {"vertices": [], "normals": [], "indices": []},
                "nurbs": {
                    "curves": [], "surfaces": [],
                    "support_surfaces": [], "constraint_visualizations": [],
                },
                "debugMarkers": {"singularities": []},
            },
        }

    def test_accepts_every_version_in_the_allowlist(self):
        # The whole point: a version being in the allowlist must be enough.
        for sv in sorted(SUPPORTED_CASE_VERSIONS):
            with self.subTest(schema_version=sv):
                validate_case_v1(self._case(sv))

    def test_rejects_a_version_outside_the_allowlist(self):
        # 2.0 stays rejected, so the allowlist still means something.
        with self.assertRaises(ContractError):
            validate_case_v1(self._case("2.0"))

    def test_corpus_versions_are_all_accepted(self):
        # 1.2 predates the allowlist and 1.3 is the current envelope; both
        # must validate, otherwise this validator is useless as a CI gate.
        for sv in ("1.2", "1.3"):
            with self.subTest(schema_version=sv):
                validate_case_v1(self._case(sv))


class DispatchShapeTests(unittest.TestCase):
    """Dispatch must not be decided by schema_version.

    MANIFEST_V1 and CASE_V1 are both "1.0", so a dispatch that branches on
    the version sends every 1.0 case envelope to the manifest validator, which
    then fails on the missing "cases" list. Classification is by shape.
    """

    def test_classifies_manifest_by_cases_list(self):
        self.assertEqual(_classify({"schema_version": "1.0",
                                    "cases": [{"file": "a.json"}]}), "manifest")

    def test_classifies_case_by_case_name(self):
        # schema_version 1.0 on purpose: the version that used to send this
        # to the manifest validator.
        self.assertEqual(_classify({"schema_version": "1.0",
                                    "caseName": "c"}), "case")

    def test_classifies_current_envelope_as_case(self):
        self.assertEqual(_classify({"schema_version": "1.3",
                                    "caseName": "c"}), "case")

    def test_rejects_an_unrecognisable_document(self):
        self.assertIsNone(_classify({"schema_version": "1.3"}))

    def test_manifest_and_case_versions_are_both_one_point_zero(self):
        # Documents the collision these tests exist to pin down, so a future
        # edit that "fixes" one of the constants notices the coupling.
        self.assertEqual(MANIFEST_V1, CASE_V1)
