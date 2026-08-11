import tableauserverclient as TSC
from pathlib import Path

def publish_hyper_to_tableau(
    hyper_file_path: str | Path,
    project_id: str,
    datasource_name: str,
    logger,
    *,
    server_url: str,
    site_id: str,
    token_name: str,
    token_secret: str,
    overwrite: bool = True,
    verify_ssl: bool = False,        
):

    logger.debug("Publishing to project %s as datasource '%s'", project_id, datasource_name)
    logger.debug("Server URL: %s | Site: %s | SSL verification: %s | overwrite: %s", server_url, site_id, verify_ssl, overwrite)

    try:
        tableau_auth = TSC.PersonalAccessTokenAuth(
            token_name=token_name,
            personal_access_token=token_secret,
            site_id=site_id,
        )
        logger.debug("Created Tableau auth context for site %s", site_id)

        server = TSC.Server(server_url, use_server_version=True)
        if not verify_ssl:
            server.add_http_options({"verify": False})
            logger.debug("Disabled SSL verification for Tableau server requests")

        publish_mode = TSC.Server.PublishMode.Overwrite if overwrite else TSC.Server.PublishMode.CreateNew
        logger.debug("Using publish mode: %s", "overwrite" if overwrite else "create_new")

        with server.auth.sign_in(tableau_auth):
            logger.info("Signed in to Tableau server")
            datasource = TSC.DatasourceItem(
                project_id=project_id,
                name=datasource_name,
            )

            published_ds = server.datasources.publish(
                datasource,
                hyper_file_path,
                publish_mode,
            )

            logger.info("Datasource published successfully: %s", published_ds.id)
            return published_ds.id
    except Exception:
        logger.exception("Failed to publish Hyper file %s to Tableau", hyper_file_path)
        raise