"""Lexical families, structural patterns, and classification rules for Pass 1.

Candidate CATEGORIES describe what kind of evidence a span *might* be.
Document CLASSES describe what a document discusses. Neither is a graph fact.
"""
from __future__ import annotations

import re

I = re.IGNORECASE

# ---------------------------------------------------------------- candidates
# category -> list of (pattern_name, compiled_regex)
CANDIDATE_PATTERNS = {
    "OWNERSHIP_EXPLICIT": [
        ("beneficial_owner", re.compile(r"\bbeneficial(?:ly)?[- ]own(?:er(?:s|ship)?|ed|s)\b", I)),
        ("owned_by", re.compile(r"\bowned\s+(?:and\s+(?:operated|controlled)\s+)?by\b", I)),
        ("owns_stake", re.compile(r"\bowns?\b[^.\n]{0,60}\b(?:percent|%|shares?|interests?|stakes?|equity)\b", I)),
        ("pct_ownership", re.compile(
            r"\b\d{1,3}(?:\.\d+)?\s?(?:%|percent)\s+"
            r"(?:(?:of\s+)?(?:the\s+)?(?:issued\s+|outstanding\s+|voting\s+|total\s+)*"
            r"(?:shares?|stock|equity|membership\s+interests?|ownership|interests?\s+in|"
            r"units|common\s+stock|voting\s+power)"
            r"|owner(?:ship)?|stake|shareholder)\b", I)),
        ("ownership_interest", re.compile(r"\b(?:ownership|equity|controlling|membership)\s+interests?\b", I)),
        ("sole_majority_owner", re.compile(r"\b(?:sole|majority|minority|principal|part|co-)\s*owner(?:s|ship)?\b", I)),
        ("shareholder_of", re.compile(r"\b(?:sole\s+)?(?:shareholder|stockholder|member)\s+of\b", I)),
        ("owner_of", re.compile(r"\bowners?\s+of\b[^.\n]{0,80}\b(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Company|Ltd\.?|LP\b|LLP\b)", I)),
    ],
    "CONTROL_EXPLICIT": [
        ("controlled_by", re.compile(r"\bcontrolled\s+by\b", I)),
        ("under_control", re.compile(r"\bunder\s+the\s+control\s+of\b", I)),
        ("exercises_control", re.compile(r"\bexercis\w+\s+(?:substantial\s+|significant\s+)?control\b", I)),
        ("substantial_control", re.compile(r"\bsubstantial\s+control\b", I)),
        ("controlling_person", re.compile(r"\bcontrolling\s+(?:person|party|shareholder|stockholder|member|entity)s?\b", I)),
        ("controls_entity", re.compile(r"\bcontrols?\b[^.\n]{0,60}\b(?:LLC|L\.L\.C\.|Inc\.?|Corp(?:oration)?\.?|Company|Ltd\.?|entit(?:y|ies)|compan(?:y|ies))\b", I)),
    ],
    "PARENT_SUBSIDIARY": [
        ("wholly_owned_sub", re.compile(r"\bwholly[- ]owned\s+subsidiar(?:y|ies)\b", I)),
        ("subsidiary_of", re.compile(r"\bsubsidiar(?:y|ies)\s+of\b", I)),
        ("subsidiary", re.compile(r"\bsubsidiar(?:y|ies)\b", I)),
        ("parent_co", re.compile(r"\bparent\s+(?:company|corporation|entity|organization|bank|holding)\b", I)),
        ("holding_co", re.compile(r"\bholding\s+compan(?:y|ies)\b", I)),
        ("affiliate", re.compile(r"\baffiliat(?:e[sd]?|ion)\b[^.\n]{0,60}\b(?:of|with)\b", I)),
        ("dba_fka", re.compile(r"\b(?:d/b/a|f/k/a|a/k/a|doing\s+business\s+as|formerly\s+known\s+as|also\s+known\s+as)\b", I)),
    ],
    "SHELL_NOMINEE": [
        ("shell", re.compile(r"\bshell\s+(?:compan(?:y|ies)|corporation|corp|entit(?:y|ies)|firm)s?\b", I)),
        ("front_co", re.compile(r"\bfront\s+(?:compan(?:y|ies)|business(?:es)?|entit(?:y|ies))\b", I)),
        ("nominee", re.compile(r"\bnominee(?:s|\s+(?:owner|director|shareholder|officer|account))?\b", I)),
        ("straw", re.compile(r"\bstraw\s+(?:owner|man|men|purchaser|buyer|borrower|donor)s?\b", I)),
        ("spv", re.compile(r"\bspecial\s+purpose\s+(?:vehicle|entit(?:y|ies))\b|\bSPV\b")),
        ("shelf_co", re.compile(r"\bshelf\s+compan(?:y|ies)\b", I)),
        ("alter_ego", re.compile(r"\balter\s+ego\b", I)),
        ("intermediary_layer", re.compile(r"\b(?:layering|layered\s+(?:through|entities)|intermediar(?:y|ies))\b", I)),
    ],
    "ROLE_TITLE": [
        ("registered_agent", re.compile(r"\bregistered\s+agents?\b", I)),
        ("managing_member", re.compile(r"\b(?:managing|sole)\s+members?\b", I)),
        ("organizer", re.compile(r"\b(?:organizer|incorporator)s?\b", I)),
        ("officer_of", re.compile(r"\b(?:president|chief\s+executive\s+officer|CEO|chief\s+financial\s+officer|CFO|secretary|treasurer|director|principal|founder|chairman|chairwoman|managing\s+director|general\s+partner)\b[^.\n]{0,40}\bof\b[^.\n]{0,80}\b(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Company|Ltd\.?|Bank|Group|Holdings?)\b", I)),
        ("member_manager_llc", re.compile(r"\b(?:member|manager)s?\b[^.\n]{0,50}\b(?:LLC|L\.L\.C\.|limited\s+liability)\b", I)),
        ("trustee_settlor", re.compile(r"\b(?:trustee|settlor|grantor)s?\b", I)),
        ("signatory", re.compile(r"\b(?:authorized\s+)?signat(?:ory|ories|ures?\s+authority)\b|\bauthorized\s+signer\b", I)),
        ("on_behalf", re.compile(r"\bon\s+behalf\s+of\b", I)),
    ],
    "FINANCIAL_FLOW": [
        ("wire_transfer", re.compile(r"\bwire\s+transfers?\b|\bwired\b", I)),
        ("transferred_amt", re.compile(r"\btransferr?(?:ed|ing)?\b[^.\n]{0,60}\$\s?[\d,]+", I)),
        ("dollar_flow", re.compile(r"\$\s?[\d,]{4,}(?:\.\d{2})?[^.\n]{0,60}\b(?:to|from|into|through)\b", I)),
        ("bank_account", re.compile(r"\bbank\s+accounts?\b|\baccount\s+(?:number|ending|held)\b", I)),
        ("proceeds", re.compile(r"\b(?:criminal\s+|illicit\s+|fraud\s+)?proceeds\b[^.\n]{0,60}\b(?:transferred|laundered|deposited|wired|funneled|diverted)\b", I)),
        ("funnel", re.compile(r"\bfunnel(?:ed|ing)?\s+(?:account|money|funds)s?\b", I)),
        ("payment_to", re.compile(r"\bpayments?\s+(?:to|from)\b[^.\n]{0,80}\b(?:LLC|Inc\.?|Corp\.?|account|bank)\b", I)),
        ("beneficiary_recipient", re.compile(r"\b(?:beneficiary|recipient|payee|remitter|originator)\b[^.\n]{0,50}\b(?:of|account|wire|transfer|payment)\b", I)),
    ],
    "SAR_BSA": [
        ("sar", re.compile(r"\bsuspicious\s+activity\s+reports?\b|\bSARs?\b")),
        ("bsa", re.compile(r"\bbank\s+secrecy\s+act\b|\bBSA\b")),
        ("aml", re.compile(r"\banti[- ]money[- ]launder\w+\b|\bAML\b")),
        ("ctr", re.compile(r"\bcurrency\s+transaction\s+reports?\b|\bCTRs?\b")),
        ("money_laundering", re.compile(r"\bmoney\s+launder\w+\b|\blaunder(?:ed|ing)\b", I)),
        ("structuring", re.compile(r"\bstructur(?:ed|ing)\s+(?:cash\s+)?(?:deposits?|transactions?|withdrawals?)\b", I)),
        ("gto", re.compile(r"\bgeographic\s+targeting\s+orders?\b", I)),
        ("314", re.compile(r"\b314\s?\(\s?[ab]\s?\)", I)),
    ],
    "BOI_CTA": [
        ("boi", re.compile(r"\bbeneficial\s+ownership\s+information\b|\bBOI\b")),
        ("cta", re.compile(r"\bcorporate\s+transparency\s+act\b", I)),
        ("boss", re.compile(r"\bbeneficial\s+ownership\s+secure\s+system\b|\bBOSS\b")),
        ("boi_rule", re.compile(r"\b(?:BOI|beneficial\s+ownership)\s+(?:report(?:s|ing)?|rule|requirements?|database|registry)\b", I)),
        ("reporting_company", re.compile(r"\breporting\s+compan(?:y|ies)\b", I)),
        ("company_applicant", re.compile(r"\bcompany\s+applicants?\b", I)),
        ("fincen_id", re.compile(r"\bFinCEN\s+identifiers?\b", I)),
        ("cta_cite", re.compile(r"\b31\s+U\.?S\.?C\.?\s+(?:§+\s*)?5336\b|\b1010\.380\b", I)),
        ("access_rule", re.compile(r"\bbeneficial\s+ownership[^.\n]{0,40}\baccess\b|\baccess\s+rule\b", I)),
    ],
    "FORMATION_DISSOLUTION": [
        ("formation_docs", re.compile(r"\b(?:articles\s+of\s+(?:incorporation|organization)|certificate\s+of\s+(?:formation|incorporation|organization))\b", I)),
        ("incorporated_in", re.compile(r"\b(?:incorporated|organized|formed|registered|chartered)\s+(?:in|under|on)\b", I)),
        ("dissolution", re.compile(r"\bdissolv(?:ed|ution)\b|\bwound\s+up\b|\bwinding\s+up\b", I)),
        ("merger", re.compile(r"\bmerg(?:er|ed|ing)\b[^.\n]{0,60}\b(?:with|into|of)\b", I)),
        ("acquired", re.compile(r"\bacquir(?:ed|es|ing|isition)\b[^.\n]{0,60}\b(?:of|by|from)\b", I)),
    ],
}

