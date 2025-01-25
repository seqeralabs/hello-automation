from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, HttpUrl, DirectoryPath, AnyHttpUrl, Field

class Settings(BaseSettings):
    """Configuration settings for SLAS 2025 application"""

    # Temporal settings
    temporal_server_url: str = "localhost:7233"
    temporal_namespace: str = "default"
    
    # File processing settings
    sequencer_monitor_path: DirectoryPath = DirectoryPath("./sequencer")
    metadata_download_url: AnyHttpUrl = AnyHttpUrl("https://raw.githubusercontent.com/nf-core/sarek/refs/tags/3.5.0/tests/csv/3.0")
    destination_bucket: str = "slas-2025"
    destination_prefix: str = "event-driven-bioinformatics"
    data_suffix: list[str] = ["_1.fastq.gz", "_2.fastq.gz"]
    
    # Seqera platform settings
    seqera_api_endpoint: HttpUrl = Field(
        default=HttpUrl("https://api.cloud.seqera.io"),
        alias="TOWER_API_ENDPOINT"
    )
    seqera_token: SecretStr = Field(
        alias="TOWER_ACCESS_TOKEN"
    )
    seqera_workspace_id: str = Field(
        alias="TOWER_WORKSPACE_ID"
    )
    seqera_action_id: str
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

# Create a global instance of settings
settings = Settings()
