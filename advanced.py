"""Three synthetic portfolio projects; not a compliant clinical system."""
import csv
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'results' / 'advanced'


def export(name, rows):
    OUT.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError('Explicit nonempty demo outputs required')
    with (OUT / name).open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def study_day(date, first_dose):
    delta = (datetime.fromisoformat(date).date() - datetime.fromisoformat(first_dose).date()).days
    return delta + 1 if delta >= 0 else delta


def derive_analysis(subjects, measurements):
    """Last nonmissing observation strictly before dose; no imputation."""
    subject_map = {s['USUBJID']: s for s in subjects}
    if len(subject_map) != len(subjects):
        raise ValueError('Duplicate subject')
    keys, grouped = set(), defaultdict(list)
    for record in measurements:
        key = (record['USUBJID'], record['SEQ'])
        if key in keys:
            raise ValueError('Duplicate measurement source key')
        keys.add(key)
        if record['USUBJID'] not in subject_map:
            raise ValueError('Unknown measurement subject')
        if record['VALUE'] is not None:
            grouped[(record['USUBJID'], record['TEST'])].append(record)
    rows = []
    for (uid, test), records in sorted(grouped.items()):
        subject = subject_map[uid]
        dose = datetime.fromisoformat(subject['DOSE'])
        pre = [r for r in records if datetime.fromisoformat(r['DATETIME']) < dose]
        # If timestamps tie, highest source SEQ is the prespecified tie-breaker.
        baseline = max(pre, key=lambda r: (r['DATETIME'], r['SEQ'])) if pre else None
        for record in sorted(records, key=lambda r: (r['DATETIME'], r['SEQ'])):
            value = record['VALUE']
            base = baseline['VALUE'] if baseline else None
            change = value - base if base is not None else None
            rows.append(dict(USUBJID=uid, ARM=subject['ARM'], PARAMCD=test,
                             ADTM=record['DATETIME'], ADY=study_day(record['DATETIME'], subject['DOSE']),
                             AVAL=value, BASE=base, CHG=change,
                             PCHG=round(100 * change / base, 4) if base not in (None, 0) else None,
                             ABLFL='Y' if baseline and baseline['SEQ'] == record['SEQ'] else '',
                             SRCSEQ=record['SEQ'], BASESRCSEQ=baseline['SEQ'] if baseline else None))
    return rows


def analysis_fixture():
    subjects, measures = [], []
    for i in range(1, 41):
        uid = f'AN-{i:03d}'
        subjects.append(dict(USUBJID=uid, ARM='Active' if i % 2 else 'Placebo', DOSE='2026-02-01T09:00:00'))
        values = [100 + i, 102 + i, 98 + i]
        if i == 1:
            values[:2] = [None, None]  # no baseline
        if i == 2:
            values[1] = 0             # percentage undefined
        for seq, (stamp, value) in enumerate(zip(
                ['2026-01-30T08:00:00', '2026-02-01T08:00:00', '2026-02-08T08:00:00'], values), 1):
            measures.append(dict(USUBJID=uid, SEQ=seq, TEST='SBP', DATETIME=stamp, VALUE=value))
    return subjects, measures


def reconcile(edc, lab, tolerance=0.01):
    """Full outer reconciliation; ambiguous duplicate keys never merged."""
    if tolerance < 0:
        raise ValueError('Negative tolerance')
    def index(records):
        result = defaultdict(list)
        for row in records:
            result[(row['USUBJID'], row['VISIT'], row['TEST'])].append(row)
        return result
    left, right = index(edc), index(lab)
    issues = []
    for key in sorted(set(left) | set(right)):
        a, b = left[key], right[key]
        def flag(rule, detail):
            issues.append(dict(RULE=rule, USUBJID=key[0], VISIT=key[1], TEST=key[2], DETAIL=detail))
        if len(a) > 1 or len(b) > 1:
            flag('DUPLICATE_KEY', f'EDC={len(a)}, LAB={len(b)}')
            continue
        if not a:
            flag('MISSING_EDC', 'Lab record absent from EDC')
        elif not b:
            flag('MISSING_LAB', 'EDC record absent from external lab')
        elif a[0]['UNIT'] != b[0]['UNIT']:
            flag('UNIT_MISMATCH', f"EDC={a[0]['UNIT']}, LAB={b[0]['UNIT']}")
        elif a[0]['VALUE'] is None or b[0]['VALUE'] is None:
            flag('MISSING_VALUE', 'One or both numeric results missing')
        elif abs(a[0]['VALUE'] - b[0]['VALUE']) > tolerance + 1e-12:
            flag('VALUE_MISMATCH', f"EDC={a[0]['VALUE']}, LAB={b[0]['VALUE']}")
    return issues


def reconciliation_fixture():
    edc = [dict(USUBJID=f'LB-{i:03d}', VISIT='Week 1', TEST='ALT', VALUE=20.0 + i, UNIT='U/L') for i in range(1, 21)]
    lab = [dict(r) for r in edc]
    lab = [r for r in lab if r['USUBJID'] != 'LB-001']
    edc = [r for r in edc if r['USUBJID'] != 'LB-002']
    next(r for r in lab if r['USUBJID'] == 'LB-003')['UNIT'] = 'IU/L'
    next(r for r in lab if r['USUBJID'] == 'LB-004')['VALUE'] = 999.0
    lab.append(dict(next(r for r in lab if r['USUBJID'] == 'LB-005')))
    return edc, lab


