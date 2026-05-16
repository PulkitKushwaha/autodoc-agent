from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AUTODOC_",
        case_sensitive=False,
    )

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    use_mock: bool = Field(default=True)
    output_dir: Path = Field(default=Path("./output"))
    temp_dir: Path = Field(default=Path("./temp_repos"))
    log_level: str = Field(default="INFO")
    log_file: Path | None = Field(default=Path("./output/autodoc.log"))

    def ensure_dirs(self) -> None:
        """Create output and temp directories if they do not exist."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