# Structural patterns — capture groups preserved verbatim in the candidate
# record (matched_groups). Never resolved to identities in this pass.
STRUCTURAL_PATTERNS = [
    ("person_role_entity", re.compile(
        r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s*,?\s+"
        r"(?:the\s+|a\s+|its\s+|former\s+)?"
        r"(president|chief executive officer|CEO|chief financial officer|CFO|"
        r"owner|co-owner|manager|managing member|sole member|member|director|"
        r"officer|principal|founder|chairman|secretary|treasurer|registered agent|"
        r"organizer|incorporator|trustee|beneficial owner)\s+"
        r"(?:and\s+\w+\s+)?of\s+"
        r"([A-Z][\w&.,'’\- ]{2,60}?(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|"
        r"Company|Co\.|Ltd\.?|LP|LLP|Group|Holdings?|Bank|Trust))")),
    ("entity_owned_by", re.compile(
        r"\b([A-Z][\w&.,'’\- ]{2,60}?(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|"
        r"Company|Co\.|Ltd\.?|LP|LLP|Group|Holdings?|Bank|Trust))\s*,?\s+"
        r"(?:which\s+)?(?:is|was)?\s*"
        r"(?:owned|controlled|owned\s+and\s+controlled|beneficially\s+owned)\s+"
        r"(?:in\s+part\s+)?by\s+"
        r"([A-Z][\w&.,'’\- ]{2,60})")),
    ("entity_subsidiary_of", re.compile(
        r"\b([A-Z][\w&.,'’\- ]{2,60}?)\s*,?\s+"
        r"(?:is\s+|was\s+)?an?\s+(?:wholly[- ]owned\s+|indirect\s+|direct\s+)?"
        r"subsidiary\s+of\s+([A-Z][\w&.,'’\- ]{2,60})")),
    ("pct_of_entity", re.compile(
        r"\b(\d{1,3}(?:\.\d+)?)\s?(?:%|percent)\s+of\s+(?:the\s+)?"
        r"(?:issued\s+|outstanding\s+|voting\s+|total\s+)*"
        r"(?:membership\s+interests?|equity|shares?|stock|ownership|units)\s+"
        r"(?:of|in)\s+"
        r"([A-Z][\w&.,'’\- ]{2,60})")),
]

