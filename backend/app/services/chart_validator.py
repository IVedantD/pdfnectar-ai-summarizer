import json
import re

class ChartValidator:
    @staticmethod
    def _generate_markdown_table(config: dict) -> str:
        """Fallback mechanism: convert parsed JSON chart back to a Markdown table."""
        try:
            title = config.get("title", "Data Summary")
            data = config.get("data", [])
            if not data or not isinstance(data, list):
                return ""
                
            md = f"**{title}**\n\n"
            md += "| Category | Value |\n"
            md += "| :--- | :--- |\n"
            for item in data:
                name = item.get("name", "Unknown")
                val = item.get("value", 0)
                md += f"| {name} | {val} |\n"
            return md
        except Exception:
            return ""

    @staticmethod
    def validate(ai_response: str, context_str: str, context_has_data: bool = True) -> str:
        """
        Validates any ```recharts JSON blocks in the AI response.
        Applies data availability gating, safe parsing, meaningful name checks, and markdown table fallback.
        """
        # 1. Final Safety Gate: If no numeric data in context, strip any hallucinated blocks
        recharts_pattern = r"```recharts\n(.*?)\n```"
        if not context_has_data:
            print(f"[ChartValidator] No data in context. Stripping block.")
            return re.sub(recharts_pattern, "", ai_response, flags=re.DOTALL).strip()

        # Find the recharts block
        match = re.search(recharts_pattern, ai_response, re.DOTALL)
        
        if not match:
            return ai_response
            
        json_str = match.group(1).strip()
        print(f"[ChartValidator] Found recharts block")
        
        # Remove trailing commas that LangChain LLMs sometimes leave
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*\]", "]", json_str)
        
        config = None
        try:
            config = json.loads(json_str)
            print(f"[ChartValidator] Parsed JSON successfully")
            
            # Safe Data Validation and String -> Float parsing
            if "data" not in config or not isinstance(config["data"], list):
                raise ValueError("Data array missing or invalid format")
                
            valid_data = []
            
            # Meaningful Data Validation: Patterns to REJECT as data point names
            REJECT_NAME_PATTERNS = [
                re.compile(r"^\d{10,}$"),                      # Long numeric IDs
                re.compile(r"^\d{4}-\d{2}-\d{2}.*$"),          # Dates/Timestamps as names
                re.compile(r"^[a-f0-9-]{36}$"),                 # UUIDs
                re.compile(r"^\d{3}[-.\s]\d{3}[-.\s]\d{4}$"),    # Phone numbers
            ]

            for item in config["data"]:
                name = str(item.get("name", ""))
                value = item.get("value")

                if not name or value is None:
                    continue
                
                # Reject if name looks like noise/IDs
                if any(p.match(name) for p in REJECT_NAME_PATTERNS):
                    print(f"[ChartValidator] Rejecting non-meaningful name: {name}")
                    continue

                try:
                    # Parse to float safely
                    val = float(value)
                    if val != val: # Check for NaN
                        raise ValueError("NaN value")
                    item["value"] = val
                    valid_data.append(item)
                except (ValueError, TypeError):
                    print(f"[ChartValidator] Discarding invalid data point: {item}")
                    continue
                    
            config["data"] = valid_data
            
            # Edge Cases
            num_points = len(valid_data)
            if num_points < 2:
                raise ValueError(f"Too few valid data points ({num_points}). Min 2 required.")
                
            all_zero_or_neg = all(item["value"] <= 0 for item in valid_data)
            if all_zero_or_neg:
                raise ValueError("All data values are non-positive")
                
            if num_points > 15:
                raise ValueError(f"Too many data points ({num_points} > 15 limit). Preferring table.")
                
            # Smart Type checking (Pie)
            if config.get("type") == "pie":
                title_lower = config.get("title", "").lower()
                is_prop_title = any(word in title_lower for word in ["%", "percent", "share", "proportion", "breakdown"])
                total = sum([item["value"] for item in valid_data])
                # Pie charts should sum to ~100 or ~1.0
                is_sum_100 = (95 <= total <= 105) or (0.95 <= total <= 1.05)
                if not is_prop_title and not is_sum_100:
                    config["type"] = "bar"
                    
            # Data Sorting (Bar/Pie)
            if config.get("type") in ["bar", "pie"]:
                config["data"] = sorted(config["data"], key=lambda x: x["value"], reverse=True)
            
            # Return cleaned JSON block
            clean_markdown = f"```recharts\n{json.dumps(config, indent=2)}\n```"
            print(f"[ChartValidator] Validation successful. Returning chart.")
            return ai_response.replace(match.group(0), clean_markdown)
            
        except json.JSONDecodeError as e:
            print(f"[ChartValidator] JSON Parsing Failed: {str(e)}\nRaw block:\n{json_str}")
            return ai_response.replace(match.group(0), "").strip()
        except Exception as e:
            print(f"[ChartValidator] Validation Rejected: {str(e)}")
            # Fallback to Markdown Table
            if config:
                md_table = ChartValidator._generate_markdown_table(config)
                if md_table:
                    print(f"[ChartValidator] Fallback to Markdown Table successful.")
                    return ai_response.replace(match.group(0), md_table).strip()
            
            # If all fallbacks fail, scrub the chart entirely
            return ai_response.replace(match.group(0), "").strip()
