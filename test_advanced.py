import unittest
from advanced import (derive_analysis, study_day, analysis_fixture, reconcile,
                      reconciliation_fixture, QueryLedger)


class AnalysisTests(unittest.TestCase):
    def test_latest_predose_and_source_trace(self):
        subjects, measures = analysis_fixture()
        rows = derive_analysis(subjects, measures)
        r = next(r for r in rows if r['USUBJID'] == 'AN-003' and r['SRCSEQ'] == 3)
        self.assertEqual((r['BASE'], r['BASESRCSEQ'], r['CHG'], r['ADY']), (105, 2, -4, 8))
        self.assertAlmostEqual(r['PCHG'], -3.8095)

    def test_missing_baseline_not_imputed(self):
        subjects, measures = analysis_fixture()
        r = next(r for r in derive_analysis(subjects, measures) if r['USUBJID'] == 'AN-001')
        self.assertEqual((r['BASE'], r['CHG'], r['PCHG'], r['BASESRCSEQ']), (None, None, None, None))

    def test_zero_baseline(self):
        subjects, measures = analysis_fixture()
        r = next(r for r in derive_analysis(subjects, measures) if r['USUBJID'] == 'AN-002' and r['SRCSEQ'] == 3)
        self.assertEqual((r['BASE'], r['CHG'], r['PCHG']), (0, 100, None))

    def test_no_day_zero(self):
        self.assertEqual(study_day('2026-01-31', '2026-02-01'), -1)
        self.assertEqual(study_day('2026-02-01', '2026-02-01'), 1)

    def test_at_dose_not_baseline(self):
        s = [dict(USUBJID='A', ARM='Active', DOSE='2026-02-01T09:00:00')]
        m = [dict(USUBJID='A', SEQ=1, TEST='SBP', DATETIME='2026-02-01T09:00:00', VALUE=100)]
        self.assertIsNone(derive_analysis(s, m)[0]['BASE'])

    def test_duplicate_source_key_rejected(self):
        subjects, measures = analysis_fixture()
        with self.assertRaises(ValueError):
            derive_analysis(subjects, measures + [measures[0]])

    def test_unknown_subject_rejected(self):
        with self.assertRaises(ValueError):
            derive_analysis([], [dict(USUBJID='X', SEQ=1)])


class ReconciliationTests(unittest.TestCase):
    def test_all_five_discrepancies_located(self):
        edc, lab = reconciliation_fixture()
        self.assertEqual({(r['RULE'], r['USUBJID']) for r in reconcile(edc, lab)},
                         {('MISSING_LAB', 'LB-001'), ('MISSING_EDC', 'LB-002'),
                          ('UNIT_MISMATCH', 'LB-003'), ('VALUE_MISMATCH', 'LB-004'),
                          ('DUPLICATE_KEY', 'LB-005')})

    def test_tolerance_boundary_and_beyond(self):
        a = dict(USUBJID='A', VISIT='V1', TEST='ALT', VALUE=20.0, UNIT='U/L')
        self.assertEqual(reconcile([a], [dict(a, VALUE=20.01)]), [])
        self.assertEqual(reconcile([a], [dict(a, VALUE=20.011)])[0]['RULE'], 'VALUE_MISMATCH')

    def test_missing_numeric_value_flagged(self):
        a = dict(USUBJID='A', VISIT='V1', TEST='ALT', VALUE=None, UNIT='U/L')
        self.assertEqual(reconcile([a], [a])[0]['RULE'], 'MISSING_VALUE')

    def test_duplicate_does_not_hide_as_many_to_many_match(self):
        a = dict(USUBJID='A', VISIT='V1', TEST='ALT', VALUE=20, UNIT='U/L')
        self.assertEqual(reconcile([a, a], [a, a])[0]['RULE'], 'DUPLICATE_KEY')


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.ledger = QueryLedger()
        self.ledger.open('Q1', 'A', 'dm', 'Check value', '2026-03-01T09:00:00')

    def tearDown(self):
        self.ledger.close()

    def test_cannot_close_without_answer(self):
        with self.assertRaises(ValueError):
            self.ledger.transition('Q1', 'CLOSED', 'dm', 'Reviewed', '2026-03-02T09:00:00')
        self.assertEqual(len(self.ledger.audit_rows()), 1)

    def test_complete_cycle_and_reopen(self):
        self.ledger.transition('Q1', 'ANSWERED', 'site', 'Clarified', '2026-03-02T09:00:00')
        self.ledger.transition('Q1', 'CLOSED', 'dm', 'Reviewed', '2026-03-03T09:00:00')
        self.assertTrue(self.ledger.readiness(True, True, True)['ready'])
        self.ledger.transition('Q1', 'OPEN', 'dm', 'New inconsistency', '2026-03-04T09:00:00')
        self.assertFalse(self.ledger.readiness(True, True, True)['ready'])
        self.assertEqual(len(self.ledger.audit_rows()), 4)

    def test_signoff_gate_remains_required(self):
        self.ledger.transition('Q1', 'ANSWERED', 'site', 'Clarified', '2026-03-02T09:00:00')
        self.ledger.transition('Q1', 'CLOSED', 'dm', 'Reviewed', '2026-03-03T09:00:00')
        self.assertFalse(self.ledger.readiness(True, True, False)['ready'])

    def test_reason_and_chronology_enforced(self):
        for reason, at in [('', '2026-03-02T09:00:00'), ('Answer', '2026-02-28T09:00:00')]:
            with self.assertRaises(ValueError):
                self.ledger.transition('Q1', 'ANSWERED', 'site', reason, at)
        self.assertEqual(len(self.ledger.audit_rows()), 1)

    def test_aging(self):
        self.assertEqual(self.ledger.aging('2026-03-10T09:00:00')[0]['AGE_DAYS'], 9)


if __name__ == '__main__':
    unittest.main()
