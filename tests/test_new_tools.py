"""Tests for the new tools: calculator, code_runner, summarizer, timer."""

import pytest
import time

from aura.tools.calculator import CalculatorTool
from aura.tools.code_runner import CodeRunnerTool
from aura.tools.summarizer import SummarizerTool
from aura.tools.timer import TimerTool, _timers


class TestCalculatorTool:
    def setup_method(self):
        self.tool = CalculatorTool()

    def test_name(self):
        assert self.tool.name == "calculator"

    def test_addition(self):
        result = self.tool.run("2 + 2")
        assert "4" in result

    def test_multiplication(self):
        result = self.tool.run("7 * 8")
        assert "56" in result

    def test_division(self):
        result = self.tool.run("10 / 4")
        assert "2.5" in result

    def test_power(self):
        result = self.tool.run("2 ** 10")
        assert "1024" in result

    def test_sqrt(self):
        result = self.tool.run("sqrt(144)")
        assert "12" in result

    def test_pi(self):
        result = self.tool.run("pi")
        assert "3.14" in result

    def test_complex_expression(self):
        result = self.tool.run("(3 + 4) * 2")
        assert "14" in result

    def test_division_by_zero(self):
        result = self.tool.run("1 / 0")
        assert "Error" in result

    def test_empty_input(self):
        result = self.tool.run("")
        assert "calculator" in result.lower()

    def test_invalid_expression(self):
        result = self.tool.run("hello world")
        assert "Error" in result

    def test_negative_numbers(self):
        result = self.tool.run("-5 + 3")
        assert "-2" in result


class TestCodeRunnerTool:
    def setup_method(self):
        self.tool = CodeRunnerTool()

    def test_name(self):
        assert self.tool.name == "code_runner"

    def test_hello_world(self):
        result = self.tool.run('print("Hello, world!")')
        assert "Hello, world!" in result

    def test_math(self):
        result = self.tool.run("print(2 + 2)")
        assert "4" in result

    def test_empty_input(self):
        result = self.tool.run("")
        assert "code_runner" in result.lower()

    def test_syntax_error(self):
        result = self.tool.run("def")
        assert "stderr" in result.lower() or "Error" in result or "exit code" in result

    def test_loop(self):
        result = self.tool.run("for i in range(3): print(i)")
        assert "0" in result
        assert "1" in result
        assert "2" in result


class TestSummarizerTool:
    def setup_method(self):
        self.tool = SummarizerTool()

    def test_name(self):
        assert self.tool.name == "summarizer"

    def test_empty_input(self):
        result = self.tool.run("")
        assert "summarizer" in result.lower()

    def test_short_text(self):
        result = self.tool.run("Short text here.")
        assert "short" in result.lower()

    def test_long_text(self):
        # Generate text with enough sentences for summarization
        sentences = [
            "Artificial intelligence is transforming industries worldwide.",
            "Machine learning algorithms can process vast amounts of data.",
            "Natural language processing enables computers to understand human speech.",
            "Computer vision allows machines to interpret visual information.",
            "Deep learning has achieved remarkable results in image recognition.",
            "Robotics combines AI with physical systems for automation.",
            "AI ethics is an important field of study and research.",
            "The future of AI holds both promises and challenges for humanity.",
        ]
        text = " ".join(sentences)
        result = self.tool.run(text)
        assert "Summary" in result

    def test_sentences_flag(self):
        sentences = [
            "First important sentence about technology.",
            "Second sentence discusses innovation.",
            "Third sentence covers research findings.",
            "Fourth sentence mentions future plans.",
            "Fifth sentence wraps up the discussion nicely.",
        ]
        text = " ".join(sentences)
        result = self.tool.run(f"--sentences 2 {text}")
        assert "2 key sentences" in result


class TestTimerTool:
    def setup_method(self):
        self.tool = TimerTool()
        _timers.clear()

    def test_name(self):
        assert self.tool.name == "timer"

    def test_set_timer(self):
        result = self.tool.run("5")
        assert "Timer set" in result
        assert "5" in result

    def test_check_empty(self):
        result = self.tool.run("check")
        assert "No active" in result

    def test_set_and_check(self):
        self.tool.run("10")
        result = self.tool.run("check")
        assert "remaining" in result.lower() or "Active" in result

    def test_clear(self):
        self.tool.run("5")
        result = self.tool.run("clear")
        assert "cleared" in result.lower()
        result = self.tool.run("check")
        assert "No active" in result

    def test_invalid_input(self):
        result = self.tool.run("abc")
        assert "not a valid" in result.lower()

    def test_empty_input(self):
        result = self.tool.run("")
        assert "timer" in result.lower()

    def test_negative_number(self):
        result = self.tool.run("-5")
        assert "positive" in result.lower()

    def test_fractional_minutes(self):
        result = self.tool.run("0.5")
        assert "Timer set" in result
        assert "30 seconds" in result
