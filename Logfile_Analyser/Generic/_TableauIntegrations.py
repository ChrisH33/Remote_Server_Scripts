import csv
from datetime import datetime
import tableauserverclient as TSC
from pathlib import Path
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

TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
TABLEAU_SITE_ID = ""
TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"


type_definitions = {
    "text": (SqlType.text(), lambda value: value),
    "int": (SqlType.big_int(), lambda value: int(value)),
    "float": (SqlType.double(), lambda value: float(value)),
    "datetime": (SqlType.timestamp(), lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S")),
    "date": (SqlType.date(), lambda value: datetime.strptime(value, "%Y-%m-%d").date()),
}

def create_hyper_from_csv(csv_path: Path, hyper_path: Path, column_headers: list[tuple[str, str, str]], logger) -> None:
    
    schema_name: str = "Extract",
    table_name: str = "Extract",
    logger.info("Starting Hyper file creation from %s",hyper_path.name)

    # ---------------------------------------------------------
    # 1. Check Files Exist
    # ---------------------------------------------------------

    # Check input exists
    if not csv_path.exists():
        logger.error(f"Raw input file not found: {csv_path}")
        return
    
    # ------------------------------------------------------------------
    # Build schema
    # ------------------------------------------------------------------

    columns = []
    for _, column_name, field_type in column_headers:
        if field_type not in type_definitions:
            raise ValueError(f"Unknown field type '{field_type} for column '{column_name}'")
        sql_type, _ = type_definitions[field_type]
        columns.append(TableDefinition.Column(column_name, sql_type))
    table = TableDefinition(table_name=TableName(schema_name, table_name), columns=columns)

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
                    "CSV headers do not match.\n"
                    f"Expected: {expected_headers}\n"
                    f"Found:    {headers}"
                )

    except Exception:
        logger.exception("CSV header validation failed for %s", csv_path)
        raise

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
    try:
        # --- Authentication -------------------------------------------
        tableau_auth = TSC.PersonalAccessTokenAuth(token_name=token_name,personal_access_token=token_secret,site_id=site_id)
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

                if True:   # Upload & publish the .hyper file itself
                    published_ds = server.datasources.publish(datasource, str(hyper_file), publish_mode)
                    logger.info("Published '%s' successfully: %s", datasource_name, published_ds.id)

    except Exception:
        # Log the full traceback for diagnosis, then re-raise so the
        # caller can decide how to handle the failure (e.g. retry, alert).
        logger.exception("Failed to publish Hyper files to Tableau")
        raise