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

embedding_model = Word2Vec(token_ch, size=100, window = 2)
embedding_model.save("asdf")