"""Guards the unit vocabulary: every config unit has an explicit number format."""
import unittest

from config.inputs import INPUTS
from xl.sheets.common import _UNIT_ROLES
from xl.styles import NUM_FORMATS


class UnitVocabularyTests(unittest.TestCase):
    def test_every_config_unit_has_role(self):
        for rec in INPUTS:
            for unit in (rec.published_unit, rec.model_unit):
                self.assertIn(unit, _UNIT_ROLES,
                              "%s: unit %r has no number-format role" % (rec.id, unit))

    def test_vocabulary_roles_exist(self):
        for unit, role in _UNIT_ROLES.items():
            self.assertIn(role, NUM_FORMATS, "unit %r maps to unknown role %r" % (unit, role))


if __name__ == "__main__":
    unittest.main()
