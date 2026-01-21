RISK_KEYWORDS = {

    # 🔴 Violence & Physical Harm
    "violence": [
        "kill", "killing", "murder", "murdered", "attack", "attacked",
        "assault", "stab", "stabbing", "shoot", "shooting",
        "bomb", "explosion", "explode", "terror", "terrorist",
        "gun", "knife", "weapon", "fight", "fighting",
        "beat", "beating", "strangle", "choke", "burn",
        "dead", "death", "execute", "execution"
    ],

    # 🔴 Fraud & Financial Crime
    "fraud": [
        "scam", "scammer", "fraud", "fraudulent", "hack", "hacked",
        "phish", "phishing", "spoof", "spoofing", "identity theft",
        "fake", "forgery", "impersonate", "impersonation",
        "credit card fraud", "stolen card", "money laundering",
        "ponzi", "pyramid scheme", "crypto scam",
        "investment scam", "loan scam", "refund scam",
        "account takeover", "otp scam"
    ],

    # 🔴 Abuse, Harassment & Hate
    "abuse": [
        "idiot", "stupid", "dumb", "moron", "loser",
        "hate", "hateful", "trash", "garbage",
        "shut up", "get lost", "go die",
        "worthless", "pathetic", "disgusting",
        "racist", "sexist", "bigot",
        "slur", "insult", "harass", "harassment",
        "bully", "bullying"
    ],

    # 🔴 Sexual & Explicit Content
    "sexual": [
        "sex", "sexual", "porn", "pornography", "nude", "naked",
        "explicit", "adult content", "xxx", "fetish",
        "escort", "prostitute", "hooker",
        "rape", "molest", "sexual assault",
        "child abuse", "minor sexual"
    ],

    # 🔴 Drugs & Illegal Substances
    "drugs": [
        "drug", "drugs", "cocaine", "heroin", "meth",
        "weed", "marijuana", "ganja", "hash",
        "lsd", "ecstasy", "mdma",
        "overdose", "inject", "dealer", "drug dealer",
        "illegal substance", "narcotics"
    ],

    # 🔴 Extremism & Radicalization
    "extremism": [
        "terrorism", "terrorist", "extremist",
        "radicalize", "radicalization",
        "isis", "al qaeda", "taliban",
        "jihad", "holy war",
        "white supremacy", "neo nazi",
        "hate group", "militant"
    ],

    # 🔴 Self-Harm & Suicide
    "self_harm": [
        "suicide", "kill myself", "self harm",
        "cut myself", "cutting",
        "end my life", "want to die",
        "no reason to live",
        "jump off", "hang myself",
        "overdose myself"
    ],

    # 🔴 Cybercrime & Hacking
    "cybercrime": [
        "ddos", "malware", "ransomware",
        "virus", "trojan", "spyware",
        "keylogger", "backdoor",
        "brute force", "sql injection",
        "zero day", "exploit",
        "payload", "botnet"
    ],

    # 🔴 Weapons & Illegal Tools
    "weapons": [
        "gun", "firearm", "rifle", "pistol",
        "ammunition", "ammo",
        "grenade", "missile",
        "explosive", "bomb",
        "knife", "dagger", "blade",
        "silencer", "automatic weapon"
    ],

    # 🔴 Threats & Intimidation
    "threats": [
        "i will kill you", "you will die",
        "i will hurt you",
        "watch your back",
        "you are dead",
        "i am coming for you",
        "threaten", "threatening",
        "extort", "blackmail",
        "ransom"
    ]
}

def analyze_text(text: str):
    try:
        if not isinstance(text, str):
            return error_response("INVALID_TYPE", "Input must be a string")

        text = text.strip().lower()

        if len(text) == 0:
            return error_response("EMPTY_INPUT", "Text is empty")

        if len(text) > 5000:
            text = text[:5000]
            truncated = True
        else:
            truncated = False

        reasons = []
        score = 0.0

        for category, words in RISK_KEYWORDS.items():
            for word in words:
                if word in text:
                    score += 0.2
                    reasons.append(f"Detected {category} keyword: {word}")

        score = min(score, 1.0)

        if score < 0.3:
            risk = "LOW"
        elif score < 0.7:
            risk = "MEDIUM"
        else:
            risk = "HIGH"

        if truncated:
            reasons.append("Input text was truncated")

        return {
            "risk_score": round(score, 2),
            "risk_category": risk,
            "trigger_reasons": reasons,
            "processed_length": len(text),
            "errors": None
        }

    except Exception as e:
        return error_response("INTERNAL_ERROR", str(e))
def error_response(code, message):
    return {
        "risk_score": 0.0,
        "risk_category": "LOW",
        "trigger_reasons": [],
        "processed_length": 0,
        "errors": {
            "error_code": code,
            "message": message
        }
    }
