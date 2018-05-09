import os
from gensim.models import Word2Vec


f = open("..//data/words.txt","r")
r = f.read()
rr = r.split("\n")
token_ch = []
for i in rr:
    word_token = []
    for j in i:
        word_token.append(j)
    token_ch.append(word_token)

embedding_model = Word2Vec(token_ch, size=300, window = 2, min_count=10, workers=4, sg=1)
embedding_model.save("asdf")