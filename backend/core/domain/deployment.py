from enum import StrEnum


class DeploymentName(StrEnum):
    PRODUCTION = "production"
    DEV = "dev"
    STAGING = "staging"
