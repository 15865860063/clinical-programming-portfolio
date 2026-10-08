"""Reproducible synthetic trial demo. Python standard library only."""
import csv
import json
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent


def generate(n=120):
    rng = Random(20261008)
    subjects, events = [], []
    for i in range(1, n + 1):
        uid = f'DEMO-{i:03d}'
        subjects.append(dict(USUBJID=uid, ARM='Active' if i % 2 else 'Placebo',
                             AGE=rng.randint(18, 75), SEX=rng.choice(['M', 'F']),
                             RFSTDTC='2026-01-01'))
        for seq in range(1, rng.randint(0, 3) + 1):
            events.append(dict(USUBJID=uid, AESEQ=seq, AETERM=rng.choice(['Headache', 'Nausea']),
                               AESTDTC='2026-01-10', AEENDTC='2026-01-12',
                               AESEV=rng.choice(['MILD', 'MODERATE', 'SEVERE'])))
    # Retain planted errors; do not silently repair source records.
    subjects[0]['AGE'] = 16
    events.extend([
        dict(USUBJID='DEMO-001', AESEQ=99, AETERM='Headache', AESTDTC='2026-01-14', AEENDTC='2026-01-13', AESEV='MILD'),
        dict(USUBJID='UNKNOWN', AESEQ=1, AETERM='Nausea', AESTDTC='2026-01-10', AEENDTC='2026-01-12', AESEV='MILD'),
    ])
    return subjects, events


def check(subjects, events):
    ids = {s['USUBJID'] for s in subjects}
    issues = []
    for s in subjects:
        if not 18 <= s['AGE'] <= 75:
            issues.append(dict(RULE='DM001', USUBJID=s['USUBJID'], RECORD='DM', MESSAGE='Age outside demo eligibility range'))
    for e in events:
        if e['USUBJID'] not in ids:
            issues.append(dict(RULE='AE001', USUBJID=e['USUBJID'], RECORD=str(e['AESEQ']), MESSAGE='Subject absent from DM'))
        if e['AEENDTC'] < e['AESTDTC']:
            issues.append(dict(RULE='AE002', USUBJID=e['USUBJID'], RECORD=str(e['AESEQ']), MESSAGE='End date precedes start date'))
    return issues


def summarize(subjects, events):
    # All generated subjects assumed dosed; unresolved date errors excluded.
    rows = []
    for arm in ['Active', 'Placebo']:
        ids = {s['USUBJID'] for s in subjects if s['ARM'] == arm}
        affected = {e['USUBJID'] for e in events if e['USUBJID'] in ids and e['AEENDTC'] >= e['AESTDTC']}
        rows.append(dict(ARM=arm, DENOMINATOR=len(ids), SUBJECTS_WITH_AE=len(affected),
                         PERCENT=round(100 * len(affected) / len(ids), 1) if ids else None))
    return rows


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    subjects, events = generate()
    issues = check(subjects, events)
    for name, rows in [('dm', subjects), ('ae', events), ('queries', issues), ('ae_summary', summarize(subjects, events))]:
        write_csv(ROOT / 'results' / f'{name}.csv', rows)
    report = dict(subjects=len(subjects), ae_records=len(events), queries=len(issues),
                  seed=20261008, synthetic=True, status='DEMO_ONLY')
    (ROOT / 'results' / 'run_summary.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
