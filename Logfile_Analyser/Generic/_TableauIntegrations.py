import csv
from datetime import datetime
from pathlib import Path
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

# =========================================================================
# CONFIGURATION
# =========================================================================

TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
TABLEAU_SITE_ID = ""
TABLEAU_PROJECT_ID = "0c88cccd-6f5c-4cd5-9641-f01c10fdbc3e"

VALUE_PARSERS = {
    "text": lambda value: value,
    "int": int,
    "float": float,
    "datetime": lambda value: datetime.strptime(value, "%Y-%m-%d %H:%M:%S"),
    "date": lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
}

SQL_TYPES = {
    "text": SqlType.text,
    "int": SqlType.big_int,
    "float": SqlType.double,
    "datetime": SqlType.timestamp,
    "date": SqlType.date,
}

# =========================================================================
# CSV VALIDATION
# =========================================================================

def validate_csv(csv_path, column_headers):
    expected_headers = [column_name for _, column_name, _ in column_headers]

    with csv_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file)

        # ---------------------------------------------------------
        # Headers
        # ---------------------------------------------------------

        headers = next(reader, [])

        if headers != expected_headers:
            raise ValueError(
                "CSV headers do not match.\n"
                f"Expected: {expected_headers}\n"
                f"Found:    {headers}"
            )

        # ---------------------------------------------------------
        # Validate field types
        # ---------------------------------------------------------

        for _, column_name, field_type in column_headers:
            if field_type not in VALUE_PARSERS:
                raise ValueError(f"Unknown field type '{field_type}' for column '{column_name}'")

        # ---------------------------------------------------------
        # Rows
        # ---------------------------------------------------------

        row_count = 0
        for row_number, row in enumerate(reader, start=2):

            # Ignore completely blank rows
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

                # Empty values become NULL in Hyper
                if not value:
                    continue

                try:
                    VALUE_PARSERS[field_type](value)

                except (ValueError, TypeError, OverflowError) as exc:

                    raise ValueError(
                        f"Invalid value on row {row_number}, "
                        f"column '{column_name}': "
                        f"{value!r} is not a valid {field_type}"
                    ) from exc

            row_count += 1

    return row_count

# =========================================================================
# COMPLEX FUNCTIONS
# =========================================================================

def create_hyper_from_csv(csv_path, hyper_path, column_headers, logger):
    """
    Create a Hyper file from a validated CSV.

    Returns:
        Number of rows written.
    """

    logger.info("Creating Hyper file: %s", hyper_path)

    row_count = validate_csv(
        csv_path,
        column_headers,
    )

    logger.info(
        "CSV validation successful: %d rows",
        row_count,
    )

    schema_name = "Extract"
    table_name = "Extract"

    # ---------------------------------------------------------
    # Build Hyper table definition
    # ---------------------------------------------------------

    columns = []

    for _, column_name, field_type in column_headers:

        try:
            sql_type = SQL_TYPES[field_type]()

        except KeyError:
            raise ValueError(
                f"Unknown field type '{field_type}' "
                f"for column '{column_name}'"
            )

        columns.append(
            TableDefinition.Column(
                column_name,
                sql_type,
            )
        )

    table = TableDefinition(
        table_name=TableName(
            schema_name,
            table_name,
        ),
        columns=columns,
    )

    # ---------------------------------------------------------
    # Create Hyper
    # ---------------------------------------------------------

    hyper_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with HyperProcess(
        Telemetry.SEND_USAGE_DATA_TO_TABLEAU,
        parameters={
            "default_database_version": "2"
        },
    ) as hyper:

        with Connection(
            endpoint=hyper.endpoint,
            database=str(hyper_path),
            create_mode=CreateMode.CREATE_AND_REPLACE,
        ) as connection:

            connection.catalog.create_schema(
                schema_name
            )

            connection.catalog.create_table(
                table
            )

            with Inserter(
                connection,
                table,
            ) as inserter:

                with csv_path.open(
                    newline="",
                    encoding="utf-8-sig",
                ) as csv_file:

                    reader = csv.reader(csv_file)

                    # Skip header
                    next(reader, None)

                    for row in reader:

                        if (
                            not row
                            or all(
                                not value.strip()
                                for value in row
                            )
                        ):
                            continue

                        parsed_row = []

                        for value, (
                            _,
                            column_name,
                            field_type,
                        ) in zip(
                            row,
                            column_headers,
                        ):

                            value = value.strip()

                            if not value:
                                parsed_row.append(None)
                                continue

                            try:
                                parsed_value = VALUE_PARSERS[
                                    field_type
                                ](value)

                            except (
                                ValueError,
                                TypeError,
                                OverflowError,
                            ) as exc:

                                raise ValueError(
                                    f"Invalid value in column "
                                    f"'{column_name}': {value!r}"
                                ) from exc

                            parsed_row.append(parsed_value)

                        inserter.add_row(parsed_row)

                inserter.execute()

    logger.info(
        "Created %s with %d rows",
        hyper_path.name,
        row_count,
    )

    return row_count

