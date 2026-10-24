"""Restore missing Firestore data documents from an app-level daily snapshot.

Run from the backend directory. The default mode is a read-only preview;
--apply creates only documents that are currently missing and never overwrites.
"""
import argparse
import sys
from datetime import date

from app.main import DB_MODE, firestore_db


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot_date', help='UTC snapshot date, YYYY-MM-DD')
    parser.add_argument('--apply', action='store_true', help='Create missing documents (no overwrites)')
    args = parser.parse_args()
    try:
        if date.fromisoformat(args.snapshot_date).isoformat() != args.snapshot_date:
            raise ValueError
    except ValueError:
        parser.error('snapshot_date must be a valid YYYY-MM-DD date.')

    if DB_MODE != 'firestore' or firestore_db is None:
        parser.error('Firestore credentials are not configured.')

    day_ref = firestore_db.collection('daily_backups').document(args.snapshot_date)
    metadata = day_ref.get()
    if not metadata.exists or metadata.to_dict().get('status') != 'complete':
        parser.error(f'No completed snapshot exists for {args.snapshot_date}.')

    candidates = []
    already_present = 0
    for snapshot_doc in day_ref.collection('data').stream():
        item = snapshot_doc.to_dict() or {}
        source_id = str(item.get('source_id') or '')
        record = item.get('record')
        if not source_id or not isinstance(record, dict):
            continue
        target = firestore_db.collection('data').document(source_id)
        if target.get().exists:
            already_present += 1
            continue
        candidates.append((target, record))

    print(f"snapshot={args.snapshot_date} backup_records={metadata.to_dict().get('record_count', 0)} "
          f"missing={len(candidates)} already_present={already_present}")
    if not args.apply:
        print('Preview only. Re-run with --apply to create missing documents; existing records will not be overwritten.')
        return

    batch = firestore_db.batch()
    pending = 0
    restored = 0
    for target, record in candidates:
        batch.create(target, record)
        pending += 1
        if pending == 400:
            batch.commit()
            restored += pending
            batch = firestore_db.batch()
            pending = 0
    if pending:
        batch.commit()
        restored += pending
    print(f'restored_missing_documents={restored}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'restore_failed={type(exc).__name__}', file=sys.stderr)
        raise
