import csv
from datetime import datetime
from pathlib import Path
import tableauserverclient as TSC
from creds import Tableau_Credentials as credentials
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
# COMPLEX FUNCTIONS
# =========================================================================

def create_hyper_from_csv(csv_path, hyper_path, column_headers, logger):

    # ---------------------------------------------------------
    # Build Hyper table definition
    # ---------------------------------------------------------

    logger.info("Creating Hyper file: %s", hyper_path)

    columns = []
    schema_name = "Extract"
    table_name = "Extract"
    for _, column_name, field_type in column_headers:
        try:
            sql_type = SQL_TYPES[field_type]()
        except KeyError:
            raise ValueError(f"Unknown field type '{field_type}' for column '{column_name}'")
        columns.append(TableDefinition.Column(column_name, sql_type))
    table = TableDefinition(table_name=TableName(schema_name, table_name), columns=columns)

    # ---------------------------------------------------------
    # Create Hyper
    # ---------------------------------------------------------

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
                with csv_path.open(
                    newline="",
                    encoding="utf-8-sig",
                ) as csv_file:
                    reader = csv.reader(csv_file)

                    # Skip header
                    next(reader, None)

                    for row in reader:
                        if (not row or all(not value.strip() for value in row)):
                            continue
                        parsed_row = []
                        for value, (_, column_name, field_type) in zip(row,column_headers):
                            value = value.strip()
                            if not value:
                                parsed_row.append(None)
                                continue
                            try:
                                parsed_value = VALUE_PARSERS[field_type](value)
                            except (ValueError, TypeError, OverflowError) as exc:
                                raise ValueError(f"Invalid value in column '{column_name}': {value!r}") from exc

                            parsed_row.append(parsed_value)
                        inserter.add_row(parsed_row)
                inserter.execute()

def publish_hyper_to_tableau(
    hyper_path,
    datasource_name,
    logger,
    server_address,
    site_id,
    project_id,
    token_name,
    token_secret,
    *,
    verify_ssl=False,
    overwrite=True,
):

    logger.info("Publishing %s to Tableau as '%s'", hyper_path.name, datasource_name)

    # --------------------- Authentication ---------------------
    tableau_auth = TSC.PersonalAccessTokenAuth(token_name=token_name, personal_access_token=token_secret, site_id=site_id)
    server = TSC.Server(server_address, use_server_version=True)
    if not verify_ssl:
        server.add_http_options({"verify": False})
        logger.warning("SSL verification disabled for Tableau connection")
    publish_mode = (TSC.Server.PublishMode.Overwrite if overwrite else TSC.Server.PublishMode.CreateNew)

    # --------------------- Sign in & Publish ---------------------
    with server.auth.sign_in(tableau_auth):
        logger.info("Signed in to Tableau")

        datasource = TSC.DatasourceItem(project_id=project_id, name=datasource_name)
        published = server.datasources.publish(datasource, str(hyper_path), publish_mode)
        logger.info("Published '%s' successfully", datasource_name)

# =========================================================================
# PUBLIC FUNCTION
# =========================================================================

def publish_csv_to_tableau(csv_path: Path, datasource_name: str, column_headers: list[tuple[str, str, str]], project_id: str, logger) -> None:

    hyper_path = csv_path.with_suffix(".hyper")
    token_name = credentials.TOKEN_NAME
    token_secret = credentials.TOKEN_SECRET
    TABLEAU_SERVER_ADDRESS = "https://globalreporting.internal.sanger.ac.uk"
    TABLEAU_SITE_ID = ""

    logger.info("Starting CSV → Hyper → Tableau pipeline")

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

    publish_hyper_to_tableau(
        hyper_path=hyper_path,
        datasource_name=datasource_name,
        logger=logger,
        server_address=TABLEAU_SERVER_ADDRESS,
        site_id=TABLEAU_SITE_ID,
        project_id=project_id,
        token_name=token_name,
        token_secret=token_secret,
    )

    hyper_path.unlink(missing_ok=True)

    logger.info("CSV → Hyper → Tableau completed successfully")