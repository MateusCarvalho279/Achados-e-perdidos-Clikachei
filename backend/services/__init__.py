"""
Camada Service — um serviço por caso de uso.

Orquestra Models e Repositories, aplica regras de negócio (limites de
tentativa, geração de código, motor de validação) e é o único lugar que
decide quando fazer `commit()`. Controllers não tocam em Model/Repository
diretamente — sempre passam por um Service.
"""

from .admin_stats_service import AdminStatsService
from .auth_service import AuthService
from .category_report_service import CategoryReportService
from .claim_review_service import ClaimReviewService
from .claim_submission_service import ClaimSubmissionService
from .item_admin_service import ItemAdminService
from .item_search_service import ItemSearchService
from .location_report_service import LocationReportService
from .user_history_service import UserHistoryService

__all__ = [
    "AdminStatsService", "AuthService", "CategoryReportService", "ClaimReviewService",
    "ClaimSubmissionService", "ItemAdminService", "ItemSearchService",
    "LocationReportService", "UserHistoryService",
]
