class CostTracker:

    # Gemini 3.7 Flash Standard pricing
    # USD per 1 million tokens
    INPUT_PRICE_PER_MILLION = 0.75
    OUTPUT_PRICE_PER_MILLION = 3.75

    def __init__(self):
        self.total_queries = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:

        input_cost = (
            input_tokens
            / 1_000_000
            * self.INPUT_PRICE_PER_MILLION
        )

        output_cost = (
            output_tokens
            / 1_000_000
            * self.OUTPUT_PRICE_PER_MILLION
        )

        return input_cost + output_cost

    def record(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0
    ):
        billed_output_tokens = (
            output_tokens + thinking_tokens
        )

        cost = self.calculate_cost(
            input_tokens,
            billed_output_tokens
        )

        self.total_queries += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += billed_output_tokens
        self.total_cost += cost

    def average_cost_per_query(self):
        if self.total_queries == 0:
            return 0.0

        return self.total_cost / self.total_queries