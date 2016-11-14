ck12_schema = {
    "$schema": "http://json-schema.org/draft-04/schema",
    "title": "Textbook Dataset",
    "type": "array",
    "items": {
        "title": "lesson",
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "required": ["topics", "globalID", "lessonName", "instructionalDiagrams", "questions", "metaLessonID"],
            "topics": {
                "type": "object",
                "additionalProperties": False,
                "patternProperties": {
                    "^(:?\w*\s?\w*)\.?[\s\w*\s]?[\w\s]+(U\.S\.)?$": {
                        "type": "object",
                        "required": ["content", "globalID", "topicName"],
                        "additionalProperties": False,
                        "properties": {
                            "globalID": {
                                "type": "string"
                            },
                            "topicName": {
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
                                        "additionalProperties": False,
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
                        "required": ["imageName", "imagePath", "rawText", "processedText", "globalID"],
                        "additionalProperties": False,
                        "properties": {
                            "imageName": {
                                "type": "string"
                            },
                            "imagePath": {
                                "type": "string"
                            },
                            "globalID": {
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
                            "^NDQ_[0-9]+$": {
                                "type": "object",
                                "required": ["beingAsked", "correctAnswer", "globalID", "answerChoices", "questionType",
                                             "questionSubType"],
                                "additionalProperties": False,
                                "properties": {
                                    "globalID": {
                                        "type": "string",
                                        "pattern": "^NDQ_[0-9]+$"
                                    },
                                    "idStructural": {
                                        "type": ["string", "null"],
                                        "pattern": "^[0-9]+(?:\.|\))\s?$"
                                    },
                                    "questionType": {
                                        "enum": ["Multiple Choice", "Direct Answer"]
                                    },
                                    "questionSubType": {
                                        "enum": ["True or False", "Multiple Choice", "Matching",
                                                 "Fill in the Blank", "Short Answer"]
                                    },
                                    "beingAsked": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "required": ["rawText", "processedText"],
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
                                        "required": ["processedText", "rawText"],
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
                                    "allOf": [
                                        {"questionSubType": {"enum": ["Multiple Choice"]},
                                         "answerChoices": {"minProperties": 3, "maxProperties": 4}},
                                        {"questionSubType": {"enum": ["True or False"]},
                                         "answerChoices": {"minProperties": 2, "maxProperties": 2}},
                                        {"questionSubType": {"enum": ["Matching"]},
                                         "answerChoices":{"minProperties": 5, "maxProperties": 7}},
                                        {"questionSubType": {"enum": ["Fill in the Blank", "Short Answer"]},
                                         "answerChoices":{"minProperties": 0, "maxProperties": 0}}
                                    ],
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
                        "patternProperties": {
                            "^DQ_[0-9]+$": {
                                "type": "object",
                                "required": ["beingAsked", "correctAnswer", "globalID", "imagePath", "answerChoices", "imageName"],
                                "additionalProperties": False,
                                "properties": {
                                    "globalID": {
                                        "type": "string",
                                        "pattern": "^DQ_[0-9]+$"
                                    },
                                    "imagePath": {
                                        "type": "string",
                                    },
                                    "idStructural": {
                                        "type": ["string", "null"],
                                        "pattern": "^[0-9]+(?:\.|\))\s?$"
                                    },
                                    "questionType": {
                                        "enum": ["Diagram Multiple Choice"]
                                    },
                                    "beingAsked": {
                                        "type": "object",
                                        "additionalProperties": False,
                                        "properties": {
                                            "rawText": {
                                                "type": "string",
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
                                        "minProperties": 4,
                                        "maxProperties": 4,
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
                                    },
                                    "imageName": {
                                        "type": "string"
                                    },
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
            },
            "lessonName": {
                "type": "string"
            },
            "globalID": {
                "type": "string",
                "pattern": "^L_[0-9]+$"
            },
            "metaLessonID": {
                "type": "string"
            },
            "adjunctTopics": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "Vocabulary": {
                        "type": "object",
                        "additionalProperties": True,
                    },
                },
                "patternProperties": {
                    "^(?!Vocabulary).*": {
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
            }
        }
    }
}