def publish_hyper_to_tableau(
    hyper_path,
    datasource_name,
    logger,
    *,
    server_url: str,
    site_id: str,
    project_id: str,
    token_name: str,
    token_secret: str,
    overwrite: bool = True,
    verify_ssl: bool = False,
):
    """
    Publish one Hyper file to Tableau.

    Returns:
        Published datasource ID.
    """

    logger.info(
        "Publishing %s to Tableau as '%s'",
        hyper_path.name,
        datasource_name,
    )

    tableau_auth = TSC.PersonalAccessTokenAuth(
        token_name=token_name,
        personal_access_token=token_secret,
        site_id=site_id,
    )

    server = TSC.Server(
        server_url,
        use_server_version=True,
    )

    if not verify_ssl:
        server.add_http_options({
            "verify": False
        })

        logger.warning(
            "SSL verification disabled for Tableau connection"
        )

    publish_mode = (
        TSC.Server.PublishMode.Overwrite
        if overwrite
        else TSC.Server.PublishMode.CreateNew
    )

    with server.auth.sign_in(tableau_auth):

        logger.info("Signed in to Tableau")

        datasource = TSC.DatasourceItem(
            project_id=project_id,
            name=datasource_name,
        )

        published = server.datasources.publish(
            datasource,
            str(hyper_path),
            publish_mode,
        )

        logger.info(
            "Published '%s' successfully",
            datasource_name,
        )

        return published.id

# =========================================================================
# PUBLIC FUNCTION
# =========================================================================

def publish_csv_to_tableau(
    csv_path: Path,
    column_headers: list[tuple[str, str, str]],
    *,
    token_name: str,
    token_secret: str,
    logger,
    hyper_path: Path,
    datasource_name: str,
):
    """
    Create a Hyper from a CSV and publish it to Tableau.

    This is the only function that should normally need to be called.

    Returns:
        Tableau datasource ID.
    """

    csv_path = Path(csv_path)

    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV file not found: {csv_path}"
        )

    # ---------------------------------------------------------
    # Determine output names
    # ---------------------------------------------------------

    if hyper_path is None:
        hyper_path = csv_path.with_suffix(".hyper")

    if datasource_name is None:
        datasource_name = csv_path.stem

    logger.info(
        "Starting CSV → Hyper → Tableau pipeline"
    )

    # ---------------------------------------------------------
    # 1. CSV → Hyper
    # ---------------------------------------------------------

    create_hyper_from_csv(
        csv_path=csv_path,
        hyper_path=hyper_path,
        column_headers=column_headers,
        logger=logger,
    )

    # ---------------------------------------------------------
    # 2. Hyper → Tableau
    # ---------------------------------------------------------

    datasource_id = publish_hyper_to_tableau(
        hyper_path=hyper_path,
        datasource_name=datasource_name,
        logger=logger,
        server_url=TABLEAU_SERVER_ADDRESS,
        site_id=TABLEAU_SITE_ID,
        project_id=TABLEAU_PROJECT_ID,
        token_name=token_name,
        token_secret=token_secret,
    )

    logger.info(
        "CSV → Hyper → Tableau completed successfully"
    )

    return datasource_id