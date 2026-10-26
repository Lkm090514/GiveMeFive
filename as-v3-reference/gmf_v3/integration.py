"""Ports only: AS V2 supplies canonical registry and its one Learning Ledger."""
from typing import Protocol
from .contracts import Contract, ExternalLink


class CanonicalRegistry(Protocol):
    def validate(self,link:ExternalLink) -> bool: ...


class LedgerPort(Protocol):
    def append_once(self,event_id:str,payload:dict) -> None: ...


def confirmed_link(link:ExternalLink,registry:CanonicalRegistry) -> ExternalLink:
    if not registry.validate(link): raise ValueError("unknown or conflicting canonical GMF IDs")
    return link.model_copy(update={"confirmed":True})


def emit_learning_evidence(ledger:LedgerPort,*,session_id:str,attempt_id:str,question_version_id:str,kind:str,payload:dict):
    if kind not in {"exam","correction","practice","mf_repair"}: raise ValueError("invalid evidence kind")
    if not all([session_id,attempt_id,question_version_id]): raise ValueError("stable identities required")
    # This module has no ledger table or sink. Existing GMF must implement append_once.
    import hashlib,json
    identity=json.dumps([session_id,attempt_id,question_version_id,kind],separators=(",",":"))
    event_id="asv3:"+hashlib.sha256(identity.encode()).hexdigest()
    ledger.append_once(event_id,{**payload,"session_id":session_id,"attempt_id":attempt_id,
        "question_version_id":question_version_id,"kind":kind})
    return event_id

