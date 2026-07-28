import tableauserverclient as TSC
from pathlib import Path

def publish_hyper_to_tableau(
    hyper_file_path: str | Path,
    project_id: str,
    datasource_name: str,
    *,
    server_url: str,
    site_id: str,
    token_name: str,
    token_secret: str,
    overwrite: bool = True,
    verify_ssl: bool = False,        
):
    tableau_auth = TSC.PersonalAccessTokenAuth(
        token_name=token_name,
        personal_access_token=token_secret,
        site_id=site_id,
    )
    
    server = TSC.Server(server_url, use_server_version=True)
    if not verify_ssl:
        server.add_http_options({"verify": False})

    publish_mode = TSC.Server.PublishMode.Overwrite if overwrite else TSC.Server.PublishMode.CreateNew

    with server.auth.sign_in(tableau_auth):
        datasource = TSC.DatasourceItem(
            project_id=project_id,
            name=datasource_name
        )

        published_ds = server.datasources.publish(
            datasource,
            hyper_file_path,
            publish_mode
        )

        print("Published:", published_ds.id)
        return published_ds.id