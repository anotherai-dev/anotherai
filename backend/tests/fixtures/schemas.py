SIMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "hello": {"type": "string"},
    },
}

STREAMLINED_FILE_SCHEMA = {
    "properties": {
        "content_type": {
            "description": "The content type of the file",
            "examples": [
                "image/png",
                "image/jpeg",
                "audio/wav",
                "application/pdf",
            ],
            "type": "string",
        },
        "data": {
            "description": "The base64 encoded data of the file",
            "type": "string",
        },
        "url": {
            "description": "The URL of the image",
            "type": "string",
        },
    },
    "type": "object",
}

FILE_SCHEMA = {"properties": {"hello": {"$ref": "#/$defs/File"}}}
FILE_SCHEMA_EXPECTED = {
    "$defs": {"File": STREAMLINED_FILE_SCHEMA},
    "properties": {"hello": {"$ref": "#/$defs/File"}},
    "type": "object",
}

STREAMLINED_CHAT_MESSAGE_SCHEMA = {
    "properties": {
        "content": {
            "description": "The content of the message",
            "examples": [
                "Thank you for your help!",
                "What is the weather forecast for tomorrow?",
            ],
            "type": "string",
        },
        "role": {
            "description": "The role of the message sender",
            "enum": [
                "USER",
                "ASSISTANT",
            ],
            "type": "string",
        },
    },
    "required": [
        "content",
        "role",
    ],
    "type": "object",
}


CHAT_MESSAGE_SCHEMA = {"properties": {"hello": {"$ref": "#/$defs/ChatMessage"}}}
CHAT_MESSAGE_SCHEMA_EXPECTED = {
    "type": "object",
    "$defs": {"ChatMessage": STREAMLINED_CHAT_MESSAGE_SCHEMA},
    "properties": {"hello": {"$ref": "#/$defs/ChatMessage"}},
}


ANY_OF = {
    "type": "object",
    "properties": {
        "new_task_schema": {
            "properties": {
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the person",
                            "examples": ["John", "Emma"],
                        },
                        "middle_name": {
                            "type": "string",
                            "description": "The middle name of the person (optional)",
                            "examples": ["Lee", "Marie"],
                        },
                        "last_name": {
                            "anyOf": [{"type": "string"}, {"type": "null"}],
                            "description": "The last name of the person (can be null)",
                            "examples": ["Smith", "Johnson", None],
                        },
                    },
                },
                "output_json_schema": {
                    "type": "object",
                    "properties": {
                        "likely_gender": {
                            "type": "string",
                            "enum": ["FEMALE", "MALE", "UNKNOWN"],
                            "description": "The likely gender based on the provided name",
                            "examples": ["FEMALE", "MALE"],
                        },
                    },
                },
            },
        },
    },
}

ANY_OF_CLEANED = {
    "type": "object",
    "properties": {
        "new_task_schema": {
            "type": "object",
            "properties": {
                "input_json_schema": {
                    "type": "object",
                    "properties": {
                        "first_name": {
                            "type": "string",
                            "description": "The first name of the person",
                            "examples": ["John", "Emma"],
                        },
                        "middle_name": {
                            "type": "string",
                            "description": "The middle name of the person (optional)",
                            "examples": ["Lee", "Marie"],
                        },
                        "last_name": {
                            "type": "string",
                            "description": "The last name of the person (can be null)",
                            "examples": ["Smith", "Johnson", None],
                        },
                    },
                },
                "output_json_schema": {
                    "type": "object",
                    "properties": {
                        "likely_gender": {
                            "type": "string",
                            "enum": ["FEMALE", "MALE", "UNKNOWN"],
                            "description": "The likely gender based on the provided name",
                            "examples": ["FEMALE", "MALE"],
                        },
                    },
                },
            },
        },
    },
}

