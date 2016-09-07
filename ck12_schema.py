ck12_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",
    "additionalProperties": False,
    "patternProperties": {
        "^[\w]+\.?[\w\s]+$": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "topics": {
                    "type": "object",
                    "additionalProperties": False,
                    "patternProperties": {
                        "^[A-Za-z\s]+$": {
                            "type": "object",
                            "required": ["content", "orderID"],
                            "additionalProperties": False,
                            "properties": {
                                "orderID": {
                                    "type": "string"
                                },
                                "content": {
                                    "type": "object",
                                    "required": ["text", "figures"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "text": {
                                            "type": "string"
                                        },
                                        "figures": {
                                            "type": "array",
                                            "items": {
                                                "properties": {
                                                    "caption": {
                                                        "type": "string"
                                                    },
                                                    "imageUri": {
                                                        "type": "string"
                                                    }
                                                }
                                            }
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
                        "nonDiagramQuestions": {
                            "type": "object",
                            "additionalProperties": False,
                            "patternProperties": {
                                "^q[0-9]+$": {
                                    "type": "object",
                                    "required": ["beingAsked", "correctAnswer", "id"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "pattern": "^q[0-9]+$"
                                        },
                                        "idStructural": {
                                            "type": ["string", "null"],
                                            "pattern": "^[1-9](?:\.|\))\s?$"
                                        },
                                        "type": {
                                            "enum": ["True or False", "Multiple Choice", "Matching",
                                                     "Fill in the Blank"]
                                        },
                                        "beingAsked": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "rawText": {
                                                    "type": "string"
                                                },
                                                "processedText": {
                                                    "type": "string"
                                                }
                                            }
                                        },
                                        "correctAnswer": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "rawText": {
                                                    "type": "string"
                                                },
                                                "processedText": {
                                                    "type": "string"
                                                }
                                            }
                                        },
                                        "answerChoices": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "patternProperties": {
                                                "[a-z]": {
                                                    "type": "object",
                                                    "required": ["idStructural", "rawText", "processedText"],
                                                    "additionalProperties": False,
                                                    "properties": {
                                                        "idStructural": {
                                                            "type": ["string", "null"],
                                                            "pattern": "[a-z][\.|\)]"
                                                        },
                                                        "rawText": {
                                                            "type": ["string", "null"],
                                                        },
                                                        "processedText": {
                                                            "type": ["string", "null"],
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                        }
                        },
                        "diagramQuestions": {
                            "type": ["object"],
                            "additionalProperties": False,
                            "properties": {
                                "id": {
                                    "type": ["string", "null"],
                                    "pattern": "^({diagramQuestions})$"
                                },

                                "beingAsked": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "processedText": {
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

                                    }
                                },
                                "figure": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "imageUri": {
                                            "type": "string"
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
                            "type": "string"
                        }
                    }
                }
            }
        }
    }
}
