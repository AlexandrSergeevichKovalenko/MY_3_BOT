VALID_CATEGORIES = [
    'Nouns', 'Cases', 'Verbs', 'Tenses', 'Adjectives', 'Adverbs', 
    'Conjunctions', 'Prepositions', 'Moods', 'Word Order', 'Other mistake'
]

VALID_SUBCATEGORIES = {
    'Nouns': ['Gendered Articles', 'Pluralization', 'Compound Nouns', 'Declension Errors'],
    'Cases': ['Nominative', 'Accusative', 'Dative', 'Genitive', 'Akkusativ + Preposition', 'Dative + Preposition', 'Genitive + Preposition'],
    'Verbs': ['Placement', 'Conjugation', 'Weak Verbs', 'Strong Verbs', 'Mixed Verbs', 'Separable Verbs', 'Reflexive Verbs', 'Auxiliary Verbs', 'Modal Verbs', 'Verb Placement in Subordinate Clause'],
    'Tenses': ['Present', 'Past', 'Simple Past', 'Present Perfect', 'Past Perfect', 'Future', 'Future 1', 'Future 2', 'Plusquamperfekt Passive', 'Futur 1 Passive', 'Futur 2 Passive'],
    'Adjectives': ['Endings', 'Weak Declension', 'Strong Declension', 'Mixed Declension', 'Placement', 'Comparative', 'Superlative', 'Incorrect Adjective Case Agreement'],
    'Adverbs': ['Placement', 'Multiple Adverbs', 'Incorrect Adverb Usage'],
    'Conjunctions': ['Coordinating', 'Subordinating', 'Incorrect Use of Conjunctions'],
    'Prepositions': ['Accusative', 'Dative', 'Genitive', 'Two-way', 'Incorrect Preposition Usage'],
    'Moods': ['Indicative', 'Declarative', 'Interrogative', 'Imperative', 'Subjunctive 1', 'Subjunctive 2'],
    'Word Order': ['Standard', 'Inverted', 'Verb-Second Rule', 'Position of Negation', 'Incorrect Order in Subordinate Clause', 'Incorrect Order with Modal Verb'],
    'Other mistake': ['Unclassified mistake']
}

VALID_CATEGORIES_lower = [cat.lower() for cat in VALID_CATEGORIES]
VALID_SUBCATEGORIES_lower = {k.lower(): [v.lower() for v in values] for k, values in VALID_SUBCATEGORIES.items()}