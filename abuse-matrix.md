# Abuse Matrix: Edge Case Validation

The following "weird" inputs are explicitly handled and tested to prevent crashes or infinite loops.

| Category | Input Example | Expected Behavior | Reason |
| :--- | :--- | :--- | :--- |
| **Zalgo Text** | `H҉e҉l҉l҉o҉` | Scored normally (strip/ignore modifiers) | Regex handles basic chars, ignores diacritics depending on normalization. |
| **Emoji Flood** | `😂😂😂` * 5000 | Truncated, 0 Score | Emojis are not risk keywords. |
| **Unicode Control** | `\u202E` (RTL Override) | Processed safely | Python strings handle unicode natively. |
| **Null Bytes** | `\x00` in string | Processed safely | Python handles embedded nulls. |
| **Whitespace Flood** | `   ` * 1000 | Trimmed -> Empty Input Error | Input normalization handles this. |
