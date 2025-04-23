import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/doce")

class AzureOpenAIConfig(BaseModel):
    """Azure OpenAI configuration settings."""
    api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    deployment_name: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")

class GoogleVisionConfig(BaseModel):
    """Google Vision API configuration settings."""
    credentials_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")

class FileStorageConfig(BaseModel):
    """File storage configuration settings."""
    contract_path: str = os.getenv("CONTRACT_STORAGE_PATH", "/tmp/contracts")
    invoice_path: str = os.getenv("INVOICE_UPLOAD_PATH", "/tmp/uploads")

class JWTConfig(BaseModel):
    """JWT authentication configuration settings."""
    secret_key: str = os.getenv("JWT_SECRET", "your_jwt_secret_key")
    algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

class Settings(BaseModel):
    """Application settings."""
    app_name: str = "Division of Contract Efficiency (DOCE)"
    database: DatabaseConfig = DatabaseConfig()
    azure_openai: AzureOpenAIConfig = AzureOpenAIConfig()
    google_vision: GoogleVisionConfig = GoogleVisionConfig()
    file_storage: FileStorageConfig = FileStorageConfig()
    jwt: JWTConfig = JWTConfig()

# Create a global settings object
settings = Settings()