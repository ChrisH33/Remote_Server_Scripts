import csv
from datetime import datetime
from pathlib import Path
from tableauhyperapi import (
    HyperProcess,
    Connection,
    Telemetry,
    CreateMode,
    TableDefinition,
    TableName,
    SqlType,
    Inserter
)

def create_hyper_from_csv(
    csv_path: str | Path,
    hyper_path: str | Path,
    logger,
    schema_name: str = "Extract",
    table_name: str = "Extract",
    sample_size: int = 100,
) -> None:

    logger.info("Starting Hyper file creation from %s", Path(hyper_path).name)

    datetime_formats = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    )

    def detect_type_and_parser(values):
        values = [v.strip() for v in values if v.strip()]
        if not values:
            return SqlType.text(), lambda v: v

        try:
            for v in values:
                int(v)
            return SqlType.big_int(), lambda v: int(v)
        except ValueError:
            pass

        try:
            for v in values:
                float(v)
            return SqlType.double(), lambda v: float(v)
        except ValueError:
            pass

        for fmt in datetime_formats:
            try:
                for v in values:
                    datetime.strptime(v, fmt)
                return SqlType.timestamp(), (lambda fmt: lambda v: datetime.strptime(v, fmt))(fmt)
            except ValueError:
                continue

        return SqlType.text(), lambda v: v

    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
            rows = list(reader)
    except Exception:
        logger.exception("Failed to read CSV file %s", csv_path)
        raise

    logger.info("Read %d headers and %d data rows from %s", len(headers), len(rows), Path(csv_path).name)

    samples = [[] for _ in headers]
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            samples[j].append(value)
        if i >= sample_size:
            break

    logger.debug("Collected sample rows for type inference across %d columns", len(headers))

    col_info = [detect_type_and_parser(values) for values in samples]
    columns = [
        TableDefinition.Column(col, sqltype)
        for col, (sqltype, _) in zip(headers, col_info)
    ]
    table = TableDefinition(table_name=TableName(schema_name, table_name), columns=columns)

    logger.debug("Inferred column types for %s: %s", table_name, ", ".join(f"{col}={sqltype}" for col, (sqltype, _) in zip(headers, col_info)))

    try:
        with HyperProcess(Telemetry.SEND_USAGE_DATA_TO_TABLEAU, parameters={"default_database_version": "2"}) as hyper:
            with Connection(endpoint=hyper.endpoint, database=hyper_path, create_mode=CreateMode.CREATE_AND_REPLACE) as connection:
                connection.catalog.create_schema(schema_name)
                connection.catalog.create_table(table)

                with Inserter(connection, table) as inserter:
                    for row in rows:
                        parsed_row = []
                        for value, (_, parser) in zip(row, col_info):
                            value = value.strip()
                            parsed_row.append(None if value == "" else parser(value))
                        inserter.add_row(parsed_row)
                    inserter.execute()
    except Exception:
        logger.exception("Failed to create Hyper file %s", hyper_path)
        raise

    logger.info("Hyper file created successfully")