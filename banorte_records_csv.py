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
from banes import banorte_email
from banes import records


def extra_amount_total(extra_amount):
    return Decimal(extra_amount.amount) + Decimal(extra_amount.tax)


def calculate_total_amount(record):
    has_extra_amounts = record.type == records.EXPENSE_RECORD_TYPE and record.extra_amounts is not None
    _extra_amount_total = sum([extra_amount_total(ea) for ea in record.extra_amounts])\
        if has_extra_amounts else Decimal(0)

    return Decimal(record.amount) + _extra_amount_total


def read_record_from_email(json_email):
    email_content = json.loads(json_email.read())
    email_id = email_content['id']
    email_from = email_content['from']
    inbox_timestamp = email_content['internal_date']
    inbox_date = datetime.fromtimestamp(inbox_timestamp / 1000.0, tz=timezone('America/Mexico_City')).isoformat()
    email_body = str(base64.urlsafe_b64decode(email_content['body'].encode('ascii')), 'utf-8')
    record = banorte_email.scrape(email_body)
    result = {
        'email_id': email_id,
        'type': record.type,
        'source': record.source,
        'total_amount': calculate_total_amount(record),
        'note': record.note,
        'inbox_timestamp': inbox_timestamp,
        'inbox_date': inbox_date,
        'operation_date': record.operation_date,
        'application_date': record.application_date if record.type == records.EXPENSE_RECORD_TYPE else None,
        'from': email_from,
        'raw': json.dumps(dataclasses.asdict(record), default=str),
    }

    return result, email_body


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


def main():
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
        'email_id',
        'email_from',
        'email_timestamp',
        'email_date',
    ]
    csv_writer = csv.DictWriter(records_csv, fieldnames=fieldnames)

    csv_writer.writeheader()

    for path in p.glob(f'*.json'):
        with path.open() as json_email:

            try:
                email_content = json.loads(json_email.read())
                email_body = str(base64.urlsafe_b64decode(email_content['body'].encode('ascii')), 'utf-8')
                record = banorte_email.scrape(email_body)
                email_id = email_content['id']
                email_timestamp = email_content['internal_date']
                email_metadata = {
                    'email_id': email_id,
                    'email_from': email_content['from'],
                    'email_timestamp': email_timestamp,
                    'email_date': datetime.fromtimestamp(email_timestamp / 1000.0,
                                                         tz=timezone('America/Mexico_City')).isoformat(),
                }
                if record.type is not records.ACCOUNT_OPERATION_TYPE:
                    row = make_csv_row(record, email_metadata)

                    csv_writer.writerow(row)
            except Exception as e:
                print(f'{email_id} - {e}')

                with open(f'./failures/{email_id}.html', 'w') as email_file:
                    email_file.write(email_body)

    records_csv.close()


if __name__ == '__main__':
    main()
