ck12_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-04/schema",
    "additionalProperties": False,
    "patternProperties": {
        "^[\w\s]+\.?[\w\s]+": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "topics": {
                    "type": "object",
                    "additionalProperties": False,
                    "patternProperties": {
                        "^(:?\w*\s?\w*)\.?[\s\w*\s]?[\w\s]+(U\.S\.)?$": {
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
                                        },
                                        "mediaLinks": {
                                            "type": "array",
                                            "items": {
                                                "properties": {
                                                    "type": "string"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "instructionalDiagrams": {
                    "type": "object",
                    "additionalProperties": False,
                    "patternProperties": {
                        "^[\w\s]+\.?[\w\s]+": {
                            "type": "object",
                            "required": ["imageName", "imageUri", "rawText", "processedText"],
                            "additionalProperties": False,
                            "properties": {
                                "imageName": {
                                    "type": "string"
                                },
                                "imageUri": {
                                    "type": "string"
                                },
                                "rawText": {
                                    "type": "string"
                                },
                                "processedText": {
                                    "type": "string"
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
                                            "pattern": "^[0-9]+(?:\.|\))\s?$"
                                        },
                                        "type": {
                                            "enum": ["True or False", "Multiple Choice", "Matching",
                                                     "Fill in the Blank", "Short Answer"]
                                        },
                                        "beingAsked": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "rawText": {
                                                    "type": "string"
                                                },
                                                "processedText": {
                                                    "type": "string",
                                                    "minLength": 3
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
                                                    "type": "string",
                                                    "minLength": 1
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
                                                            "minLength": 1
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
                                "imageName": {
                                  "type": "string"
                                },
                                "imageUri": {
                                    "type": "object",
                                    "required": ["imageName", "imageUri", "description", "annotationUri"],
                                    "additionalProperties": False,
                                    "properties": {
                                        "imageName": {
                                            "type": "string"
                                        },
                                        "imageUri": {
                                            "type": "string"
                                        },
                                        "annotationUri": {
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
