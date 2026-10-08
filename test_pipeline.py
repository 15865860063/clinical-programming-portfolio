import unittest
from pipeline import generate, check, summarize


class TrialTests(unittest.TestCase):
    def test_planted_errors_are_located(self):
        subjects, events = generate()
        self.assertEqual({(x['RULE'], x['USUBJID']) for x in check(subjects, events)},
                         {('DM001', 'DEMO-001'), ('AE001', 'UNKNOWN'), ('AE002', 'DEMO-001')})
        self.assertEqual(len(check(subjects, events)), 3)

    def test_counts_subjects_instead_of_events(self):
        subjects = [{'USUBJID': 'A', 'ARM': 'Active'}, {'USUBJID': 'B', 'ARM': 'Active'},
                    {'USUBJID': 'C', 'ARM': 'Placebo'}]
        events = [dict(USUBJID='A', AESTDTC='2026-01-01', AEENDTC='2026-01-02')] * 3
        self.assertEqual(summarize(subjects, events)[0],
                         dict(ARM='Active', DENOMINATOR=2, SUBJECTS_WITH_AE=1, PERCENT=50.0))

    def test_reproducible(self):
        self.assertEqual(generate(), generate())

    def test_unresolved_dates_and_unknown_subjects_excluded(self):
        subjects = [{'USUBJID': 'A', 'ARM': 'Active'}, {'USUBJID': 'B', 'ARM': 'Placebo'}]
        events = [dict(USUBJID='A', AESTDTC='2026-01-03', AEENDTC='2026-01-02'),
                  dict(USUBJID='UNKNOWN', AESTDTC='2026-01-01', AEENDTC='2026-01-02')]
        self.assertEqual([r['SUBJECTS_WITH_AE'] for r in summarize(subjects, events)], [0, 0])

    def test_empty_population_does_not_report_zero_percent(self):
        self.assertTrue(all(r['PERCENT'] is None for r in summarize([], [])))

    def test_eligibility_boundaries(self):
        subjects = [dict(USUBJID=str(age), AGE=age) for age in [17, 18, 75, 76]]
        self.assertEqual([r['USUBJID'] for r in check(subjects, [])], ['17', '76'])


if __name__ == '__main__':
    unittest.main()
