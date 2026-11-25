import tempfile
import unittest
from pathlib import Path

from aider import energy

HEADER = "model_name,use_case,tier,energy_wh_mean,energy_wh_sd,carbon_gco2e_mean,energy_wh_per_usd"
ROWS = [
    "Claude Opus 4.5,Agentic,Typical,100,20,60,10",
    "Claude Opus 4.1,Agentic,Typical,100,20,60,12",
    "Claude Haiku 4.5,Agentic,Typical,50,5,25,8",
    "Claude Opus 4.5,Chat,Typical,100,20,60,99",
    "Claude Opus 4.5,Agentic,Heavy,100,20,60,99",
    '"GPT-5.4 mini, test",Agentic,Typical,10,1,5,4',
    "Bad,Agentic,Typical,0,1,1,1",
]


def write_csv(rows=ROWS, header=HEADER):
    f = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
    f.write("\n".join([header, *rows]))
    f.close()
    return f.name


class TestEnergy(unittest.TestCase):
    def setUp(self):
        path = write_csv()
        self.addCleanup(Path(path).unlink)
        self.rows = energy.load_table(path)

    def test_load_filters(self):
        self.assertEqual(len(self.rows), 4)

    def test_missing_column(self):
        path = write_csv(header="model_name,use_case")
        self.addCleanup(Path(path).unlink)
        with self.assertRaises(ValueError):
            energy.load_table(path)

    def test_name_key(self):
        self.assertEqual(
            energy.name_key("openrouter/anthropic/claude-opus-4-5-20251101"), "opus 4.5"
        )
        self.assertEqual(energy.name_key("anthropic/claude-sonnet-4-5[1m]"), "sonnet 4.5")

    def test_exact_and_proxy(self):
        fmt = energy.format_estimate
        self.assertEqual(
            fmt(self.rows, "anthropic/claude-opus-4-5", 1.0), "⚡ 8.0-12 Wh · 4.8-7.2 gCO₂e"
        )
        # 4.6 is absent: newest lower version (4.5) is proxied
        self.assertTrue(fmt(self.rows, "claude-opus-4-6", 1.0).startswith("⚡ ~8.0-12 Wh"))
        # 4.0 is below everything: falls back to newest of family
        self.assertTrue(fmt(self.rows, "claude-opus-4", 1.0).startswith("⚡ ~"))

    def test_no_match_or_cost(self):
        fmt = energy.format_estimate
        self.assertEqual(fmt(self.rows, "unknown-model", 1.0), "")
        self.assertEqual(fmt(self.rows, "claude-opus-4-5", 0), "")
        self.assertEqual(fmt(self.rows, "claude-sonnet-4-5", 1.0), "")

    def test_options(self):
        fmt = energy.format_estimate
        self.assertEqual(fmt(self.rows, "claude-opus-4-5", 1.0, carbon=False), "⚡ 8.0-12 Wh")
        # 10 Wh at 500 g/kWh = 5 g, band 4.0-6.0
        self.assertEqual(
            fmt(self.rows, "claude-opus-4-5", 1.0, grid_g_per_kwh=500), "⚡ 8.0-12 Wh · 4.0-6.0 gCO₂e"
        )

    def test_kwh_and_clamp(self):
        self.assertIn("kWh", energy.format_estimate(self.rows, "claude-opus-4-5", 100.0))
        rows = [dict(self.rows[0], sd_ratio=1.5)]
        self.assertTrue(energy.format_estimate(rows, "claude-opus-4-5", 1.0).startswith("⚡ 0-25"))

    def test_small_values(self):
        fmt = energy.format_estimate
        # 0.001 USD x 10 Wh/USD = 0.01 Wh, band tops out below 0.05
        self.assertEqual(fmt(self.rows, "claude-opus-4-5", 0.001), "⚡ <0.1 Wh · <0.1 gCO₂e")
        # 0.04 USD -> 0.32-0.48 Wh, 0.19-0.29 g (opus 4.5 row: 10 Wh/USD, sd 20%, 0.6 g/Wh)
        self.assertEqual(fmt(self.rows, "claude-opus-4-5", 0.04), "⚡ 0.3-0.5 Wh · 0.2-0.3 gCO₂e")
        # a low end that would print "0.0" prints "0"
        self.assertEqual(fmt(self.rows, "claude-opus-4-5", 0.005), "⚡ 0-0.1 Wh · <0.1 gCO₂e")
        # equal ends display once
        rows = [dict(self.rows[0], sd_ratio=0.0)]
        self.assertEqual(energy.format_estimate(rows, "claude-opus-4-5", 0.5), "⚡ 5.0 Wh · 3.0 gCO₂e")

    def test_total_sums_per_model(self):
        # opus 4.5: 1 USD -> 8-12 Wh; haiku 4.5: 1 USD -> 7.2-8.8 Wh (sd 10%)
        total = energy.format_total(self.rows, {"claude-opus-4-5": 1.0, "claude-haiku-4-5": 1.0})
        self.assertTrue(total.startswith("⚡ 15-21 Wh"), total)
        # unmatched model is skipped, not attributed to another model
        only = energy.format_total(self.rows, {"claude-opus-4-5": 1.0, "unknown-model": 5.0})
        self.assertEqual(only, energy.format_estimate(self.rows, "claude-opus-4-5", 1.0))
        self.assertEqual(energy.format_total(self.rows, {}), "")


if __name__ == "__main__":
    unittest.main()
