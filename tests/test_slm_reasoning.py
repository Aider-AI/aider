from aider.slm.reasoning import ReasoningEngine


def test_gas_burned_expected_profit_prompt() -> None:
    eng = ReasoningEngine()
    line = "[WARN] Gas Burned > Expected Profit: tx=0xabc gas=123 profit=45"
    decision = eng.decision_from_log(line)
    assert decision is not None
    assert "/code" in decision.prompt
    assert "src/main.rs" in (decision.files or [])


def test_slm_prompt_passthrough() -> None:
    eng = ReasoningEngine()
    decision = eng.decision_from_log("INFO SLM_PROMPT: do the thing")
    assert decision is not None
    assert decision.prompt == "do the thing"


def test_relevant_error_line_generates_prompt() -> None:
    eng = ReasoningEngine()
    decision = eng.decision_from_log("ERROR slippage too high for trade")
    assert decision is not None
    assert "Investigate" in decision.prompt


def test_irrelevant_error_line_is_ignored() -> None:
    eng = ReasoningEngine()
    assert eng.decision_from_log("ERROR database connection failed") is None
