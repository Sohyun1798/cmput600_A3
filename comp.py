import json

en = json.load(open('en.json', 'r'))
ko = json.load(open('ko.json', 'r'))
wn_offset_to_words = { i.split('\t')[0]: i.split('\t')[2].split(',')  for i in open('ko-en_multi-wordnet.tsv').readlines() }

assert len(en) == len(ko)

total = len(en)
populated = len([1 for i in en if i is not None])
assert total != populated
correct = 0
tp, tn, fp, fn = (None,) * 4

for idx, (e, k) in enumerate(zip(en, ko)):
  if e is None:
    continue
  for e_ in e:
    offset = k['__wn']
    words = wn_offset_to_words[offset]
    for k_ in k['senses']:
      prop = k_['properties']
      if prop['fullLemma'] in words or prop['simpleLemma'] == words or prop['lemma']['lemma'] == words:
        correct += 1

print(correct / populated)