class QueryLedger:
    """Educational SQLite status ledger, no production access controls."""
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS queries (
            id TEXT PRIMARY KEY, subject TEXT NOT NULL, status TEXT NOT NULL,
            opened TEXT NOT NULL, changed TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS audit (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, query_id TEXT NOT NULL,
            old_status TEXT NOT NULL, new_status TEXT NOT NULL,
            actor TEXT NOT NULL, reason TEXT NOT NULL, at TEXT NOT NULL);
        """)

    def open(self, qid, subject, actor, reason, at):
        datetime.fromisoformat(at)
        if not all([qid, subject, actor, reason]):
            raise ValueError('Required field empty')
        with self.db:
            self.db.execute('INSERT INTO queries VALUES (?,?,?,?,?)', (qid, subject, 'OPEN', at, at))
            self.db.execute('INSERT INTO audit(query_id,old_status,new_status,actor,reason,at) VALUES (?,?,?,?,?,?)',
                            (qid, '', 'OPEN', actor, reason, at))

    def transition(self, qid, target, actor, reason, at):
        transitions = {'OPEN': {'ANSWERED'}, 'ANSWERED': {'CLOSED', 'OPEN'}, 'CLOSED': {'OPEN'}}
        row = self.db.execute('SELECT * FROM queries WHERE id=?', (qid,)).fetchone()
        if row is None:
            raise ValueError('Unknown query')
        if target not in transitions[row['status']]:
            raise ValueError('Illegal transition')
        if not actor.strip() or not reason.strip():
            raise ValueError('Actor and reason required')
        if datetime.fromisoformat(at) < datetime.fromisoformat(row['changed']):
            raise ValueError('Audit timestamp precedes previous event')
        with self.db:
            self.db.execute('UPDATE queries SET status=?,changed=? WHERE id=?', (target, at, qid))
            self.db.execute('INSERT INTO audit(query_id,old_status,new_status,actor,reason,at) VALUES (?,?,?,?,?,?)',
                            (qid, row['status'], target, actor, reason, at))

    def readiness(self, reconciled, reviewed, signed):
        unresolved = self.db.execute("SELECT count(*) FROM queries WHERE status != 'CLOSED'").fetchone()[0]
        checks = dict(no_unresolved_queries=unresolved == 0, external_data_reconciled=reconciled,
                      data_review_complete=reviewed, investigator_signoff=signed)
        return dict(ready=all(checks.values()), unresolved_queries=unresolved, checks=checks)

    def aging(self, as_of):
        date = datetime.fromisoformat(as_of)
        rows = []
        for q in self.db.execute("SELECT * FROM queries WHERE status != 'CLOSED' ORDER BY id"):
            days = (date.date() - datetime.fromisoformat(q['opened']).date()).days
            if days < 0:
                raise ValueError('As-of date before query creation')
            rows.append(dict(QUERY_ID=q['id'], STATUS=q['status'], AGE_DAYS=days))
        return rows

    def audit_rows(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM audit ORDER BY event_id')]

    def close(self):
        self.db.close()


def main():
    subjects, measures = analysis_fixture()
    analysis = derive_analysis(subjects, measures)
    export('analysis_subjects.csv', subjects)
    export('source_measurements.csv', measures)
    export('analysis_sbp.csv', analysis)
    edc, lab = reconciliation_fixture()
    issues = reconcile(edc, lab)
    export('edc_lab.csv', edc)
    export('external_lab.csv', lab)
    export('lab_reconciliation.csv', issues)
    OUT.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / 'query_ledger.sqlite'
    if ledger_path.exists():
        raise FileExistsError('Use a fresh results directory to preserve existing query audit')
    ledger = QueryLedger(str(ledger_path))
    try:
        for i in range(1, 4):
            ledger.open(f'Q{i}', f'DM-{i:03d}', 'demo_dm', 'Synthetic discrepancy', '2026-03-01T09:00:00')
        ledger.transition('Q1', 'ANSWERED', 'demo_site', 'Source record clarified', '2026-03-02T09:00:00')
        ledger.transition('Q1', 'CLOSED', 'demo_dm', 'Response reviewed', '2026-03-03T09:00:00')
        export('query_aging_before_resolution.csv', ledger.aging('2026-03-10T09:00:00'))
        before = ledger.readiness(False, True, False)
        for i in [2, 3]:
            ledger.transition(f'Q{i}', 'ANSWERED', 'demo_site', 'Source record clarified', '2026-03-10T10:00:00')
            ledger.transition(f'Q{i}', 'CLOSED', 'demo_dm', 'Response reviewed', '2026-03-10T11:00:00')
        after = ledger.readiness(True, True, True)
        export('query_audit.csv', ledger.audit_rows())
    finally:
        ledger.close()
    report = dict(synthetic=True, analysis_subjects=len(subjects), source_measurements=len(measures),
                  analysis_records=len(analysis), lab_issues=len(issues), query_audit_events=9,
                  readiness_before=before, readiness_after=after,
                  compliance='Educational only; no CDISC conformance or validated EDC claim')
    (OUT / 'summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