ANY_OF_2 = {
    "$defs": {
        "Currency": {
            "enum": [
                "USD",
                "EUR",
                "JPY",
                "GBP",
                "AUD",
                "CAD",
                "CHF",
                "CNY",
                "SEK",
                "NZD",
                "MXN",
                "SGD",
                "HKD",
                "NOK",
                "KRW",
                "TRY",
                "INR",
                "RUB",
                "BRL",
                "ZAR",
                "DKK",
                "PLN",
                "THB",
                "IDR",
                "MYR",
            ],
            "title": "Currency",
            "type": "string",
        },
        "Price": {
            "properties": {
                "amount": {
                    "description": "The amount of the price.",
                    "title": "Amount",
                    "type": "number",
                    "examples": [
                        250000.0,
                    ],
                },
                "currency": {
                    "allOf": [{"$ref": "#/$defs/Currency"}],
                    "description": "The currency of the price.",
                    "examples": ["USD", "EUR"],
                },
            },
            "required": ["amount", "currency"],
            "title": "Price",
            "type": "object",
        },
        "RealEstateListing": {
            "properties": {
                "description": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "The description of the real estate listing",
                    "examples": ["A beautiful 3-bedroom house with a spacious garden."],
                    "title": "Description",
                },
                "address": {
                    "anyOf": [{"type": "string"}, {"type": "null"}],
                    "description": "The address of the real estate listing",
                    "examples": ["123 Main St, Springfield, IL"],
                    "title": "Address",
                },
                "price": {
                    "anyOf": [{"$ref": "#/$defs/Price"}, {"type": "null"}],
                    "description": "The price details of the real estate listing",
                },
                "surface_area": {
                    "anyOf": [{"$ref": "#/$defs/SurfaceArea"}, {"type": "null"}],
                    "description": "The surface area of the real estate listing in square feet",
                },
                "bedrooms_count": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "description": "The number of bedrooms in the real estate listing",
                    "examples": [3],
                    "title": "Bedrooms Count",
                },
                "bathrooms_count": {
                    "anyOf": [{"type": "integer"}, {"type": "null"}],
                    "description": "The number of bathrooms in the real estate listing",
                    "examples": [2],
                    "title": "Bathrooms Count",
                },
            },
            "required": ["description", "address", "price", "surface_area", "bedrooms_count", "bathrooms_count"],
            "title": "RealEstateListing",
            "type": "object",
        },
        "SurfaceArea": {
            "properties": {
                "value": {
                    "description": "The value of the surface area.",
                    "examples": ["1506.7"],
                    "title": "Value",
                    "type": "number",
                },
                "unit": {
                    "allOf": [{"$ref": "#/$defs/Unit"}],
                    "description": "The unit of the surface area.",
                    "examples": ["SQFT", "SQM"],
                },
            },
            "required": ["value", "unit"],
            "title": "SurfaceArea",
            "type": "object",
        },
        "Unit": {"enum": ["SQFT", "SQM"], "title": "Unit", "type": "string"},
    },
    "properties": {
        "listing": {
            "$ref": "#/$defs/RealEstateListing",
            "default": None,
            "description": "The extracted real estate listing, if any",
        },
    },
    "title": "ExtractRealEstateListingDetailsTaskOutput",
    "type": "object",
}


ANY_OF_2_CLEANED = {
    "properties": {
        "listing": {
            "default": None,
            "description": "The extracted real estate listing, if any",
            "properties": {
                "address": {
                    "type": ["string", "null"],
                    "description": "The address of the real estate listing",
                    "examples": [
                        "123 Main St, Springfield, IL",
                    ],
                    "title": "Address",
                },
                "bathrooms_count": {
                    "type": ["integer", "null"],
                    "description": "The number of bathrooms in the real estate listing",
                    "examples": [
                        2,
                    ],
                    "title": "Bathrooms Count",
                },
                "bedrooms_count": {
                    "type": ["integer", "null"],
                    "description": "The number of bedrooms in the real estate listing",
                    "examples": [
                        3,
                    ],
                    "title": "Bedrooms Count",
                },
                "description": {
                    "type": ["string", "null"],
                    "description": "The description of the real estate listing",
                    "examples": [
                        "A beautiful 3-bedroom house with a spacious garden.",
                    ],
                    "title": "Description",
                },
                "price": {
                    "properties": {
                        "amount": {
                            "description": "The amount of the price.",
                            "examples": [
                                250000.0,
                            ],
                            "title": "Amount",
                            "type": "number",
                        },
                        "currency": {
                            "description": "The currency of the price.",
                            "enum": [
                                "USD",
                                "EUR",
                                "JPY",
                                "GBP",
                                "AUD",
                                "CAD",
                                "CHF",
                                "CNY",
                                "SEK",
                                "NZD",
                                "MXN",
                                "SGD",
                                "HKD",
                                "NOK",
                                "KRW",
                                "TRY",
                                "INR",
                                "RUB",
                                "BRL",
                                "ZAR",
                                "DKK",
                                "PLN",
                                "THB",
                                "IDR",
                                "MYR",
                            ],
                            "examples": [
                                "USD",
                                "EUR",
                            ],
                            "title": "Currency",
                            "type": "string",
                        },
                    },
                    "required": [
                        "amount",
                        "currency",
                    ],
                    "title": "Price",
                    "type": ["object", "null"],
                    "description": "The price details of the real estate listing",
                },
                "surface_area": {
                    "properties": {
                        "unit": {
                            "description": "The unit of the surface area.",
                            "enum": [
                                "SQFT",
                                "SQM",
                            ],
                            "examples": [
                                "SQFT",
                                "SQM",
                            ],
                            "title": "Unit",
                            "type": "string",
                        },
                        "value": {
                            "description": "The value of the surface area.",
                            "examples": [
                                "1506.7",
                            ],
                            "title": "Value",
                            "type": "number",
                        },
                    },
                    "required": [
                        "unit",
                        "value",
                    ],
                    "title": "SurfaceArea",
                    "type": ["object", "null"],
                    "description": "The surface area of the real estate listing in square feet",
                },
            },
            "required": [
                "address",
                "bathrooms_count",
                "bedrooms_count",
                "description",
                "price",
                "surface_area",
            ],
            "title": "RealEstateListing",
            "type": "object",
        },
    },
    "title": "ExtractRealEstateListingDetailsTaskOutput",
    "type": "object",
}


