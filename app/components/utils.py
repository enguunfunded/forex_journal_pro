from datetime import time

def infer_session(dt):
    t = dt.time()
    if t >= time(0,0) and t < time(8,0):
        return "Asia"
    elif t >= time(8,0) and t < time(16,0):
        return "London"
    else:
        return "NewYork"

def mtf_alignment_score(h4,h1,m15):
    score = 0
    if h4 == h1 and h4 in ("UP","DOWN"): score+=1
    if h4 == m15 and h4 in ("UP","DOWN"): score+=1
    if h1 == m15 and h1 in ("UP","DOWN"): score+=1
    return score
