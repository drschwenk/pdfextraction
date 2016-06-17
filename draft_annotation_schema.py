page_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",
    "additionalProperties": False,
    "properties": {
        "text": {
            "type": "object",
            "additionalProperties": False,
            "patternProperties": {
                "^T[0-9]+$": {
                    "type": "object",
                    "required": ["rectangle", "category", "box_id", "source", "score", "contents"],
                    "additionalProperties": False,
                    "properties": {
                        "box_id": {
                            "type": "string"
                        },
                        "category": {
                                "enum": ["header/topic", "definition", "discussion", "question", "answer",
                                         "figure_label", "unlabeled"]
                            },
                        "contents": {
                            "type": "string"
                        },
                        "score": {
                        },
                        "rectangle": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 2,
                            "items": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "integer",
                                },
                            },
                        },
                        "source": {
                            "type": "object",
                            "items": {
                                "$schema": "http://json-schema.org/draft-04/schema#",
                                "title": "C Object",

                                "type": "object",
                                "required": ["book_source", "page_n"],

                                "properties": {
                                    "book_source": {
                                        "type": "string"
                                    },
                                    "page_n": {
                                        "type": "int"
                                    }
                                },
                                "additionalProperties": False
                            }
                        }
                    }
                }
            }
        },
        "multiple choice":
            {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^Q[0-9]+$": {
                        "type": "object",
                        "required": ["rectangle", "box_id", "source", "question posed"],
                        "additionalProperties": False,
                        "properties": {
                            "box_id": {
                                "type": "string"
                            },
                            "question_id": {
                                "type": "string"
                            },
                            "question posed": {
                                "type": "string"
                            },
                            "answer choices": {
                                "patternProperties": {
                                    "^AC[0-9]+$": {
                                        "type": "object",
                                        "items": {
                                            "$schema": "http://json-schema.org/draft-04/schema#",
                                            "title": "C Object",

                                            "type": "object",
                                            "required": ["identifier", "text"],
                                            "properties": {
                                                "text": {
                                                    "type": "string"
                                                },
                                                "choice number": {
                                                    "type": "int"
                                                }
                                            },
                                            "additionalProperties": False
                                        }
                                    }
                                }
                            },
                            "correct answer": {
                            },
                            "rectangle": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {
                                        "type": "integer",
                                    },
                                },
                            },
                            "source": {
                                "type": "object",
                                "items": {
                                    "$schema": "http://json-schema.org/draft-04/schema#",
                                    "title": "C Object",

                                    "type": "object",
                                    "required": ["book_source", "page_n"],

                                    "properties": {
                                        "book_source": {
                                            "type": "string"
                                        },
                                        "page_n": {
                                            "type": "int"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                }
            },
        "short answer":
            {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^Q[0-9]+$": {
                        "type": "object",
                        "required": ["rectangle", "box_id", "source", "question posed"],
                        "additionalProperties": False,
                        "properties": {
                            "box_id": {
                                "type": "string"
                            },
                            "question_id": {
                                "type": "string"
                            },
                            "question posed": {
                                "type": "string"
                            },
                            "correct answer": {
                            },
                            "rectangle": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {
                                        "type": "integer",
                                    },
                                },
                            },
                            "source": {
                                "type": "object",
                                "items": {
                                    "$schema": "http://json-schema.org/draft-04/schema#",
                                    "title": "C Object",

                                    "type": "object",
                                    "required": ["book_source", "page_n"],

                                    "properties": {
                                        "book_source": {
                                            "type": "string"
                                        },
                                        "page_n": {
                                            "type": "int"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                }
            },
        "true/false":
            {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^Q[0-9]+$": {
                        "type": "object",
                        "required": ["rectangle", "box_id", "source", "question posed"],
                        "additionalProperties": False,
                        "properties": {
                            "box_id": {
                                "type": "string"
                            },
                            "question_id": {
                                "type": "string"
                            },
                            "question posed": {
                                "type": "string"
                            },
                            "correct answer": {
                            },
                            "rectangle": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {
                                        "type": "integer",
                                    },
                                },
                            },
                            "source": {
                                "type": "object",
                                "items": {
                                    "$schema": "http://json-schema.org/draft-04/schema#",
                                    "title": "C Object",

                                    "type": "object",
                                    "required": ["book_source", "page_n"],

                                    "properties": {
                                        "book_source": {
                                            "type": "string"
                                        },
                                        "page_n": {
                                            "type": "int"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                }
            },
        "fill in the blank":
            {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^Q[0-9]+$": {
                        "type": "object",
                        "required": ["rectangle", "box_id", "source", "question posed"],
                        "additionalProperties": False,
                        "properties": {
                            "box_id": {
                                "type": "string"
                            },
                            "question_id": {
                                "type": "string"
                            },
                            "question posed": {
                                "type": "string"
                            },
                            "answer choices": {
                                "patternProperties": {
                                    "^AC[0-9]+$": {
                                        "type": "object",
                                        "items": {
                                            "$schema": "http://json-schema.org/draft-04/schema#",
                                            "title": "C Object",

                                            "type": "object",
                                            "required": ["text"],
                                            "properties": {
                                                "text": {
                                                    "type": "string"
                                                },
                                            },
                                            "additionalProperties": False
                                        }
                                    }
                                }
                            },
                            "correct answer": {
                            },
                            "rectangle": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {
                                        "type": "integer",
                                    },
                                },
                            },
                            "source": {
                                "type": "object",
                                "items": {
                                    "$schema": "http://json-schema.org/draft-04/schema#",
                                    "title": "C Object",

                                    "type": "object",
                                    "required": ["book_source", "page_n"],

                                    "properties": {
                                        "book_source": {
                                            "type": "string"
                                        },
                                        "page_n": {
                                            "type": "int"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        }
                    }
                }
            },
        "figures": {
            "type": "object",
        },
        "relationships": {
            "type": "object",
        }
    },
    "required properties": ["text", "figure", "relationship"]
}

