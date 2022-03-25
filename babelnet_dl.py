from nis import cat
import re
import requests
from random import choice
import json

get_wn_path = 'https://babelnet.io/v6/getSynsetIdsFromResourceID?id=wn:{}&wnVersion=WN_30&source=WN&key=44eb9536-43f3-4c74-8c28-186ccec84448'
get_ko_path = 'https://babelnet.io/v6/getSynset?id={}&key=44eb9536-43f3-4c74-8c28-186ccec84448&targetLang=KO'
wn_offsets = [ i.split('\t')[0] for i in open('ko-en_multi-wordnet.tsv').readlines() if (i.split('\t')[2] != '_NONE_') ]
chosen = []
en_data = []
ko_data = []

for i in range(200):
  offset = None
  while True:
    offset = choice(wn_offsets)
    if offset not in chosen:
      chosen.append(offset)
      break
  
  print(i, offset)
  try:
    e_res = requests.get(get_wn_path.format(offset)).json()
    if len(e_res) == 0:
      en_data.append(None)
      ko_data.append(None)
      continue
    for i in range(len(e_res)):
      e_res[i]['__wn'] = offset

    bn_offset = e_res[0]['id']
    k_res = requests.get(get_ko_path.format(bn_offset)).json()
    if len(k_res) == 0 or len(k_res['senses']) == 0:
      ko_data.append(None)
      en_data.append(None)
      continue
    k_res['__wn'] = offset

    en_data.append(e_res)
    ko_data.append(k_res)
  except Exception as e:
    # print('Ignoring:', e)
    # pass
    raise e

json.dump(en_data, open('en.json', 'w'), ensure_ascii=False, indent=2)
json.dump(ko_data, open('ko.json', 'w'), ensure_ascii=False, indent=2)
  