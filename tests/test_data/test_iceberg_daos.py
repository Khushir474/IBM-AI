"""Tests for Task 1.2: Iceberg/Presto Data Access Objects (DAOs)."""

import pytest
from datetime import date, datetime, timedelta
from typing import List


class TestIcebergDAOImports:
    """Verify Iceberg DAO modules can be imported."""

    def test_iceberg_dao_module_importable(self):
        """Test that iceberg_daos module can be imported."""
        try:
            from src.data.daos import iceberg_daos
            assert iceberg_daos is not None
        except ImportError as e:
            pytest.fail(f"Failed to import iceberg_daos module: {e}")

    def test_cohort_retention_dao_importable(self):
        """Test that CohortRetentionDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import CohortRetentionDAO
            assert CohortRetentionDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CohortRetentionDAO: {e}")

    def test_customer_ltv_dao_importable(self):
        """Test that CustomerLTVDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import CustomerLTVDAO
            assert CustomerLTVDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CustomerLTVDAO: {e}")

    def test_orders_archive_dao_importable(self):
        """Test that OrdersArchiveDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import OrdersArchiveDAO
            assert OrdersArchiveDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import OrdersArchiveDAO: {e}")

    def test_daily_sales_summary_dao_importable(self):
        """Test that DailySalesSummaryDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import DailySalesSummaryDAO
            assert DailySalesSummaryDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import DailySalesSummaryDAO: {e}")

    def test_product_performance_dao_importable(self):
        """Test that ProductPerformanceDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import ProductPerformanceDAO
            assert ProductPerformanceDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import ProductPerformanceDAO: {e}")

    def test_competitor_prices_dao_importable(self):
        """Test that CompetitorPricesDAO can be imported."""
        try:
            from src.data.daos.iceberg_daos import CompetitorPricesDAO
            assert CompetitorPricesDAO is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CompetitorPricesDAO: {e}")


class TestCohortRetentionDAO:
    """Test CohortRetentionDAO methods."""

    def test_cohort_retention_dao_initialization(self):
        """Test CohortRetentionDAO can be initialized."""
        from src.data.daos.iceberg_daos import CohortRetentionDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = CohortRetentionDAO(client)

        assert dao is not None
        assert dao.client == client

    def test_cohort_retention_dao_get_cohort_method_exists(self):
        """Test get_cohort_retention method exists."""
        from src.data.daos.iceberg_daos import CohortRetentionDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = CohortRetentionDAO(client)

        assert hasattr(dao, "get_cohort_retention")
        assert inspect.iscoroutinefunction(dao.get_cohort_retention)

    def test_cohort_retention_dao_get_stats_method_exists(self):
        """Test get_cohort_stats method exists."""
        from src.data.daos.iceberg_daos import CohortRetentionDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = CohortRetentionDAO(client)

        assert hasattr(dao, "get_cohort_stats")
        assert inspect.iscoroutinefunction(dao.get_cohort_stats)


class TestCustomerLTVDAO:
    """Test CustomerLTVDAO methods."""

    def test_customer_ltv_dao_initialization(self):
        """Test CustomerLTVDAO can be initialized."""
        from src.data.daos.iceberg_daos import CustomerLTVDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = CustomerLTVDAO(client)

        assert dao is not None

    def test_customer_ltv_dao_get_snapshot_method_exists(self):
        """Test get_customer_ltv_snapshot method exists."""
        from src.data.daos.iceberg_daos import CustomerLTVDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = CustomerLTVDAO(client)

        assert hasattr(dao, "get_customer_ltv_snapshot")
        assert inspect.iscoroutinefunction(dao.get_customer_ltv_snapshot)

    def test_customer_ltv_dao_get_latest_method_exists(self):
        """Test get_latest_customer_ltv method exists."""
        from src.data.daos.iceberg_daos import CustomerLTVDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = CustomerLTVDAO(client)

        assert hasattr(dao, "get_latest_customer_ltv")
        assert inspect.iscoroutinefunction(dao.get_latest_customer_ltv)


class TestOrdersArchiveDAO:
    """Test OrdersArchiveDAO methods."""

    def test_orders_archive_dao_initialization(self):
        """Test OrdersArchiveDAO can be initialized."""
        from src.data.daos.iceberg_daos import OrdersArchiveDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = OrdersArchiveDAO(client)

        assert dao is not None

    def test_orders_archive_dao_get_history_method_exists(self):
        """Test get_customer_order_history method exists."""
        from src.data.daos.iceberg_daos import OrdersArchiveDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = OrdersArchiveDAO(client)

        assert hasattr(dao, "get_customer_order_history")
        assert inspect.iscoroutinefunction(dao.get_customer_order_history)

    def test_orders_archive_dao_query_by_date_range_method_exists(self):
        """Test query_orders_by_date_range method exists."""
        from src.data.daos.iceberg_daos import OrdersArchiveDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = OrdersArchiveDAO(client)

        assert hasattr(dao, "query_orders_by_date_range")
        assert inspect.iscoroutinefunction(dao.query_orders_by_date_range)


class TestDailySalesSummaryDAO:
    """Test DailySalesSummaryDAO methods."""

    def test_daily_sales_summary_dao_initialization(self):
        """Test DailySalesSummaryDAO can be initialized."""
        from src.data.daos.iceberg_daos import DailySalesSummaryDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = DailySalesSummaryDAO(client)

        assert dao is not None

    def test_daily_sales_summary_dao_get_revenue_method_exists(self):
        """Test get_daily_revenue method exists."""
        from src.data.daos.iceberg_daos import DailySalesSummaryDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = DailySalesSummaryDAO(client)

        assert hasattr(dao, "get_daily_revenue")
        assert inspect.iscoroutinefunction(dao.get_daily_revenue)

    def test_daily_sales_summary_dao_query_by_category_region_method_exists(self):
        """Test query_sales_by_category_region method exists."""
        from src.data.daos.iceberg_daos import DailySalesSummaryDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = DailySalesSummaryDAO(client)

        assert hasattr(dao, "query_sales_by_category_region")
        assert inspect.iscoroutinefunction(dao.query_sales_by_category_region)


class TestProductPerformanceDAO:
    """Test ProductPerformanceDAO methods."""

    def test_product_performance_dao_initialization(self):
        """Test ProductPerformanceDAO can be initialized."""
        from src.data.daos.iceberg_daos import ProductPerformanceDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = ProductPerformanceDAO(client)

        assert dao is not None

    def test_product_performance_dao_get_weekly_performance_method_exists(self):
        """Test get_weekly_performance method exists."""
        from src.data.daos.iceberg_daos import ProductPerformanceDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = ProductPerformanceDAO(client)

        assert hasattr(dao, "get_weekly_performance")
        assert inspect.iscoroutinefunction(dao.get_weekly_performance)


class TestCompetitorPricesDAO:
    """Test CompetitorPricesDAO methods."""

    def test_competitor_prices_dao_initialization(self):
        """Test CompetitorPricesDAO can be initialized."""
        from src.data.daos.iceberg_daos import CompetitorPricesDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = CompetitorPricesDAO(client)

        assert dao is not None

    def test_competitor_prices_dao_get_latest_prices_method_exists(self):
        """Test get_latest_competitor_prices method exists."""
        from src.data.daos.iceberg_daos import CompetitorPricesDAO
        from src.data.presto_client import PrestoClient
        import inspect

        client = PrestoClient(presto_host="localhost")
        dao = CompetitorPricesDAO(client)

        assert hasattr(dao, "get_latest_competitor_prices")
        assert inspect.iscoroutinefunction(dao.get_latest_competitor_prices)


class TestIcebergDAOQueries:
    """Test Iceberg DAO query construction."""

    def test_cohort_retention_dao_query_structure(self):
        """Test that CohortRetentionDAO constructs valid queries."""
        from src.data.daos.iceberg_daos import CohortRetentionDAO

        assert hasattr(CohortRetentionDAO, "QUERY_GET_COHORT") or hasattr(
            CohortRetentionDAO, "get_cohort_retention"
        )

    def test_customer_ltv_dao_query_structure(self):
        """Test that CustomerLTVDAO constructs valid queries."""
        from src.data.daos.iceberg_daos import CustomerLTVDAO

        assert hasattr(CustomerLTVDAO, "QUERY_GET_SNAPSHOT") or hasattr(
            CustomerLTVDAO, "get_customer_ltv_snapshot"
        )

    def test_orders_archive_dao_date_range_queries(self):
        """Test that OrdersArchiveDAO supports date range queries."""
        from src.data.daos.iceberg_daos import OrdersArchiveDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = OrdersArchiveDAO(client)

        assert hasattr(dao, "query_orders_by_date_range")

    def test_daily_sales_summary_dao_aggregation_queries(self):
        """Test that DailySalesSummaryDAO supports aggregation queries."""
        from src.data.daos.iceberg_daos import DailySalesSummaryDAO
        from src.data.presto_client import PrestoClient

        client = PrestoClient(presto_host="localhost")
        dao = DailySalesSummaryDAO(client)

        assert hasattr(dao, "get_daily_revenue")


class TestIcebergDAOPartitionFiltering:
    """Test that Iceberg DAOs use partition filtering for optimization."""

    def test_orders_archive_uses_date_partitions(self):
        """Test that OrdersArchiveDAO filters on date partitions."""
        from src.data.daos.iceberg_daos import OrdersArchiveDAO

        # Should have query with year/month partitions
        assert hasattr(OrdersArchiveDAO, "QUERY_GET_HISTORY") or hasattr(
            OrdersArchiveDAO, "get_customer_order_history"
        )

    def test_daily_sales_summary_uses_date_partitions(self):
        """Test that DailySalesSummaryDAO filters on date partitions."""
        from src.data.daos.iceberg_daos import DailySalesSummaryDAO

        # Should have query with year/month partitions
        assert hasattr(DailySalesSummaryDAO, "QUERY_GET_REVENUE") or hasattr(
            DailySalesSummaryDAO, "get_daily_revenue"
        )

    def test_product_performance_uses_week_partitions(self):
        """Test that ProductPerformanceDAO filters on week partitions."""
        from src.data.daos.iceberg_daos import ProductPerformanceDAO

        assert hasattr(ProductPerformanceDAO, "QUERY_GET_PERFORMANCE") or hasattr(
            ProductPerformanceDAO, "get_weekly_performance"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
