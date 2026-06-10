"""A/B testing and experiment service (Task 3.6)."""

import logging
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    """A/B test experiment."""

    experiment_id: str
    name: str
    treatments: List[str]  # e.g., ["control", "10%_discount", "15%_discount"]
    metric: str  # e.g., "recovery_rate"
    start_date_iso: str
    end_date_iso: str
    status: str  # "running", "completed"
    sample_size_per_treatment: int


@dataclass
class ExperimentResults:
    """A/B test results with statistical significance."""

    experiment_id: str
    treatment_results: Dict[str, Dict]  # {treatment: {conversions, sent, rate, ci_lower, ci_upper}}
    winner: Optional[str] = None
    p_value: Optional[float] = None
    significant_at_95: Optional[bool] = None
    recommendation: Optional[str] = None


class ExperimentService:
    """Business logic for A/B testing and pricing experiments."""

    def __init__(self, experiment_dao=None):
        """Initialize ExperimentService.

        Args:
            experiment_dao: Optional DAO for Cassandra experiment tables
        """
        self.experiment_dao = experiment_dao

    def create_discount_experiment(
        self,
        name: str,
        treatments: List[Dict],  # [{name: "10%", discount_pct: 10}, ...]
        metric: str,  # "recovery_rate"
        start_date_iso: str,
        end_date_iso: str,
        sample_size_per_treatment: int = 1000,
    ) -> Experiment:
        """Create pricing discount A/B experiment.

        Args:
            name: Experiment name (e.g., "Q3 Recovery Discount Test")
            treatments: List of treatment dicts with name and parameters
            metric: Metric to measure (e.g., "recovery_rate", "conversion_rate")
            start_date_iso: Experiment start
            end_date_iso: Experiment end
            sample_size_per_treatment: How many per treatment

        Returns:
            Experiment record

        REQ-019: Create pricing experiment
        """
        experiment_id = f"exp_{datetime.utcnow().isoformat()}_pricing"
        treatment_names = [t["name"] for t in treatments]

        experiment = Experiment(
            experiment_id=experiment_id,
            name=name,
            treatments=treatment_names,
            metric=metric,
            start_date_iso=start_date_iso,
            end_date_iso=end_date_iso,
            status="running",
            sample_size_per_treatment=sample_size_per_treatment,
        )

        logger.info(
            f"Created experiment {experiment_id} with treatments: {treatment_names}"
        )
        return experiment

    def get_treatment_for_cart(
        self,
        experiment_id: str,
        customer_id: str,
    ) -> str:
        """Deterministically assign cart to treatment.

        Args:
            experiment_id: Experiment ID
            customer_id: Customer ID

        Returns:
            Treatment name (e.g., "control", "10%_discount")

        REQ-019: Deterministic assignment
        """
        # Use hash of (experiment_id + customer_id) to determine treatment
        hash_input = f"{experiment_id}:{customer_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        # Simplified: assign to treatment based on hash
        # In real implementation, would have full treatment list
        treatments = ["control", "treatment_a", "treatment_b", "treatment_c"]
        treatment_index = hash_value % len(treatments)

        return treatments[treatment_index]

    def track_experiment_event(
        self,
        experiment_id: str,
        customer_id: str,
        event_type: str,  # "conversion", "no_conversion"
        data: Dict,
    ):
        """Record experiment event.

        Args:
            experiment_id: Experiment ID
            customer_id: Customer ID
            event_type: Type of event
            data: Event data {order_value, timestamp, etc}

        REQ-019: Track events
        """
        event_record = {
            "experiment_id": experiment_id,
            "customer_id": customer_id,
            "event_type": event_type,
            "occurred_at": datetime.utcnow().isoformat(),
            "data": data,
        }

        logger.info(f"Recorded {event_type} for {experiment_id}/{customer_id}")
        return event_record

    def analyze_experiment_results(
        self,
        experiment_id: str,
        treatment_data: Dict[str, List[Dict]],
    ) -> ExperimentResults:
        """Analyze experiment results with statistical significance testing.

        Args:
            experiment_id: Experiment ID
            treatment_data: {treatment_name: [event records]}

        Returns:
            ExperimentResults with p-value, confidence intervals, winner

        REQ-019: Analyze results with significance
        """
        treatment_results = {}
        conversions_by_treatment = {}

        # Calculate conversion rates for each treatment
        for treatment_name, events in treatment_data.items():
            total_events = len(events)
            converted = sum(1 for e in events if e.get("event_type") == "conversion")

            conversion_rate = (converted / total_events * 100) if total_events > 0 else 0

            # Calculate confidence interval (95%)
            ci_lower, ci_upper = self._calculate_confidence_interval(
                converted, total_events
            )

            treatment_results[treatment_name] = {
                "sent": total_events,
                "conversions": converted,
                "conversion_rate": conversion_rate,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
            }

            conversions_by_treatment[treatment_name] = [
                1 if e.get("event_type") == "conversion" else 0 for e in events
            ]

        # Calculate statistical significance (2-sample proportion test)
        p_value = None
        significant = False
        treatment_names = list(treatment_data.keys())

        if len(treatment_names) >= 2:
            # Compare first treatment to control (assuming control is first or named "control")
            control_name = (
                "control" if "control" in treatment_names else treatment_names[0]
            )
            treatment_name = (
                treatment_names[1] if treatment_names[0] == control_name else treatment_names[0]
            )

            control_conversions = sum(conversions_by_treatment[control_name])
            treatment_conversions = sum(conversions_by_treatment[treatment_name])
            control_size = len(conversions_by_treatment[control_name])
            treatment_size = len(conversions_by_treatment[treatment_name])

            if control_size > 0 and treatment_size > 0:
                # Perform chi-square test
                contingency_table = [
                    [control_conversions, control_size - control_conversions],
                    [treatment_conversions, treatment_size - treatment_conversions],
                ]

                try:
                    chi2, p_value, _, _ = stats.chi2_contingency(contingency_table)
                    significant = p_value < 0.05
                except Exception as e:
                    logger.error(f"Error computing chi-square: {e}")

        # Determine winner
        winner = None
        if treatment_results:
            winner = max(
                treatment_results.items(),
                key=lambda x: x[1]["conversion_rate"],
            )[0]

        # Generate recommendation
        recommendation = None
        if significant and winner:
            winner_rate = treatment_results[winner]["conversion_rate"]
            # Find control rate
            control_rate = next(
                (v["conversion_rate"] for k, v in treatment_results.items() if k == "control"),
                0,
            )
            lift = ((winner_rate - control_rate) / control_rate * 100) if control_rate > 0 else 0
            recommendation = f"SIGNIFICANT: Scale up {winner} (lift: {lift:.1f}%)"

        return ExperimentResults(
            experiment_id=experiment_id,
            treatment_results=treatment_results,
            winner=winner,
            p_value=p_value,
            significant_at_95=significant,
            recommendation=recommendation,
        )

    @staticmethod
    def _calculate_confidence_interval(successes: int, total: int, confidence: float = 0.95):
        """Calculate 95% confidence interval for proportion.

        Args:
            successes: Number of successes
            total: Total trials
            confidence: Confidence level (default 0.95)

        Returns:
            Tuple of (lower, upper) bounds
        """
        if total == 0:
            return 0, 0

        proportion = successes / total
        z_score = 1.96  # For 95% confidence

        std_error = (proportion * (1 - proportion) / total) ** 0.5
        margin_of_error = z_score * std_error

        lower = max(0, proportion - margin_of_error) * 100
        upper = min(1, proportion + margin_of_error) * 100

        return lower, upper
