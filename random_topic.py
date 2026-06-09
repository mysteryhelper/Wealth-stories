"""
Wealth Stories — Daily topic selector
Rags to riches, finance emotional, Indian success stories
"""
import random

TOPICS = [
    # Rags to riches
    "A poor boy from a village who became a millionaire with just ₹100",
    "A tea seller's son who built a ₹50 crore business",
    "A farmer's daughter who became India's youngest CEO",
    "A rickshaw puller who sent his son to IIT",
    "A street vendor who turned his cart into a restaurant chain",
    "A daily wage worker who retired with ₹1 crore savings",

    # Struggle and sacrifice
    "A mother who sold her gold bangles to fund her son's startup",
    "A man who lost everything at 40 and rebuilt his life from zero",
    "A village girl who walked 10km to school and became a doctor",
    "A blind man who built a successful business using only his voice",

    # Smart money decisions
    "The ₹500 investment that changed a poor family's life forever",
    "How a servant became richer than his employer in 10 years",
    "The auto driver who invested in land and became a crorepati",
    "A woman who saved ₹50 every day for 20 years — her result will shock you",

    # Betrayal and comeback
    "He was cheated by his business partner — his comeback story is unbelievable",
    "She lost her job at 45 and started over — what happened next changed her family",
    "They laughed at his idea — 5 years later he proved them all wrong",

    # Emotional family stories
    "A father who worked three jobs so his children never felt poor",
    "The last letter a dying father wrote to his son about money and life",
    "She promised her mother she would buy her a house — the journey took 12 years",
]

print(random.choice(TOPICS))
