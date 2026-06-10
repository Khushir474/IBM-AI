"""Iceberg/Presto Data Access Objects for cold/analytical data.

Implements query methods for all Iceberg analytics tables via Presto:
- cohort_retention, customer_ltv_monthly
- orders_archive, order_items_archive
- daily_sales_summary, product_performance_weekly
- competitor_prices_weekly
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, datetime, timedelta

import structlog

from src.data.presto_client import PrestoClient

logger = structlog.get_logger(__name__)


class CohortRetentionDAO:
    """Data Access Object for cohort retention analytics from Iceberg."""

    QUERY_GET_COHORT = """
        SELECT cohort_year, cohort_month, retention_rate, cohort_size
        FROM iceberg_data.ecommerce.cohort_retention
        WHERE cohort_year = ? AND cohort_month = ?
    """

    QUERY_GET_COHORT_STATS = """
        SELECT *
        FROM iceberg_data.ecommerce.cohort_retention
        WHERE cohort_year = ? AND cohort_month = ?
    """

    def __init__(self, client: PrestoClient):
        """Initialize CohortRetentionDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_cohort_retention(
        self, cohort_year: int, cohort_month: int
    ) -> Optional[Dict[str, Any]]:
        """Get retention rate for cohort.

        Args:
            cohort_year: Cohort year
            cohort_month: Cohort month (1-12)

        Returns:
            Cohort retention dict or None if not found
        """
        rows = await self.client.execute(
            self.QUERY_GET_COHORT,
            [cohort_year, cohort_month],
        )
        return rows[0] if rows else None

    async def get_cohort_stats(
        self, cohort_year: int, cohort_month: int
    ) -> Optional[Dict[str, Any]]:
        """Get detailed stats for cohort.

        Args:
            cohort_year: Cohort year
            cohort_month: Cohort month

        Returns:
            Cohort stats dict
        """
        rows = await self.client.execute(
            self.QUERY_GET_COHORT_STATS,
            [cohort_year, cohort_month],
        )
        return rows[0] if rows else None


class CustomerLTVDAO:
    """Data Access Object for customer LTV data from Iceberg."""

    QUERY_GET_SNAPSHOT = """
        SELECT customer_id, ltv, cumulative_orders, snapshot_year, snapshot_month
        FROM iceberg_data.ecommerce.customer_ltv_monthly
        WHERE customer_id = ? AND snapshot_year = ? AND snapshot_month = ?
    """

    QUERY_GET_LATEST = """
        SELECT customer_id, ltv, cumulative_orders, snapshot_year, snapshot_month
        FROM iceberg_data.ecommerce.customer_ltv_monthly
        WHERE customer_id = ?
        ORDER BY snapshot_year DESC, snapshot_month DESC
        LIMIT 1
    """

    def __init__(self, client: PrestoClient):
        """Initialize CustomerLTVDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_customer_ltv_snapshot(
        self, customer_id: str, snapshot_year: int, snapshot_month: int
    ) -> Optional[Dict[str, Any]]:
        """Get LTV snapshot for specific month.

        Args:
            customer_id: Customer ID
            snapshot_year: Snapshot year
            snapshot_month: Snapshot month

        Returns:
            LTV snapshot dict or None
        """
        rows = await self.client.execute(
            self.QUERY_GET_SNAPSHOT,
            [customer_id, snapshot_year, snapshot_month],
        )
        return rows[0] if rows else None

    async def get_latest_customer_ltv(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get latest LTV snapshot for customer.

        Args:
            customer_id: Customer ID

        Returns:
            Latest LTV snapshot dict or None
        """
        rows = await self.client.execute(
            self.QUERY_GET_LATEST,
            [customer_id],
        )
        return rows[0] if rows else None


class OrdersArchiveDAO:
    """Data Access Object for historical orders from Iceberg."""

    QUERY_GET_HISTORY = """
        SELECT order_id, customer_id, order_date, order_value, items_count
        FROM iceberg_data.ecommerce.orders_archive
        WHERE customer_id = ? AND order_year = ? AND order_month >= ?
        ORDER BY order_date DESC
        LIMIT ?
    """

    QUERY_GET_BY_DATE_RANGE = """
        SELECT order_id, customer_id, order_date, order_value
        FROM iceberg_data.ecommerce.orders_archive
        WHERE order_year = ? AND order_month BETWEEN ? AND ?
        AND order_date BETWEEN ? AND ?
    """

    def __init__(self, client: PrestoClient):
        """Initialize OrdersArchiveDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_customer_order_history(
        self, customer_id: str, days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get customer order history from Iceberg.

        Args:
            customer_id: Customer ID
            days: Days back to look (default 90)

        Returns:
            List of orders
        """
        # Calculate year/month back N days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        order_year = cutoff_date.year
        order_month = cutoff_date.month

        rows = await self.client.execute(
            self.QUERY_GET_HISTORY,
            [customer_id, order_year, order_month, 100],
        )
        return rows

    async def query_orders_by_date_range(
        self, start_date: date, end_date: date, **filters
    ) -> List[Dict[str, Any]]:
        """Query orders by date range with optional filters.

        Args:
            start_date: Start date for range
            end_date: End date for range
            **filters: Optional filters (category, region, etc)

        Returns:
            List of matching orders
        """
        start_year = start_date.year
        start_month = start_date.month
        end_month = end_date.month

        rows = await self.client.execute(
            self.QUERY_GET_BY_DATE_RANGE,
            [start_year, start_month, end_month, start_date, end_date],
        )
        return rows


