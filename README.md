# gaston-data
Data scripts for the [Gaston](https://github.com/ramomar/gaston) project.

## Scripts

### List of scripts

| Name | Description | Example usage |
|------|-------------|-------|
| `banorte_records_csv` | Reads a folder of emails stored in JSON format and produces CSV files with the following naming schema `f'{date.year}-{date.month}-{len(rows)}'` in the `period_records/` folder. It also writes emails that fail processing in the `./failures/{email_id}.html` path.| `python banorte_records_csv.py ~/emails` |