ONE_OF = {
    "type": "object",
    "properties": {
        "result_array": {
            "type": "array",
            "description": "desc",
            "items": {"oneOf": [{"type": "number"}, {"type": "null"}]},
            "minItems": 3,
            "maxItems": 3,
        },
    },
}

ONE_OF_CLEANED = {
    "type": "object",
    "properties": {
        "result_array": {
            "type": "array",
            "description": "desc",
            "items": {"type": ["number", "null"]},
            "minItems": 3,
            "maxItems": 3,
        },
    },
}

ALL_OF = {
    "$defs": {"Category": {"enum": ["POSITIVE", "NEUTRAL", "NEGATIVE", "OTHER"], "type": "string"}},
    "properties": {
        "categories": {
            "description": "An array of sentiment categories for the input text",
            "items": {"$ref": "#/$defs/Category"},
            "type": "array",
            "minItems": 1,
        },
        "primary_category": {
            "allOf": [{"$ref": "#/$defs/Category"}],
            "description": "The primary or dominant sentiment category of the input text",
            "examples": ["POSITIVE", "NEUTRAL", "NEGATIVE"],
        },
    },
    "type": "object",
}

ALL_OF_CLEANED = {
    "properties": {
        "categories": {
            "description": "An array of sentiment categories for the input text",
            "items": {"enum": ["POSITIVE", "NEUTRAL", "NEGATIVE", "OTHER"], "type": "string"},
            "type": "array",
            "minItems": 1,
        },
        "primary_category": {
            "enum": ["POSITIVE", "NEUTRAL", "NEGATIVE", "OTHER"],
            "type": "string",
            "description": "The primary or dominant sentiment category of the input text",
            "examples": ["POSITIVE", "NEUTRAL", "NEGATIVE"],
        },
    },
    "type": "object",
}

TYPE_ARRAY = {
    "type": "object",
    "properties": {
        "result": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
            },
            "description": "desc",
        },
    },
}

TYPE_ARRAY_CLEANED = {
    "type": "object",
    "properties": {
        "result": {
            "type": "array",
            "items": {"type": ["string", "null"]},
            "description": "desc",
        },
    },
}


SCHEMA_WITH_EMPTY_DEFS = {
    "type": "object",
    "properties": {
        "text": {
            "description": "The original text to be summarized",
            "examples": [
                "This is a long text that needs to be summarized in French.",
            ],
            "type": "string",
        },
    },
    "$defs": {},
}

SCHEMA_WITH_EMPTY_DEFS_CLEANED = {
    "type": "object",
    "properties": {
        "text": {
            "description": "The original text to be summarized",
            "examples": [
                "This is a long text that needs to be summarized in French.",
            ],
            "type": "string",
        },
    },
}


SCHEMA_WITH_REQUIRED_AS_FIELD_NAME = {
    "type": "object",
    "properties": {
        "required": {
            "type": "string",
            "description": "The required field",
        },
    },
    "required": ["required"],
}

SCHEMA_WITH_REQUIRED_AS_FIELD_NAME_CLEANED = {
    "type": "object",
    "properties": {
        "required": {
            "type": "string",
            "description": "The required field",
        },
    },
    "required": ["required"],
}