# ------------------------------------------------------------- doc classes
# class -> regex that, if found anywhere in searchable text, tags the doc.
CLASS_PATTERNS = {
    "BOI_CTA": re.compile(r"\bbeneficial\s+ownership\s+information\b|\bcorporate\s+transparency\s+act\b|\b31\s+U\.?S\.?C\.?\s+(?:§+\s*)?5336\b|\b1010\.380\b|\bFinCEN\s+identifier\b", I),
    "BOSS": re.compile(r"\bbeneficial\s+ownership\s+secure\s+system\b|\bBOSS\b"),
    "BENEFICIAL_OWNERSHIP": re.compile(r"\bbeneficial(?:ly)?[- ]own", I),
    "CORPORATE_OWNERSHIP": re.compile(r"\bowned\s+by\b|\bownership\s+interest\b|\bequity\s+interest\b|\bcontrolling\s+interest\b|\bshareholder\b|\bstockholder\b", I),
    "SUBSTANTIAL_CONTROL": re.compile(r"\bsubstantial\s+control\b|\bcontrolled\s+by\b|\bunder\s+the\s+control\s+of\b", I),
    "PARENT_SUBSIDIARY": re.compile(r"\bsubsidiar(?:y|ies)\b|\bparent\s+(?:company|corporation|holding)\b|\bholding\s+compan", I),
    "SHELL_COMPANY": re.compile(r"\bshell\s+(?:compan|corporation|entit)|\bfront\s+compan|\bshelf\s+compan", I),
    "ENTITY_FORMATION": re.compile(r"\barticles\s+of\s+(?:incorporation|organization)\b|\bcertificate\s+of\s+formation\b|\bcompany\s+formation\b|\bformation\s+agent", I),
    "ENTITY_DISSOLUTION": re.compile(r"\bdissolution\b|\bdissolved\b|\badministratively\s+dissolved\b", I),
    "MERGER_ACQUISITION": re.compile(r"\bmergers?\s+and\s+acquisitions?\b|\bmerger\s+agreement\b|\bacquisition\s+of\b|\bmerged\s+(?:with|into)\b", I),
    "OFFICER_DIRECTOR": re.compile(r"\b(?:officers?\s+and\s+directors?|board\s+of\s+directors|chief\s+executive\s+officer|president\s+of)\b", I),
    "MEMBER_MANAGER": re.compile(r"\bmanaging\s+member\b|\bsole\s+member\b|\bmember[- ]managed\b|\bmanager[- ]managed\b", I),
    "REGISTERED_AGENT": re.compile(r"\bregistered\s+agents?\b", I),
    "TRUST_NOMINEE": re.compile(r"\bnominee\b|\btrustee\b|\bsettlor\b|\bgrantor\s+trust\b", I),
    "FINANCIAL_TRANSACTION": re.compile(r"\bwire\s+transfer|\btransferred\s+\$|\bfunds\s+transfer|\bmonetary\s+transactions?\b", I),
    "WIRE_TRANSFER": re.compile(r"\bwire\s+transfers?\b|\bwired\s+\$", I),
    "BANK_ACCOUNT": re.compile(r"\bbank\s+accounts?\b|\baccount\s+(?:number|ending)\b|\bcorrespondent\s+account", I),
    "BSA_AML": re.compile(r"\bbank\s+secrecy\s+act\b|\banti[- ]money[- ]launder|\bAML\b|\bBSA\b"),
    "SAR_RELATED": re.compile(r"\bsuspicious\s+activity\s+report|\bSARs?\b"),
    "ENFORCEMENT": re.compile(r"\bconsent\s+order\b|\bcease\s+and\s+desist\b|\bcivil\s+money\s+penalt|\benforcement\s+action|\bsettlement\s+agreement\b|\bdeferred\s+prosecution\b|\bplea(?:ded|d)?\s+guilty\b|\bindictment\b|\bconvicted\b|\bsentenced\b", I),
    "INVESTIGATION": re.compile(r"\binvestigat(?:ion|ed|ing|ors)\b|\bprobe\b|\bsubpoena", I),
    "CONGRESSIONAL_EVIDENCE": re.compile(r"\bcommittee\s+on\s+(?:oversight|financial\s+services|banking|judiciary)\b|\bcongressional\s+(?:hearing|testimony|report)\b|\bexhibits?\s+\d+\b|\bhearing\s+before\b|\bwritten\s+testimony\b", I),
    "COURT_RECORD": re.compile(r"\bunited\s+states\s+district\s+court\b|\bplaintiff\b|\bdefendant\b|\bcase\s+no\.\b|\bcivil\s+action\b|\bcriminal\s+complaint\b|\bdocket\b", I),
    "REAL_ESTATE": re.compile(r"\breal\s+(?:estate|property)\b|\bresidential\s+(?:purchase|real)\b|\btitle\s+insurance\b|\ball[- ]cash\s+purchase|\bdeed\b", I),
    "PROCUREMENT": re.compile(r"\bprocurement\b|\bfederal\s+contract(?:or|s)?\b|\bSAM\.gov\b|\bsolicitation\s+number\b", I),
    "SEC_OWNERSHIP": re.compile(r"\bschedule\s+13[dg]\b|\bform\s+[34]\b[^.\n]{0,40}ownership|\bsection\s+16\b|\b10\s?%\s+owner|\bbeneficial\s+ownership\s+report", I),
    "SEC_SUBSIDIARY": re.compile(r"\bexhibit\s+21\b|\bsubsidiaries\s+of\s+the\s+registrant\b", I),
    "UCC": re.compile(r"\bUCC(?:-1|-3)?\s+(?:filing|financing\s+statement)\b|\buniform\s+commercial\s+code\b", I),
    "SANCTIONS": re.compile(r"\bOFAC\b|\bspecially\s+designated\s+nationals?\b|\bsanction(?:s|ed)\b|\bblocked\s+propert", I),
    "LICENSING": re.compile(r"\blicens(?:e[sd]?|ing)\b[^.\n]{0,40}\b(?:money\s+(?:transmitter|services)|MSB|casino|bank)|money\s+services\s+business", I),
}

# Definition/boilerplate downranking cues.
DEFINITIONAL = re.compile(
    r"\b(?:means|is\s+defined\s+as|definition\s+of|for\s+purposes\s+of\s+this|"
    r"the\s+term\s+[\"“'])", I)

AMOUNT = re.compile(r"\$\s?[\d,]{3,}(?:\.\d{2})?|\b(?:million|billion)\b", I)
PCT = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?(?:%|percent)\b", I)
DATE_NEARBY = re.compile(
    r"\b(?:19|20)\d{2}\b|\b(?:January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+\d{1,2}\b", I)
PERSON_NAME = re.compile(r"\b[A-Z][a-z]{2,}\s+(?:[A-Z]\.?\s+)?[A-Z][a-z]{2,}\b")
ENTITY_SUFFIX = re.compile(
    r"\b(?:LLC|L\.L\.C\.|Inc\.?|Corp\.?|Corporation|Ltd\.?|LP|LLP|PLLC|"
    r"Company|Co\.)\b")
