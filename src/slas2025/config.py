from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, HttpUrl, DirectoryPath, AnyHttpUrl, Field

class Settings(BaseSettings):
    """Configuration settings for SLAS 2025 application"""

    # Temporal settings
    temporal_server_url: HttpUrl = HttpUrl("http://localhost:7233")
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

    # Studio settings
    data_studio_tool_url: HttpUrl = Field(
        default=HttpUrl("https://studio.cloud.seqera.io"),
        description="URL for the data studio tool"
    )
    compute_env_id: str = Field(
        description="ID of the compute environment to use for the studio"
    )
    studio_cpu: int = Field(
        default=2,
        description="Number of CPUs to allocate for the studio"
    )
    studio_memory: int = Field(
        default=8,
        description="Amount of memory in GB to allocate for the studio"
    )
    studio_conda_env: str = Field(
        default="base",
        description="Conda environment to use for the studio"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

# Create a global instance of settings
settings = Settings()
