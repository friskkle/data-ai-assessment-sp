"""
Defining the cosine similarity function in its own file to separate the logic
and make it easier to read. Using plain mathematics to calculate.
"""

def cosine_similarity(vec1, vec2):
    dot_product = sum(a*b for a,b in zip(vec1, vec2))
    norm_vec1 = sum(a*a for a in vec1) ** 0.5
    norm_vec2 = sum(b*b for b in vec2) ** 0.5
    return dot_product / (norm_vec1 * norm_vec2) if norm_vec1 and norm_vec2 else 0.0