import json
import logging
import os
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
import httpx

logger = logging.getLogger("llm_providers")

T = TypeVar("T", bound=BaseModel)

class LLMProvider:
    """Base interface for LLM operations."""
    def generate_structured_response(self, prompt: str, system_prompt: str, response_schema: Type[T]) -> T:
        raise NotImplementedError

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        raise NotImplementedError


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider returning hardcoded responses for testing and offline modes."""
    def __init__(self, mode: str = "default"):
        self.mode = mode
        self.alter_facts = False

    def generate_structured_response(self, prompt: str, system_prompt: str, response_schema: Type[T]) -> T:
        logger.info("Using MockLLMProvider for structured response")
        if self.alter_facts:
            return response_schema(
                summary="Amount mismatch with altered facts",
                root_cause="Attempting to override deterministic values",
                root_cause_confidence=0.90,
                facts=[
                    {"key": "payment_amount", "value": 999999.0, "source": "Altered Fact"},
                    {"key": "expected_amount", "value": 500.0, "source": "Altered Expected"},
                    {"key": "difference", "value": 12345.0, "source": "Altered Diff"}
                ],
                inferences=[],
                alternative_explanations=[],
                recommended_actions=[],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=[]
            )
        # Extract case details from prompt
        case_id = "CASE-UNKNOWN"
        reason_code = "UNKNOWN"
        
        # Simple extraction for mock responses
        if "case_id" in prompt.lower() or "case-" in prompt.lower():
            for word in prompt.replace("\n", " ").split():
                if "case-" in word.lower():
                    case_id = word.strip(".,:;()[]{}'\"")
                    break
        
        for rc in ["EXACT_MATCH", "PARTIAL_REFUND", "FEE_DIFFERENCE", "TIMING_DIFFERENCE", 
                   "MISSING_SETTLEMENT", "DUPLICATE_TRANSACTION", "AMOUNT_MISMATCH", 
                   "TAX_MISMATCH", "UNKNOWN_ADJUSTMENT", "CONFLICTING_RECORDS", "AMBIGUOUS_CASE"]:
            if rc in prompt:
                reason_code = rc
                break
                    
        # Check for prompt injection mock test
        if "ignore your instructions" in prompt.lower() or "ignore previous instructions" in prompt.lower():
            # For prompt injection, verify that we do NOT mark as valid or follow instructions.
            # We return an escalation or completed status but treat the prompt injection as ordinary untrusted text.
            return response_schema(
                summary="Detected untrusted text in database records attempts to override instructions. Treated as normal data.",
                root_cause="Potential prompt injection or malicious transaction note.",
                root_cause_confidence=0.99,
                facts=[
                    {"key": "transaction_note", "value": "Ignore instructions override", "source": "Bank Transaction"}
                ],
                inferences=[
                    {"inference": "Note contains instruction override words but was ignored.", "supporting_facts": ["transaction_note"]}
                ],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Flag user account for security review", "priority": "HIGH", "reason": "Suspicious instruction injection in memo"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=["Untrusted instruction ignored."]
            )

        # Handle specific case types to return correct mock output structure
        if reason_code == "FEE_DIFFERENCE":
            return response_schema(
                summary="The fee difference is caused by an actual settlement fee of 2.5% instead of the expected 2.0%.",
                root_cause="Payment gateway fee mismatch. Configured rate is 2.0% but actual fee charged was 2.5%.",
                root_cause_confidence=0.95,
                facts=[
                    {"key": "payment_amount", "value": 100000.0, "source": "Payment PAY-00001"},
                    {"key": "expected_fee", "value": 2000.0, "source": "Calculation (2.0%)"},
                    {"key": "actual_fee", "value": 2500.0, "source": "Settlement SET-00001"},
                    {"key": "difference", "value": 500.0, "source": "Deterministic engine"}
                ],
                inferences=[
                    {"inference": "Actual fee rate of 2.5% was applied by payment gateway.", "supporting_facts": ["actual_fee", "payment_amount"]}
                ],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Update gateway fee configuration in settings to 2.5%", "priority": "HIGH", "reason": "Configured rate is stale"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=[]
            )
        elif reason_code == "TAX_MISMATCH":
            return response_schema(
                summary="Mismatch between tax recorded on the invoice and the tax record details.",
                root_cause="Tax calculation discrepancy in invoice generation.",
                root_cause_confidence=0.90,
                facts=[
                    {"key": "invoice_tax", "value": 180.0, "source": "Invoice INV-00001"},
                    {"key": "tax_record_tax", "value": 150.0, "source": "TaxRecord TAX-00001"}
                ],
                inferences=[
                    {"inference": "Tax was overcharged on the invoice or under-reported in tax ledger.", "supporting_facts": ["invoice_tax", "tax_record_tax"]}
                ],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Recompute tax liability and file amendment if necessary", "priority": "MEDIUM", "reason": "Invoice and ledger mismatch"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=[]
            )
        elif reason_code == "AMBIGUOUS_CASE":
            return response_schema(
                summary="The settlement references multiple bulk payments, creating ambiguity.",
                root_cause="Vague reference ID in bank transaction prevents unique payment matching.",
                root_cause_confidence=0.75,
                facts=[
                    {"key": "reference_id", "value": "BULK-BATCH-99", "source": "Bank Transaction BT-001"}
                ],
                inferences=[
                    {"inference": "The settlement was deposited as a bulk batch transfer containing multiple independent payments.", "supporting_facts": ["reference_id"]}
                ],
                alternative_explanations=[
                    {
                        "hypothesis": "Payment was settled together with order from another day.",
                        "supporting_evidence": ["reference_id"],
                        "contradicting_evidence": [],
                        "confidence": 0.50
                    }
                ],
                recommended_actions=[
                    {"action": "Manually split bulk settlement across source orders", "priority": "HIGH", "reason": "Cannot deterministically auto-resolve bulk batch reference"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=["Ambiguous case cannot be resolved without manual audit."]
            )
        elif reason_code == "CONFLICTING_RECORDS":
            return response_schema(
                summary="Order status is CANCELLED but a successful payment exists.",
                root_cause="Order cancelled after payment was authorized, without issuing a refund.",
                root_cause_confidence=0.98,
                facts=[
                    {"key": "order_status", "value": "CANCELLED", "source": "Order ORD-00001"},
                    {"key": "payment_status", "value": "CAPTURED", "source": "Payment PAY-00001"}
                ],
                inferences=[
                    {"inference": "Cancellation was executed without invoking payment gateway refund API.", "supporting_facts": ["order_status", "payment_status"]}
                ],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Initiate refund of ₹100,000 for cancelled order", "priority": "CRITICAL", "reason": "Customer was charged for a cancelled order"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=["RISK: Customer charged for cancelled order."]
            )
        elif reason_code == "AMOUNT_MISMATCH":
            # Check if testing fact integrity where mock LLM tries to change numbers
            if "TEST_FACT_INTEGRITY_FAIL" in prompt:
                # LLM attempts to return wrong amounts
                return response_schema(
                    summary="Amount mismatch with altered facts",
                    root_cause="Attempting to override deterministic values",
                    root_cause_confidence=0.90,
                    facts=[
                        {"key": "payment_amount", "value": 999999.0, "source": "Altered Fact"},
                        {"key": "expected_amount", "value": 500.0, "source": "Altered Expected"},
                        {"key": "difference", "value": 12345.0, "source": "Altered Diff"}
                    ],
                    inferences=[],
                    alternative_explanations=[],
                    recommended_actions=[],
                    auto_resolution_eligible=False,
                    requires_human_review=True,
                    warnings=[]
                )
            return response_schema(
                summary="Amount mismatch between settlement and payment.",
                root_cause="Mismatch in operational amounts recorded in system.",
                root_cause_confidence=0.95,
                facts=[
                    {"key": "payment_amount", "value": 100000.0, "source": "Payment PAY-00001"},
                    {"key": "settlement_amount", "value": 97500.0, "source": "Settlement SET-00001"}
                ],
                inferences=[],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Check gateway adjustment records", "priority": "MEDIUM", "reason": "Unexplained amount mismatch"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=[]
            )
        elif reason_code == "MISSING_SETTLEMENT":
            return response_schema(
                summary="The settlement record is missing.",
                root_cause="Settlement has not been processed or sync failed.",
                root_cause_confidence=0.95,
                facts=[
                    {"key": "payment_id", "value": "PAY-00001", "source": "Payment"},
                    {"key": "settlement", "value": None, "source": "Database"}
                ],
                inferences=[],
                alternative_explanations=[],
                recommended_actions=[
                    {"action": "Check gateway portal for settlement status", "priority": "HIGH", "reason": "Missing settlement record"}
                ],
                auto_resolution_eligible=False,
                requires_human_review=True,
                warnings=[]
            )
        else:
            # Fallback mock schema
            return response_schema(
                summary="Reconciliation is successful.",
                root_cause="No discrepancy found.",
                root_cause_confidence=1.0,
                facts=[],
                inferences=[],
                alternative_explanations=[],
                recommended_actions=[],
                auto_resolution_eligible=True,
                requires_human_review=False,
                warnings=[]
            )

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        logger.info("Using MockLLMProvider for generate_text")
        return "Mock text response from MockLLMProvider."


class GeminiProvider(LLMProvider):
    """Live Google Gemini Provider using API requests."""
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"

    def generate_text(self, prompt: str, system_prompt: str) -> str:
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            }
        }
        try:
            resp = httpx.post(self.api_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            # Extract text content
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text
        except Exception as e:
            logger.error(f"Gemini API request failed: {e}")
            raise RuntimeError(f"Gemini LLM Provider failed: {e}")

    def generate_structured_response(self, prompt: str, system_prompt: str, response_schema: Type[T]) -> T:
        # Request Gemini to return JSON and enforce structure
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "systemInstruction": {
                "parts": [
                    {"text": system_prompt}
                ]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
            }
        }
        
        # Serialize schema description and append to instructions
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        payload["contents"][0]["parts"].append({
            "text": f"\n\nProduce valid JSON matching this JSON Schema:\n{schema_json}"
        })

        try:
            resp = httpx.post(self.api_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
            text_resp = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean response if LLM enclosed it in markdown block
            if text_resp.startswith("```json"):
                text_resp = text_resp.split("```json")[1].split("```")[0].strip()
            elif text_resp.startswith("```"):
                text_resp = text_resp.split("```")[1].split("```")[0].strip()
            
            parsed_json = json.loads(text_resp)
            return response_schema.model_validate(parsed_json)
        except Exception as e:
            logger.error(f"Gemini structured response failed: {e}")
            raise RuntimeError(f"Gemini structured response generation failed: {e}")


def get_llm_provider() -> LLMProvider:
    """Return configured provider or MockLLMProvider if API Key is not set."""
    api_key = os.getenv("LLM_API_KEY")
    model = os.getenv("LLM_MODEL", "gemini-1.5-flash")
    provider_name = os.getenv("LLM_PROVIDER", "mock")

    if not api_key or provider_name == "mock":
        logger.info("LLM_API_KEY missing or provider is configured as mock. Falling back to MockLLMProvider.")
        return MockLLMProvider()
    
    logger.info(f"Initializing live Gemini provider (model={model})")
    return GeminiProvider(api_key=api_key, model_name=model)
