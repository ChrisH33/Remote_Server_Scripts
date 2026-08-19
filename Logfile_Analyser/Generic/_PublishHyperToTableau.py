import tableauserverclient as TSC
from pathlib import Path


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
                    "Publishing %s as datasource '%s'",
                    hyper_file.name,
                    datasource_name,
                )

                # Describe the target datasource: which project it belongs to and what it should be named.
                datasource = TSC.DatasourceItem(project_id=project_id, name=datasource_name)

                if False:   # Upload & publish the .hyper file itself
                    published_ds = server.datasources.publish(datasource, str(hyper_file), publish_mode)
                    logger.info("Published '%s' successfully: %s", datasource_name, published_ds.id)

    except Exception:
        # Log the full traceback for diagnosis, then re-raise so the
        # caller can decide how to handle the failure (e.g. retry, alert).
        logger.exception("Failed to publish Hyper files to Tableau")
        raise