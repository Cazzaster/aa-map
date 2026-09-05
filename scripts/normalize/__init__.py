from . import meeting_guide_json, bmlt

PARSERS = {
    "meeting_guide_json": meeting_guide_json.parse,
    "tsml": meeting_guide_json.parse,  # TSML's wp-json feed is spec-compliant
    "bmlt": bmlt.parse,
}
