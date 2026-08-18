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
    """
    Publish a batch of Hyper files to Tableau Server as datasources.

    Parameters
    ----------
    datasets : list[tuple[Path, str]]
        List of (hyper_file_path, datasource_name) pairs. Each hyper file is
        published under the given datasource name.
    project_id : str
        ID of the Tableau project the datasources should be published into.
    logger : logging.Logger
        Logger used for progress and error reporting.
    server_url : str
        Base URL of the Tableau Server / Tableau Cloud instance.
    site_id : str
        Tableau site (content URL) to sign in to.
    token_name : str
        Name of the Tableau Personal Access Token (PAT) to authenticate with.
    token_secret : str
        Secret value of the Tableau Personal Access Token.
    overwrite : bool, default True
        If True, overwrite an existing datasource with the same name.
        If False, always publish as a new datasource.
    verify_ssl : bool, default False
        If False, disable SSL certificate verification for requests to the
        Tableau server (useful for self-signed certs on internal servers).

    Returns
    -------
    list[str]
        The Tableau-assigned IDs of the published datasources, in the same
        order as `datasets`.

    Raises
    ------
    Exception
        Re-raises any exception encountered during authentication or
        publishing, after logging it.
    """

    # --- Setup: log what we're about to do -----------------------------
    logger.debug(
        "Preparing to publish %d Hyper files to project %s",
        len(datasets),
        project_id,
    )

    try:
        # --- Authentication -------------------------------------------
        # Use a Tableau Personal Access Token (PAT) rather than username/
        # password, so credentials can be rotated without touching this code.
        tableau_auth = TSC.PersonalAccessTokenAuth(
            token_name=token_name,
            personal_access_token=token_secret,
            site_id=site_id,
        )

        server = TSC.Server(server_url, use_server_version=True)

        # Optionally disable SSL verification (e.g. internal servers using
        # self-signed certificates).
        if not verify_ssl:
            server.add_http_options({"verify": False})
            logger.debug("Disabled SSL verification for Tableau server requests")

        # Decide whether to overwrite existing datasources or always create
        # new ones.
        publish_mode = (
            TSC.Server.PublishMode.Overwrite
            if overwrite
            else TSC.Server.PublishMode.CreateNew
        )

        # --- Sign in and publish each Hyper file -----------------------
        # The `with` block signs out automatically once publishing is done,
        # even if an error occurs partway through.
        with server.auth.sign_in(tableau_auth):
            logger.info("Signed in to Tableau server")

            for hyper_file, datasource_name in datasets:
                # Ensure we always have a Path object, even if a plain
                # string was passed in for this entry.
                hyper_file = Path(hyper_file)

                logger.info(
                    "Publishing %s as datasource '%s'",
                    hyper_file.name,
                    datasource_name,
                )

                # Describe the target datasource: which project it belongs
                # to and what it should be named.
                datasource = TSC.DatasourceItem(
                    project_id=project_id,
                    name=datasource_name,
                )

                # Upload and publish the .hyper file itself.
                published_ds = server.datasources.publish(
                    datasource,
                    str(hyper_file),
                    publish_mode,
                )

                logger.info(
                    "Published '%s' successfully: %s",
                    datasource_name,
                    published_ds.id,
                )

    except Exception:
        # Log the full traceback for diagnosis, then re-raise so the
        # caller can decide how to handle the failure (e.g. retry, alert).
        logger.exception("Failed to publish Hyper files to Tableau")
        raise