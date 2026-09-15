from __future__ import annotations

import os
from threading import Lock


class CostTracker:
    """
    Thread-safe in-memory usage and cost tracker.

    Pricing is configurable through environment variables:

        INPUT_PRICE_PER_MILLION
        OUTPUT_PRICE_PER_MILLION

    Prices are expressed in USD per 1 million tokens.

    The tracker is intentionally in-memory for the current
    project architecture. It is suitable for local development
    and a single application process.

    It should not be treated as durable billing storage.
    """

    DEFAULT_INPUT_PRICE_PER_MILLION = 0.75
    DEFAULT_OUTPUT_PRICE_PER_MILLION = 3.75

    def __init__(
        self,
        input_price_per_million: float | None = None,
        output_price_per_million: float | None = None,
    ):
        self.input_price_per_million = (
            self._get_price(
                env_name="INPUT_PRICE_PER_MILLION",
                default=(
                    self.DEFAULT_INPUT_PRICE_PER_MILLION
                ),
                explicit_value=(
                    input_price_per_million
                ),
            )
        )

        self.output_price_per_million = (
            self._get_price(
                env_name="OUTPUT_PRICE_PER_MILLION",
                default=(
                    self.DEFAULT_OUTPUT_PRICE_PER_MILLION
                ),
                explicit_value=(
                    output_price_per_million
                ),
            )
        )

        self.total_queries = 0

        self.total_input_tokens = 0

        self.total_output_tokens = 0

        self.total_thinking_tokens = 0

        self.total_billed_output_tokens = 0

        self.total_cost = 0.0

        self._lock = Lock()

    # ========================================================
    # Configuration
    # ========================================================

    @staticmethod
    def _get_price(
        env_name: str,
        default: float,
        explicit_value: float | None,
    ) -> float:

        if explicit_value is not None:

            if explicit_value < 0:
                raise ValueError(
                    f"{env_name} cannot be negative."
                )

            return float(
                explicit_value
            )

        environment_value = os.getenv(
            env_name
        )

        if environment_value is None:
            return float(
                default
            )

        try:
            price = float(
                environment_value
            )

        except ValueError as error:

            raise ValueError(
                f"{env_name} must be a valid number."
            ) from error

        if price < 0:
            raise ValueError(
                f"{env_name} cannot be negative."
            )

        return price

    # ========================================================
    # Cost calculation
    # ========================================================

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate cost for a single model call.

        `output_tokens` should represent the tokens that
        should be billed as output.

        The method does not modify tracker state.
        """

        self._validate_tokens(
            input_tokens,
            "input_tokens",
        )

        self._validate_tokens(
            output_tokens,
            "output_tokens",
        )

        input_cost = (
            input_tokens
            / 1_000_000
            * self.input_price_per_million
        )

        output_cost = (
            output_tokens
            / 1_000_000
            * self.output_price_per_million
        )

        return (
            input_cost
            + output_cost
        )

    # ========================================================
    # Record usage
    # ========================================================

    def record(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
    ) -> float:
        """
        Record usage for one model call.

        Returns:
            Calculated cost for this call.

        `output_tokens` and `thinking_tokens` are kept
        separately, while `total_output_tokens` preserves
        normal generated output only.

        `total_billed_output_tokens` represents the value
        actually passed to the cost calculation.
        """

        self._validate_tokens(
            input_tokens,
            "input_tokens",
        )

        self._validate_tokens(
            output_tokens,
            "output_tokens",
        )

        self._validate_tokens(
            thinking_tokens,
            "thinking_tokens",
        )

        billed_output_tokens = (
            output_tokens
            + thinking_tokens
        )

        cost = self.calculate_cost(
            input_tokens=input_tokens,
            output_tokens=billed_output_tokens,
        )

        with self._lock:

            self.total_queries += 1

            self.total_input_tokens += (
                input_tokens
            )

            self.total_output_tokens += (
                output_tokens
            )

            self.total_thinking_tokens += (
                thinking_tokens
            )

            self.total_billed_output_tokens += (
                billed_output_tokens
            )

            self.total_cost += cost

        return cost

    # ========================================================
    # Statistics
    # ========================================================

    def average_cost_per_query(self) -> float:
        """
        Return the average recorded cost per query.
        """

        with self._lock:

            if self.total_queries == 0:
                return 0.0

            return (
                self.total_cost
                / self.total_queries
            )

    def snapshot(self) -> dict[str, float | int]:
        """
        Return a consistent snapshot of current usage.

        Useful for API metrics and monitoring.
        """

        with self._lock:

            return {
                "total_queries": (
                    self.total_queries
                ),
                "total_input_tokens": (
                    self.total_input_tokens
                ),
                "total_output_tokens": (
                    self.total_output_tokens
                ),
                "total_thinking_tokens": (
                    self.total_thinking_tokens
                ),
                "total_billed_output_tokens": (
                    self.total_billed_output_tokens
                ),
                "total_cost": (
                    self.total_cost
                ),
                "average_cost_per_query": (
                    (
                        self.total_cost
                        / self.total_queries
                    )
                    if self.total_queries
                    else 0.0
                ),
                "input_price_per_million": (
                    self.input_price_per_million
                ),
                "output_price_per_million": (
                    self.output_price_per_million
                ),
            }

    # ========================================================
    # Validation
    # ========================================================

    @staticmethod
    def _validate_tokens(
        value: int,
        name: str,
    ) -> None:

        if isinstance(value, bool):
            raise ValueError(
                f"{name} must be an integer."
            )

        if not isinstance(value, int):
            raise ValueError(
                f"{name} must be an integer."
            )

        if value < 0:
            raise ValueError(
                f"{name} cannot be negative."
            )