class DailySalesSummaryDAO:
    """Data Access Object for daily sales aggregations from Iceberg."""

    QUERY_GET_DAILY_REVENUE = """
        SELECT summary_date, net_revenue, units_sold, orders_count
        FROM iceberg_data.ecommerce.daily_sales_summary
        WHERE summary_year = ? AND summary_month = ?
        AND summary_date BETWEEN ? AND ?
    """

    QUERY_GET_BY_CATEGORY_REGION = """
        SELECT summary_date, category, region, net_revenue, units_sold
        FROM iceberg_data.ecommerce.daily_sales_summary
        WHERE summary_year = ? AND summary_month BETWEEN ? AND ?
        AND summary_date BETWEEN ? AND ?
    """

    def __init__(self, client: PrestoClient):
        """Initialize DailySalesSummaryDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_daily_revenue(
        self, date_range: Tuple[date, date], category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get daily revenue summary (baseline for lift calculations).

        Args:
            date_range: Tuple of (start_date, end_date)
            category: Optional category filter

        Returns:
            List of daily summaries
        """
        start_date, end_date = date_range
        start_year = start_date.year
        start_month = start_date.month

        rows = await self.client.execute(
            self.QUERY_GET_DAILY_REVENUE,
            [start_year, start_month, start_date, end_date],
        )
        return rows

    async def query_sales_by_category_region(
        self, start_date: date, end_date: date, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query sales by category and region.

        Args:
            start_date: Start date
            end_date: End date
            category: Optional category filter

        Returns:
            List of sales summaries by category/region
        """
        start_year = start_date.year
        start_month = start_date.month
        end_month = end_date.month

        rows = await self.client.execute(
            self.QUERY_GET_BY_CATEGORY_REGION,
            [start_year, start_month, end_month, start_date, end_date],
        )
        return rows


class ProductPerformanceDAO:
    """Data Access Object for product performance metrics from Iceberg."""

    QUERY_GET_WEEKLY_PERFORMANCE = """
        SELECT product_id, week_year, week_start_date, units_sold, return_rate, conversion_rate
        FROM iceberg_data.ecommerce.product_performance_weekly
        WHERE product_id = ? AND week_year = ?
        ORDER BY week_start_date DESC
        LIMIT ?
    """

    def __init__(self, client: PrestoClient):
        """Initialize ProductPerformanceDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_weekly_performance(
        self, product_id: str, weeks: int = 12
    ) -> List[Dict[str, Any]]:
        """Get weekly performance metrics for product (velocity, return rate).

        Args:
            product_id: Product ID
            weeks: Number of weeks to retrieve (default 12)

        Returns:
            List of weekly performance records
        """
        # Get current year
        current_year = datetime.utcnow().year

        rows = await self.client.execute(
            self.QUERY_GET_WEEKLY_PERFORMANCE,
            [product_id, current_year, weeks],
        )
        return rows


class CompetitorPricesDAO:
    """Data Access Object for competitor pricing data from Iceberg."""

    QUERY_GET_LATEST_PRICES = """
        SELECT product_id, competitor_name, competitor_price, week_start_date
        FROM iceberg_data.ecommerce.competitor_prices_weekly
        WHERE week_start_date >= ?
        ORDER BY week_start_date DESC
    """

    def __init__(self, client: PrestoClient):
        """Initialize CompetitorPricesDAO.

        Args:
            client: PrestoClient instance
        """
        self.client = client

    async def get_latest_competitor_prices(
        self, week_start_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get latest competitor prices for comparison.

        Args:
            week_start_date: Start date (default: last week)

        Returns:
            List of competitor prices
        """
        if not week_start_date:
            # Default to last week
            week_start_date = datetime.utcnow().date() - timedelta(days=7)

        rows = await self.client.execute(
            self.QUERY_GET_LATEST_PRICES,
            [week_start_date],
        )
        return rows
