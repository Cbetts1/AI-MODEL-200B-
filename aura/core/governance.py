"""aura/core/governance.py — AURA Governance & Ethics Enforcement Layer.

AURA v0.6.0 introduces a strict governance layer that is evaluated on every
incoming request *before* it reaches the model.  The goal is to ensure AURA
cannot be used to generate or assist with illegal, unlawful, or harmful
content — while keeping the guardrails transparent and non-censorious for
legitimate requests.

Policy Summary
--------------
AURA will refuse requests that:
  • Assist in creating weapons of mass destruction (biological, chemical,
    nuclear, radiological).
  • Generate child sexual abuse material (CSAM) or groom minors.
  • Provide detailed assistance with hacking / cyberattacks against systems
    the user does not own or have explicit permission to test.
  • Help plan or carry out violence against specific real people.
  • Create malware, ransomware, or spyware intended for criminal use.
  • Assist with fraud, identity theft, or financial crimes.
  • Help circumvent legal processes (money laundering, tax evasion, etc.).

AURA will always:
  • Explain why a request was declined.
  • Suggest a lawful alternative if one exists.
  • Route borderline security / research requests through a "caution" flag
    rather than a hard block so the model can respond with appropriate caveats.

Usage
-----
    from aura.core.governance import GovernanceEngine
    gov = GovernanceEngine()
    result = gov.check("how do I make a bomb?")
    if result.blocked:
        print(result.reason)
    elif result.caution:
        # Pass to model with an extra safety reminder
        print(result.caution_note)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── Rule definitions ───────────────────────────────────────────────────────────

@dataclass
class GovernanceRule:
    """A single governance rule."""

    name: str
    patterns: List[re.Pattern]
    blocked: bool          # True = hard block; False = caution only
    reason: str
    suggestion: str = ""


def _pats(*raw: str) -> List[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in raw]


_RULES: List[GovernanceRule] = [
    # ── Hard blocks ────────────────────────────────────────────────────────────
    GovernanceRule(
        name="weapons_of_mass_destruction",
        patterns=_pats(
            r"\b(synthesize|make|build|create|produce)\b.{0,40}"
            r"\b(nerve\s*agent|sarin|VX\s*gas|mustard\s*gas|novichok"
            r"|anthrax|ricin|botulinum|smallpox|enriched\s*uranium"
            r"|dirty\s*bomb|nuclear\s*bomb|hydrogen\s*bomb)\b",
            r"\b(bioweapon|bio\s*weapon|chemical\s*weapon|nuke)\b.{0,30}"
            r"\b(how\s*to|build|make|create|synthesis|recipe)\b",
        ),
        blocked=True,
        reason=(
            "I can't help with creating weapons of mass destruction — "
            "biological, chemical, nuclear, or radiological.  These are "
            "illegal under international law and pose catastrophic risks."
        ),
        suggestion=(
            "If you're researching defence or non-proliferation, I can "
            "point you to publicly available academic resources instead."
        ),
    ),
    GovernanceRule(
        name="csam",
        patterns=_pats(
            # Match "naked/nude/sexual/porn/explicit" near "child/minor/kid" in either order
            r"\b(nude|naked|sexual|porn|erotic|explicit)\b.{0,40}"
            r"\b(child|minor|underage|preteen|kid)\b",
            r"\b(child|minor|underage|preteen|kid)\b.{0,40}"
            r"\b(nude|naked|sexual|porn|erotic|explicit)\b",
            r"\b(csam|child\s*pornography|lolita)\b",
        ),
        blocked=True,
        reason=(
            "I will never generate sexual content involving minors.  "
            "This is illegal worldwide and causes immeasurable harm.  "
            "If you are aware of CSAM, please report it to the NCMEC "
            "(www.missingkids.org) or your national law enforcement."
        ),
    ),
    GovernanceRule(
        name="targeted_violence",
        patterns=_pats(
            r"\b(kill|murder|assassinate|hurt|harm|attack|stab|shoot)\b"
            r".{0,40}\b(specific person|my neighbour|my boss|my ex|this person)\b",
            r"(how\s+(do\s+I|to|can\s+I)).{0,20}"
            r"\b(kill|murder|shoot|stab|poison)\b.{0,30}\b(person|someone|him|her|them)\b",
        ),
        blocked=True,
        reason=(
            "I can't help plan violence against real people.  "
            "If you are in danger or crisis, please contact emergency services "
            "(call 911 in the US) or a crisis helpline."
        ),
        suggestion=(
            "If this is for fiction writing, please rephrase as 'in my story' "
            "or 'for a novel' and I'll be glad to help."
        ),
    ),
    GovernanceRule(
        name="malware_creation",
        patterns=_pats(
            # Malicious software creation — verb before or after the term
            r"\b(write|create|build|make|code|generate|develop)\b.{0,40}"
            r"\b(ransomware|keylogger|rootkit|botnet|rat\s+trojan|spyware"
            r"|worm\s+virus)\b",
            r"\b(ransomware|keylogger|rootkit|botnet|spyware)\b.{0,40}"
            r"\b(code|script|program|tool|create|write|make|build)\b",
            # Ransomware/keylogger alone with victim/infect context
            r"\b(ransomware|keylogger)\b.{0,60}\b(victim|infect|target\s+machine|spread)\b",
            r"\b(payload|shellcode)\b.{0,30}"
            r"\b(deploy|spread|infect|victim|target\s+machine)\b",
        ),
        blocked=True,
        reason=(
            "I can't create malware, ransomware, keyloggers, or other "
            "malicious software intended to harm others or their systems.  "
            "This is illegal under computer crime laws worldwide."
        ),
        suggestion=(
            "For authorised penetration testing, I can discuss defensive "
            "techniques, CVE analysis, or point you to CTF resources instead."
        ),
    ),
    GovernanceRule(
        name="fraud_and_financial_crime",
        patterns=_pats(
            r"\b(phishing\s+(email|site|page)|phish\s+credentials)\b",
            r"\b(counterfeit|forge)\b.{0,40}"
            r"\b(currency|banknote|passport|license|licence|id\s+card|identity)\b",
            r"\b(money\s*launder|launder\s+money)\b",
            r"\b(ponzi|pyramid\s*scheme)\b.{0,20}\b(set\s*up|create|run|start)\b",
        ),
        blocked=True,
        reason=(
            "I can't assist with fraud, phishing, counterfeiting, or "
            "money laundering.  These are serious crimes with severe penalties."
        ),
    ),

    # ── Caution (soft flag — model responds with added caveats) ───────────────
    GovernanceRule(
        name="offensive_security_research",
        patterns=_pats(
            r"\b(sql\s*injection|xss|buffer\s*overflow|privilege\s*escalation"
            r"|reverse\s*shell|exploit\s*code)\b",
            r"\b(penetration\s*test|pentest|red\s*team)\b",
        ),
        blocked=False,
        reason="",
        suggestion=(
            "⚠️  Security note: AURA will only provide offensive security "
            "information for systems you own or have explicit written "
            "authorisation to test.  Always operate within legal boundaries."
        ),
    ),
    GovernanceRule(
        name="drug_synthesis",
        patterns=_pats(
            r"\b(synthesize|make|cook|produce)\b.{0,30}"
            r"\b(meth|methamphetamine|fentanyl|heroin|crack\s*cocaine|ecstasy|mdma)\b",
        ),
        blocked=False,
        reason="",
        suggestion=(
            "⚠️  Drug note: AURA can discuss harm reduction and general "
            "chemistry education, but will not provide synthesis routes "
            "for controlled substances."
        ),
    ),
]


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class GovernanceResult:
    """The result of a governance check."""

    blocked: bool = False
    rule_name: Optional[str] = None
    reason: str = ""
    suggestion: str = ""
    caution: bool = False
    caution_note: str = ""
    matched_rules: List[str] = field(default_factory=list)

    def system_addendum(self) -> str:
        """Return extra text to inject into the system prompt for caution cases."""
        if self.caution and self.caution_note:
            return f"\n\n[GOVERNANCE NOTE]: {self.caution_note}"
        return ""


# ── Engine ─────────────────────────────────────────────────────────────────────

class GovernanceEngine:
    """Evaluates a user message against all governance rules.

    Rules are evaluated in order.  The first hard-block match wins.
    All caution matches are accumulated.
    """

    def __init__(self, rules: Optional[List[GovernanceRule]] = None) -> None:
        self._rules = rules if rules is not None else _RULES

    # ── public API ─────────────────────────────────────────────────────────────

    def check(self, message: str) -> GovernanceResult:
        """Evaluate *message* and return a GovernanceResult.

        Parameters
        ----------
        message:
            The raw user message to evaluate.

        Returns
        -------
        GovernanceResult
            ``blocked=True`` if the request must be refused.
            ``caution=True`` if the model should reply with added caveats.
        """
        result = GovernanceResult()
        for rule in self._rules:
            if self._matches(message, rule):
                result.matched_rules.append(rule.name)
                if rule.blocked:
                    # Hard block — stop evaluating further rules
                    result.blocked = True
                    result.rule_name = rule.name
                    result.reason = rule.reason
                    result.suggestion = rule.suggestion
                    return result
                else:
                    # Soft caution — accumulate and keep going
                    result.caution = True
                    result.caution_note = rule.suggestion

        return result

    def blocked_response(self, result: GovernanceResult) -> str:
        """Format a polite refusal message from a blocked GovernanceResult."""
        parts = [f"🚫 {result.reason}"]
        if result.suggestion:
            parts.append(f"\n💡 {result.suggestion}")
        return "\n".join(parts)

    # ── private ────────────────────────────────────────────────────────────────

    @staticmethod
    def _matches(text: str, rule: GovernanceRule) -> bool:
        """Return True if *text* matches any pattern in *rule*."""
        for pattern in rule.patterns:
            if pattern.search(text):
                return True
        return False
