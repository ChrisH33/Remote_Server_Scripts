import csv
from datetime import datetime
from pathlib import Path

try:
    import tableauserverclient as TSC
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
    TABLEAU_LIBS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when libs are absent
    TABLEAU_LIBS_AVAILABLE = False

TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
TABLEAU_SITE_ID = ""
TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"


def _type_definitions():
    """Column-type -> (SqlType, string-parser) lookup.

    Built lazily rather than at import time so this module can still be
    imported (and its pure CSV-validation helpers used/tested) even where
    tableauhyperapi isn't installed.
    """
    return {
        "text": (SqlType.text(), lambda value: value),
        "int": (SqlType.big_int(), lambda value: int(value)),
        "float": (SqlType.double(), lambda value: float(value)),
        "datetime": (SqlType.timestamp(), lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S")),
        "date": (SqlType.date(), lambda value: datetime.strptime(value, "%Y-%m-%d").date()),
    }


# The parsers themselves don't need tableauhyperapi at all - only the
# SqlType half of each pair does - so they're kept separately importable
# for validation logic/tests that don't touch Tableau.
_VALUE_PARSERS = {
    "text": lambda value: value,
    "int": lambda value: int(value),
    "float": lambda value: float(value),
    "datetime": lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S"),
    "date": lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
}


# =========================================================================
# CSV VALIDATION (pure - no Tableau dependency, fully unit-testable)
# =========================================================================

def validate_csv_headers(csv_path: Path, column_headers: list[tuple[str, str, str]]) -> None:
    """Raise ValueError if the CSV's header row doesn't match column_headers."""
    expected_headers = [column_name for _, column_name, _ in column_headers]
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        headers = next(reader, [])
        if headers != expected_headers:
            raise ValueError(
                "CSV headers do not match.\n"
                f"Expected: {expected_headers}\n"
                f"Found:    {headers}"
            )


def validate_csv_rows(csv_path: Path, column_headers: list[tuple[str, str, str]]) -> int:
    """Validate every data row against column_headers' declared types.

    Returns the number of (non-blank) rows validated. Raises ValueError on
    the first malformed row or value, or on an unknown field type.
    """
    for _, column_name, field_type in column_headers:
        if field_type not in _VALUE_PARSERS:
            raise ValueError(f"Unknown field type '{field_type}' for column '{column_name}'")

    row_count = 0
    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)
        next(reader, None)  # skip header

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

                parser = _VALUE_PARSERS[field_type]
                try:
                    parser(value)
                except (ValueError, TypeError, OverflowError) as exc:
                    raise ValueError(
                        f"Invalid value on row {row_number}, "
                        f"column '{column_name}': "
                        f"{value!r} is not a valid {field_type}"
                    ) from exc

            row_count += 1

    return row_count


# =========================================================================
# HYPER FILE CREATION
# =========================================================================

def create_hyper_from_csv(
    csv_path: Path,
    hyper_path: Path,
    column_headers: list[tuple[str, str, str]],
    logger,
) -> None:

    # BUG FIX: these used to be written as
    #     schema_name: str = "Extract",
    #     table_name: str = "Extract",
    # The trailing commas silently turned both into 1-element tuples
    # instead of strings, which would have broken TableName(schema_name,
    # table_name) as soon as this function was actually exercised.
    schema_name = "Extract"
    table_name = "Extract"

    if not TABLEAU_LIBS_AVAILABLE:
        raise ImportError(
            "tableauserverclient / tableauhyperapi are not installed - "
            "cannot create a Hyper file. CSV validation can still be run "
            "via validate_csv_headers()/validate_csv_rows()."
        )

    logger.info("Starting Hyper file creation from %s", hyper_path.name)

    # ---------------------------------------------------------
    # 1. Check Files Exist
    # ---------------------------------------------------------

    if not csv_path.exists():
        logger.error(f"Raw input file not found: {csv_path}")
        return

    # ------------------------------------------------------------------
    # Build schema
    # ------------------------------------------------------------------

    type_definitions = _type_definitions()
    columns = []
    for _, column_name, field_type in column_headers:
        if field_type not in type_definitions:
            raise ValueError(f"Unknown field type '{field_type}' for column '{column_name}'")
        sql_type, _ = type_definitions[field_type]
        columns.append(TableDefinition.Column(column_name, sql_type))
    table = TableDefinition(table_name=TableName(schema_name, table_name), columns=columns)

    # ------------------------------------------------------------------
    # Validate CSV headers + data
    # ------------------------------------------------------------------

    try:
        validate_csv_headers(csv_path, column_headers)
    except Exception:
        logger.exception("CSV header validation failed for %s", csv_path)
        raise

    logger.info("Validating CSV against predefined field types")
    try:
        row_count = validate_csv_rows(csv_path, column_headers)
    except Exception:
        logger.exception("CSV validation failed for %s", csv_path)
        raise

    logger.info("CSV validation successful: %d rows validated", row_count)

    # ------------------------------------------------------------------
    # Create Hyper
    # ------------------------------------------------------------------

    try:
        hyper_path.parent.mkdir(parents=True, exist_ok=True)
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
                        next(reader, None)  # skip header

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
                                except (ValueError, TypeError, OverflowError) as exc:
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


def publish_hypers_to_tableau(
    datasets: list[tuple[Path, str]],
    project_id: str,
    logger,
    *,
    server_url: str,
    site_id: str,
    token_name: str,
    token_secret: str,
    overwrite: bool = True,
    verify_ssl: bool = False,
):
    if not TABLEAU_LIBS_AVAILABLE:
        raise ImportError("tableauserverclient is not installed - cannot publish to Tableau.")

    try:
        # --- Authentication -------------------------------------------
        tableau_auth = TSC.PersonalAccessTokenAuth(token_name=token_name, personal_access_token=token_secret, site_id=site_id)
        server = TSC.Server(server_url, use_server_version=True)

        if not verify_ssl:      # Optionally disable SSL verification
            server.add_http_options({"verify": False})
            logger.debug("Disabled SSL verification for Tableau server requests")

        publish_mode = (        # Overwrite existing datasources or always create new ones
            TSC.Server.PublishMode.Overwrite
            if overwrite
            else TSC.Server.PublishMode.CreateNew
        )

        # --- Sign in and publish each Hyper file -----------------------
        with server.auth.sign_in(tableau_auth):
            logger.info("Signed in to Tableau server")
            for hyper_file, datasource_name in datasets:
                hyper_file = Path(hyper_file)   # Ensure it's always a Path object
                logger.info(
                    "Preparing to publish %s as datasource '%s'",
                    hyper_file.name,
                    datasource_name,
                )

                # Describe the target datasource: which project it belongs to and what it should be named.
                datasource = TSC.DatasourceItem(project_id=project_id, name=datasource_name)

                published_ds = server.datasources.publish(datasource, str(hyper_file), publish_mode)
                logger.info("Published '%s' successfully: %s", datasource_name, published_ds.id)

    except Exception:
        # Log the full traceback for diagnosis, then re-raise so the
        # caller can decide how to handle the failure (e.g. retry, alert).
        logger.exception("Failed to publish Hyper files to Tableau")
        raise