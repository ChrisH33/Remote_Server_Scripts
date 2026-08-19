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
    Inserter,
)


def create_hyper_from_csv(
    csv_path: Path,
    hyper_path: Path,
    column_headers: list[tuple[str, str, str]],
    logger,
    schema_name: str = "Extract",
    table_name: str = "Extract",
) -> None:

    logger.info("Starting Hyper file creation from %s",hyper_path.name)

    # ------------------------------------------------------------------
    # Type definitions
    # ------------------------------------------------------------------

    type_definitions = {
        "text": (SqlType.text(), lambda value: value),
        "float": (SqlType.double(), lambda value: float(value)),
        "datetime": (SqlType.timestamp(), lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S")),
        "date": (SqlType.date(), lambda value: datetime.strptime(value, "%Y-%m-%d").date()),
    }

    # ------------------------------------------------------------------
    # Build schema
    # ------------------------------------------------------------------

    columns = []
    for _, column_name, field_type in column_headers:
        if field_type not in type_definitions:
            raise ValueError(f"Unknown field type '{field_type} for column '{column_name}'")
        sql_type, _ = type_definitions[field_type]
        columns.append(TableDefinition.Column(column_name, sql_type))
    table = TableDefinition(
        table_name=TableName(schema_name, table_name),
        columns=columns,
    )

    # ------------------------------------------------------------------
    # Validate CSV headers
    # ------------------------------------------------------------------

    expected_headers = [column_name for _, column_name, _ in column_headers]

    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)
            headers = next(reader)

            if headers != expected_headers:
                raise ValueError(
                    "CSV headers do not match TIDY_FIELDS.\n"
                    f"Expected: {expected_headers}\n"
                    f"Found:    {headers}"
                )

    except Exception:
        logger.exception("CSV header validation failed for %s", csv_path)
        raise

    logger.info("CSV headers validated successfully")

    # ------------------------------------------------------------------
    # Validate CSV data
    # ------------------------------------------------------------------

    logger.info("Validating CSV against predefined field types")

    row_count = 0
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
            reader = csv.reader(csv_file)

            # Skip header
            next(reader)
            for row_number, row in enumerate(reader, start=2):

                # Ignore completely empty rows
                if not row or all(not value.strip() for value in row):
                    continue
                if len(row) != len(column_headers):
                    raise ValueError(
                        f"Malformed row {row_number}: "
                        f"expected {len(column_headers)} columns, "
                        f"got {len(row)}"
                    )

                for value, (_, column_name, field_type) in zip(row, column_headers):
                    value = value.strip()

                    # Empty CSV values become NULL
                    if value == "":
                        continue

                    _, parser = type_definitions[field_type]
                    try:
                        parser(value)

                    except (ValueError, TypeError, OverflowError) as exc:

                        raise ValueError(
                            f"Invalid value on row {row_number}, "
                            f"column '{column_name}': "
                            f"{value!r} is not a valid {field_type}"
                        ) from exc

                row_count += 1

    except Exception:
        logger.exception("CSV validation failed for %s", csv_path)
        raise

    logger.info("CSV validation successful: %d rows validated", row_count)

    # ------------------------------------------------------------------
    # Create Hyper
    # ------------------------------------------------------------------

    try:
        with HyperProcess(
            Telemetry.SEND_USAGE_DATA_TO_TABLEAU,
            parameters={"default_database_version": "2"},
        ) as hyper:

            with Connection(
                endpoint=hyper.endpoint,
                database=str(hyper_path),
                create_mode=CreateMode.CREATE_AND_REPLACE,
            ) as connection:
                connection.catalog.create_schema(schema_name)
                connection.catalog.create_table(table)

                with Inserter(connection, table) as inserter:
                    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
                        reader = csv.reader(csv_file)

                        # Skip header
                        next(reader)

                        for row_number, row in enumerate(reader, start=2):
                            if not row or all(not value.strip() for value in row):
                                continue

                            parsed_row = []
                            for value, (
                                _,
                                column_name,
                                field_type,
                            ) in zip(row, column_headers):

                                value = value.strip()

                                if value == "":
                                    parsed_row.append(None)
                                    continue

                                _, parser = type_definitions[field_type]

                                try:
                                    parsed_row.append(parser(value))

                                except (
                                    ValueError,
                                    TypeError,
                                    OverflowError,
                                ) as exc:

                                    raise ValueError(
                                        f"Invalid value on row "
                                        f"{row_number}, column "
                                        f"'{column_name}': "
                                        f"{value!r}"
                                    ) from exc

                            inserter.add_row(parsed_row)

                    inserter.execute()

    except Exception:
        logger.exception("Failed to create Hyper file %s", hyper_path)
        raise

    logger.info(f"Finished. {hyper_path.name} created with {row_count} rows")