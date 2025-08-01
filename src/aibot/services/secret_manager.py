import os

from google.cloud import secretmanager

from src.aibot.cli import logger


class SecretManagerService:
    def __init__(self, project_id: str | None = None) -> None:
        self.client = secretmanager.SecretManagerServiceClient()
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT_ID")

    def get_secret(self, secret_id: str, version: str = "latest") -> str | None:
        if not self.project_id:
            logger.error("Google Cloud project ID not configured")
            return None

        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/{version}"

        try:
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info("Successfully retrieved secret: %s", secret_id)
            return secret_value

        except Exception as e:
            logger.error("Failed to retrieve secret %s: %s", secret_id, e)
            return None

    def get_api_key(self, provider: str) -> str | None:
        """Get API key for specific AI provider from Secret Manager."""
        secret_mapping = {
            "anthropic": os.getenv("ANTHROPIC_SECRET_NAME", ""),
            "google": os.getenv("GEMINI_SECRET_NAME", ""),
            "openai": os.getenv("OPENAI_SECRET_NAME", ""),
        }

        secret_id = secret_mapping.get(provider)
        if not secret_id:
            logger.error("Unknown provider: %s", provider)
            return None

        return self.get_secret(secret_id)
