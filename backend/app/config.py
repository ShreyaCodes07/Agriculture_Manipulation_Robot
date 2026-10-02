"""
Agriculture Manipulation Robot - Application Configuration Settings
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Agriculture Manipulation Robot OS API"
    VERSION: str = "1.0.0"
    
    # Operation Mode: "simulation" or "hardware"
    MODE: str = "simulation"

    # Host & Port Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Allowed Origins
    CORS_ORIGINS: list = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "*"
    ]

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./agri_robot.db"

    # Robot Safety Thresholds
    OBSTACLE_BRAKE_THRESHOLD_CM: float = 30.0
    SOIL_MOISTURE_LOW_THRESHOLD: float = 20.0

settings = Settings()
