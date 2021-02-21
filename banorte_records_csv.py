import sys
import os
import pathlib
import json
import base64
import csv
import dataclasses
from decimal import Decimal
from datetime import datetime
from pytz import timezone
from collections import defaultdict
from banes import banorte_email
from banes import records


def extra_amount_total(extra_amount):
    return Decimal(extra_amount.amount) + Decimal(extra_amount.tax)


def calculate_total_amount(record):
    has_extra_amounts = record.type == records.EXPENSE_RECORD_TYPE and record.extra_amounts is not None
    _extra_amount_total = sum([extra_amount_total(ea) for ea in record.extra_amounts])\
        if has_extra_amounts else Decimal(0)

    return Decimal(record.amount) + _extra_amount_total


def make_csv_row(record, email_metadata):
    return dict({
        'type': record.type,
        'source': record.source,
        'total_amount': calculate_total_amount(record),
        'note': record.note,
        'operation_date': record.operation_date,
        'application_date': record.application_date if record.type == records.EXPENSE_RECORD_TYPE else None,
        'raw': json.dumps(dataclasses.asdict(record), default=str),
    }, **email_metadata)


def make_period_csv(period, rows):
    fieldnames = [
        'type',
        'source',
        'total_amount',
        'note',
        'operation_date',
        'application_date',
        'raw',
        'email_id',
        'email_from',
        'email_timestamp',
        'email_date',
    ]

    with open(f'period_records/{period}-{len(rows)}.csv', 'w', newline='') as records_csv:
        csv_writer = csv.DictWriter(records_csv, fieldnames=fieldnames)

        csv_writer.writeheader()

        for row in rows:
            csv_writer.writerow(row)


def main():
    input_folder = sys.argv[1]

    try:
        os.mkdir('failures')
    except FileExistsError:
        pass

    try:
        os.mkdir('period_records')
    except FileExistsError:
        pass

    period_csv_rows = defaultdict(list)

    for path in pathlib.Path(input_folder).glob(f'*.json'):
        with path.open() as json_email:

            try:
                email_content = json.loads(json_email.read())
                email_body = str(base64.urlsafe_b64decode(email_content['body'].encode('ascii')), 'utf-8')
                email_id = email_content['id']
                email_timestamp = email_content['internal_date']
                date = datetime.fromtimestamp(email_timestamp / 1000.0, tz=timezone('America/Mexico_City'))
                email_metadata = {
                    'email_id': email_id,
                    'email_from': email_content['from'],
                    'email_timestamp': email_timestamp,
                    'email_date': date.isoformat(),
                }
                record = banorte_email.scrape(email_body)
                if record.type is not records.ACCOUNT_OPERATION_TYPE:
                    period = f'{date.year}-{date.month}'
                    row = make_csv_row(record, email_metadata)

                    period_csv_rows[period].append(row)
            except Exception as e:
                print(f'{email_id} - {e}')

                with open(f'./failures/{email_id}.html', 'w') as email_file:
                    email_file.write(email_body)

    for period, csv_rows in period_csv_rows.items():
        print(period)
        make_period_csv(period, csv_rows)


if __name__ == '__main__':
    main()
