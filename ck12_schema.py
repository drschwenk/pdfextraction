ck12_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",
    "additionalProperties": False,
    "properties": {
        "lessons": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "topics": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {
                            {"type": "integer"}
                        },
                        "content": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "text": {
                                    {"type": "string"}
                                },
                                "figures": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "caption": {
                                            {"type": "string"}
                                        },
                                        "imageUri": {
                                            {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "questions": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "nonDiagramQuestions":{
                            "type": "object",
                            "additionalProperties": False,
                            "patternProperties": {
                                "^Q[0-9]+$": {
                                    "type": "object",
                                    "required": ["beingAsked", "correctAnswer", "id"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "pattern": "^({nonDiagramQuestions})$"
                                        },
                                        "type": {
                                            "enum": ["True or False", "Multiple Choice", "Matching", "Fill in the Blank"]
                                        },
                                        "beingAsked": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "rawText": {
                                                    "type": "string"
                                                },
                                                "normalizedText": {
                                                    "type": "string"
                                                }
                                            }
                                        },
                                        "answerChoices":{
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "idStructural": {
                                                    "type": ["string", "null"],
                                                    "pattern": "^({answerChoices})$"
                                                },
                                                "rawText": {
                                                    "type": ["string", "null"],
                                                },
                                                "normalizedText": {
                                                    "type": ["string", "null"],
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "diagramQuestions": {
                            "type": ["string", "null"],
                            "additionalProperties": False,
                            "properties": {
                                "id":{
                                    "type": ["string", "null"],
                                    "pattern": "^({diagramQuestions})$"
                                },
                                "beingAsked": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "normalizedText": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "answerChoices": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "idStructural": {
                                            "type": "string",
                                            "pattern": "^({answerChoices})$"
                                        },
                                        "normalizedText": {
                                            "type": "string"
                                        }
                                    }
                                },
                                "figure": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "imageUri": {
                                            {"type": "string"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "hidden": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "source": {
                            {"type": "string"}
                        }
                    }
                }
            }
        }
    }
}
