import sys
import os
import pathlib
import json
import base64
import csv
import dataclasses
from decimal import Decimal
from banes import banorte_email
from banes import records


def extra_amount_total(extra_amount):
    return Decimal(extra_amount.amount) + Decimal(extra_amount.tax)


def calculate_total_amount(record):
    has_extra_amounts = record.type == records.EXPENSE_RECORD_TYPE and record.extra_amounts is not None
    _extra_amount_total = sum([extra_amount_total(ea) for ea in record.extra_amounts])\
        if has_extra_amounts else Decimal(0)

    return Decimal(record.amount) + _extra_amount_total


input_folder = sys.argv[1]
p = pathlib.Path(input_folder)

try:
    os.mkdir('failures')
except FileExistsError:
    pass

records_csv = open('records.csv', 'w', newline='')
fieldnames = [
    'type',
    'source',
    'total_amount',
    'note',
    'operation_date',
    'application_date',
    'raw',
]
csv_writer = csv.DictWriter(records_csv, fieldnames=fieldnames)

csv_writer.writeheader()

for path in p.glob(f'*.json'):
    with path.open() as json_email:
        email_content = json.loads(json_email.read())
        email_id = email_content['id']
        email_from = email_content['from']
        email_date = email_content['internal_date']
        email_body = str(base64.urlsafe_b64decode(email_content['body'].encode('ascii')), 'utf-8')

        try:
            r = banorte_email.scrape(email_body)

            if r.type is not records.ACCOUNT_OPERATION_TYPE:
                csv_writer.writerow({
                    'type': r.type,
                    'source': r.source,
                    'total_amount': calculate_total_amount(r),
                    'note': r.note,
                    'inbox_date': email_date,
                    'operation_date': r.operation_date,
                    'application_date': r.application_date if r.type == records.EXPENSE_RECORD_TYPE else None,
                    'from': email_from,
                    'raw': json.dumps(dataclasses.asdict(r), default=str),
                })
        except Exception as e:
            print(f'{email_id} - {e}')

            with open(f'./failures/{email_id}.html', 'w') as email_file:
                email_file.write(email_body)

records_csv.close()
