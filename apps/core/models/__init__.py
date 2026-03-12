"""
Core models package — re-exports all models for backward compatibility.

All existing imports like ``from .models import Project, Site`` continue to work.
"""
# Project
from .project import Project, ProjectScore  # noqa: F401

# Site & related
from .site import Site, GA4EventDefinition, KPIGoal, WeeklySnapshot  # noqa: F401

# Alerts
from .alerts import AlertRule, AlertEvent  # noqa: F401

# Audit
from .audit import AuditReport, AuditRecommendation, AuditConfig, RecommendationNote  # noqa: F401

# Brand Intel
from .brand import BrandProfile, DataSnapshot  # noqa: F401

# AI
from .ai import AIProvider, ProjectLearningContext, ExpertArticle  # noqa: F401

# Errors
from .errors import SystemErrorLog  # noqa: F401

__all__ = [
    "Project", "ProjectScore",
    "Site", "GA4EventDefinition", "KPIGoal", "WeeklySnapshot",
    "AlertRule", "AlertEvent",
    "AuditReport", "AuditRecommendation", "AuditConfig", "RecommendationNote",
    "BrandProfile", "DataSnapshot",
    "AIProvider", "ProjectLearningContext", "ExpertArticle",
    "SystemErrorLog",
]
