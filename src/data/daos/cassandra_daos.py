"""Cassandra Data Access Objects for hot/operational data.

Implements query methods for all Cassandra tables:
- customers, orders_inflight, order_items_inflight
- products, active_carts
- live_sessions
- inventory_ledger_recent, reviews_recent
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

import structlog

from src.data.cassandra_client import CassandraClient

logger = structlog.get_logger(__name__)


class CustomerDAO:
    """Data Access Object for customer data from Cassandra."""

    QUERY_GET_CUSTOMER = "SELECT * FROM cassandra.ecommerce.customers WHERE customer_id = ?"
    QUERY_LIST_CUSTOMERS = "SELECT * FROM cassandra.ecommerce.customers WHERE customer_id IN ?"
    QUERY_GET_BY_EMAIL = "SELECT * FROM cassandra.ecommerce.customers_by_email WHERE email = ?"

    def __init__(self, client: CassandraClient):
        """Initialize CustomerDAO.

        Args:
            client: CassandraClient instance for queries
        """
        self.client = client

    async def get_customer(self, customer_id: UUID) -> Optional[Dict[str, Any]]:
        """Get customer by ID.

        Args:
            customer_id: Customer UUID

        Returns:
            Customer dict or None if not found
        """
        rows = await self.client.execute(
            self.QUERY_GET_CUSTOMER,
            [customer_id],
        )
        return rows[0] if rows else None

    async def list_customers_by_ids(self, customer_ids: List[UUID]) -> List[Dict[str, Any]]:
        """Get multiple customers by IDs.

        Args:
            customer_ids: List of customer UUIDs

        Returns:
            List of customer dicts
        """
        if not customer_ids:
            return []

        rows = await self.client.execute(
            self.QUERY_LIST_CUSTOMERS,
            [customer_ids],
        )
        return rows

    async def get_customers_by_email_index(self, email: str) -> Optional[Dict[str, Any]]:
        """Get customer by email (secondary index lookup).

        Args:
            email: Customer email address

        Returns:
            Customer dict or None if not found
        """
        rows = await self.client.execute(
            self.QUERY_GET_BY_EMAIL,
            [email],
        )
        return rows[0] if rows else None


class OrderDAO:
    """Data Access Object for order data from Cassandra."""

    QUERY_GET_INFLIGHT_ORDERS = (
        "SELECT * FROM cassandra.ecommerce.orders_inflight "
        "WHERE customer_id = ? ORDER BY order_date DESC LIMIT ?"
    )
    QUERY_GET_ORDER_ITEMS = "SELECT * FROM cassandra.ecommerce.order_items_inflight WHERE order_id = ?"

    def __init__(self, client: CassandraClient):
        """Initialize OrderDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_inflight_orders(
        self, customer_id: UUID, limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent inflight orders for customer.

        Args:
            customer_id: Customer UUID
            limit: Max number of orders to return

        Returns:
            List of order dicts
        """
        rows = await self.client.execute(
            self.QUERY_GET_INFLIGHT_ORDERS,
            [customer_id, limit],
        )
        return rows

    async def get_order_items(self, order_id: UUID) -> List[Dict[str, Any]]:
        """Get line items for an order.

        Args:
            order_id: Order UUID

        Returns:
            List of order item dicts
        """
        rows = await self.client.execute(
            self.QUERY_GET_ORDER_ITEMS,
            [order_id],
        )
        return rows


class ProductDAO:
    """Data Access Object for product data from Cassandra."""

    QUERY_GET_PRODUCT = "SELECT * FROM cassandra.ecommerce.products WHERE product_id = ?"
    QUERY_GET_PRODUCTS_BATCH = "SELECT * FROM cassandra.ecommerce.products WHERE product_id IN ?"
    QUERY_GET_BY_CATEGORY = "SELECT * FROM cassandra.ecommerce.products_by_category WHERE category = ?"

    def __init__(self, client: CassandraClient):
        """Initialize ProductDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_product(self, product_id: UUID) -> Optional[Dict[str, Any]]:
        """Get product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product dict or None if not found
        """
        rows = await self.client.execute(
            self.QUERY_GET_PRODUCT,
            [product_id],
        )
        return rows[0] if rows else None

    async def get_products_batch(self, product_ids: List[UUID]) -> List[Dict[str, Any]]:
        """Get multiple products by IDs (batch operation).

        Args:
            product_ids: List of product UUIDs

        Returns:
            List of product dicts
        """
        if not product_ids:
            return []

        rows = await self.client.execute(
            self.QUERY_GET_PRODUCTS_BATCH,
            [product_ids],
        )
        return rows

    async def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all products in a category.

        Args:
            category: Category name

        Returns:
            List of product dicts
        """
        rows = await self.client.execute(
            self.QUERY_GET_BY_CATEGORY,
            [category],
        )
        return rows


class CartDAO:
    """Data Access Object for shopping cart data from Cassandra."""

    QUERY_GET_ACTIVE_CARTS = "SELECT * FROM cassandra.ecommerce.active_carts WHERE customer_id = ?"
    QUERY_DETECT_ABANDONED = (
        "SELECT * FROM cassandra.ecommerce.active_carts "
        "WHERE updated_at < ? ALLOW FILTERING"
    )
    QUERY_INSERT_CART_ITEM = (
        "INSERT INTO cassandra.ecommerce.active_carts "
        "(customer_id, product_id, quantity, unit_price, added_at) VALUES (?, ?, ?, ?, ?)"
    )
    QUERY_DELETE_CART_ITEM = (
        "DELETE FROM cassandra.ecommerce.active_carts "
        "WHERE customer_id = ? AND product_id = ?"
    )

    def __init__(self, client: CassandraClient):
        """Initialize CartDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_active_carts(self, customer_id: UUID) -> List[Dict[str, Any]]:
        """Get active cart items for customer.

        Args:
            customer_id: Customer UUID

        Returns:
            List of cart item dicts
        """
        rows = await self.client.execute(
            self.QUERY_GET_ACTIVE_CARTS,
            [customer_id],
        )
        return rows

    async def detect_abandoned_carts(self, idle_minutes: int = 60) -> List[Dict[str, Any]]:
        """Detect abandoned carts (idle for N minutes).

        Args:
            idle_minutes: Idle threshold in minutes

        Returns:
            List of abandoned cart item dicts
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=idle_minutes)

        rows = await self.client.execute(
            self.QUERY_DETECT_ABANDONED,
            [cutoff_time],
        )
        return rows

    async def insert_cart_item(
        self,
        customer_id: UUID,
        product_id: UUID,
        quantity: int,
        unit_price: float,
    ) -> None:
        """Insert or update a cart item.

        Args:
            customer_id: Customer UUID
            product_id: Product UUID
            quantity: Item quantity
            unit_price: Price per unit
        """
        await self.client.execute(
            self.QUERY_INSERT_CART_ITEM,
            [customer_id, product_id, quantity, unit_price, datetime.utcnow()],
        )

        logger.info(
            "cart_item_inserted",
            customer_id=str(customer_id),
            product_id=str(product_id),
            quantity=quantity,
        )

    async def delete_cart_item(self, customer_id: UUID, product_id: UUID) -> None:
        """Delete a cart item.

        Args:
            customer_id: Customer UUID
            product_id: Product UUID
        """
        await self.client.execute(
            self.QUERY_DELETE_CART_ITEM,
            [customer_id, product_id],
        )

        logger.info(
            "cart_item_deleted",
            customer_id=str(customer_id),
            product_id=str(product_id),
        )


class SessionDAO:
    """Data Access Object for user session data from Cassandra."""

    QUERY_GET_RECENT_SESSIONS = (
        "SELECT * FROM cassandra.ecommerce.live_sessions "
        "WHERE customer_id = ? ORDER BY session_id DESC LIMIT ?"
    )

    def __init__(self, client: CassandraClient):
        """Initialize SessionDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_recent_sessions(
        self, customer_id: UUID, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent sessions for customer (engagement signal).

        Args:
            customer_id: Customer UUID
            limit: Max number of sessions to return

        Returns:
            List of session dicts
        """
        rows = await self.client.execute(
            self.QUERY_GET_RECENT_SESSIONS,
            [customer_id, limit],
        )
        return rows


class InventoryLedgerDAO:
    """Data Access Object for inventory movements from Cassandra."""

    QUERY_GET_RECENT_MOVEMENTS = (
        "SELECT * FROM cassandra.ecommerce.inventory_ledger_recent "
        "WHERE product_id = ? AND movement_date > ? ALLOW FILTERING"
    )

    def __init__(self, client: CassandraClient):
        """Initialize InventoryLedgerDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_recent_movements(
        self, product_id: UUID, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent inventory movements (stock, sales signals).

        Args:
            product_id: Product UUID
            days: Days back to look

        Returns:
            List of movement dicts
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        rows = await self.client.execute(
            self.QUERY_GET_RECENT_MOVEMENTS,
            [product_id, cutoff_date],
        )
        return rows


class ReviewDAO:
    """Data Access Object for product reviews from Cassandra."""

    QUERY_GET_RECENT_REVIEWS = (
        "SELECT * FROM cassandra.ecommerce.reviews_recent "
        "WHERE product_id = ? AND review_date > ? ALLOW FILTERING"
    )

    def __init__(self, client: CassandraClient):
        """Initialize ReviewDAO.

        Args:
            client: CassandraClient instance
        """
        self.client = client

    async def get_recent_reviews(
        self, product_id: UUID, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent reviews for product (sentiment signal).

        Args:
            product_id: Product UUID
            days: Days back to look

        Returns:
            List of review dicts
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        rows = await self.client.execute(
            self.QUERY_GET_RECENT_REVIEWS,
            [product_id, cutoff_date],
        )
        return rows
