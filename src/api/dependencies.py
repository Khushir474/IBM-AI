"""FastAPI dependency injection for services."""

from fastapi import Depends

from src.features.churn_features import ChurnFeatureEngineer
from src.features.ltv_features import LTVFeatureEngineer
from src.features.cart_features import CartAbandonmentFeatureEngineer
from src.features.pricing_features import PricingFeatureEngineer
from src.models.inference import ModelInference
from src.models.explainer import Explainer
from src.services.churn_service import ChurnService
from src.services.ltv_service import LTVService
from src.services.cart_service import CartService
from src.services.pricing_service import PricingService
from src.services.campaign_service import CampaignService
from src.services.experiment_service import ExperimentService
from src.services.dashboard_service import DashboardService
from src.services.export_service import ExportService


def get_churn_service() -> ChurnService:
    """Factory for ChurnService."""
    feature_eng = ChurnFeatureEngineer(
        customer_dao=None,
        order_dao=None,
        session_dao=None,
        review_dao=None,
    )
    model_inf = ModelInference(model_repository=None)
    explainer = Explainer(model_repository=None)
    return ChurnService(
        feature_engineer=feature_eng,
        model_inference=model_inf,
        explainer=explainer,
    )


def get_ltv_service() -> LTVService:
    """Factory for LTVService."""
    feature_eng = LTVFeatureEngineer(
        customer_dao=None,
        order_dao=None,
        customer_ltv_dao=None,
        daily_sales_dao=None,
    )
    model_inf = ModelInference(model_repository=None)
    explainer = Explainer(model_repository=None)
    return LTVService(
        feature_engineer=feature_eng,
        model_inference=model_inf,
        explainer=explainer,
    )


def get_cart_service() -> CartService:
    """Factory for CartService."""
    feature_eng = CartAbandonmentFeatureEngineer(
        customer_dao=None,
        cart_dao=None,
        session_dao=None,
        product_perf_dao=None,
    )
    model_inf = ModelInference(model_repository=None)
    explainer = Explainer(model_repository=None)
    return CartService(
        feature_engineer=feature_eng,
        model_inference=model_inf,
        explainer=explainer,
        cart_dao=None,
    )


def get_pricing_service() -> PricingService:
    """Factory for PricingService."""
    feature_eng = PricingFeatureEngineer(
        product_dao=None,
        daily_sales_dao=None,
        product_perf_dao=None,
        competitor_dao=None,
    )
    model_inf = ModelInference(model_repository=None)
    explainer = Explainer(model_repository=None)
    return PricingService(
        feature_engineer=feature_eng,
        model_inference=model_inf,
        explainer=explainer,
        pricing_dao=None,
    )


def get_campaign_service() -> CampaignService:
    """Factory for CampaignService."""
    return CampaignService(campaign_dao=None)


def get_experiment_service() -> ExperimentService:
    """Factory for ExperimentService."""
    return ExperimentService(experiment_dao=None)


def get_dashboard_service(
    churn_svc: ChurnService = Depends(get_churn_service),
    ltv_svc: LTVService = Depends(get_ltv_service),
    cart_svc: CartService = Depends(get_cart_service),
    pricing_svc: PricingService = Depends(get_pricing_service),
) -> DashboardService:
    """Factory for DashboardService."""
    return DashboardService(
        churn_service=churn_svc,
        ltv_service=ltv_svc,
        cart_service=cart_svc,
        pricing_service=pricing_svc,
        analytics_dao=None,
    )


def get_export_service(
    churn_svc: ChurnService = Depends(get_churn_service),
    cart_svc: CartService = Depends(get_cart_service),
) -> ExportService:
    """Factory for ExportService."""
    return ExportService(
        churn_service=churn_svc,
        cart_service=cart_svc,
    )
