import json
import sys
import xml.etree.ElementTree as ET
from nltk.corpus import wordnet as wn, reader
from copy import deepcopy


'''
    python main.py bitext/blind_ko-en.txt alignments/blind_align raganato/en.blind.xml silver-wsd-annotations/en.blind_predictions.txt projections/blindProjection.json ko-en_multi-wordnet.tsv
'''

if len(sys.argv) < 7:
    print('Invalid command-line arguments')
    exit(1)

dat_path = sys.argv[1]
align_path = sys.argv[2]
rag_path = sys.argv[3]
pred_path = sys.argv[4]
out_path = sys.argv[5]
mwn_path = sys.argv[6]

dat_tups = [i.strip().split(' ||| ') for i in open(dat_path, 'r').readlines()]
align = list(map(lambda x: [tuple([int(j) for j in i.split('-')])
             for i in x.strip().split(' ')], open(align_path, 'r').readlines()))

pred_map = {}
for i in open(pred_path, 'r').readlines():
    split = i.strip().split(' ')
    if len(split) == 2:
        pred_map[split[0]] = split[1]

rag = ET.parse(rag_path)
sents_xml = rag.getroot()[0]

assert len(dat_tups) == len(align)
assert len(dat_tups) == len(sents_xml)

combos = {}
punks = set([',', '.', '?', '(', ')', ':', '"', "'", ';', '-', '--'])

def tagged_offset(syn):
    return '{:08}{}'.format(syn.offset(), syn.pos())

pending_map_pop_exc = None
for index in range(len(dat_tups)):
    s, t = dat_tups[index]
    s, t = s.split(' '), t.split(' ')
    a = align[index]
    combo = []
    s_to_t = {}
    t_to_s = {}

    # TODO: fix this so that we can recognize contractions
    # for i_index, t_word in enumerate(t):
    #     t_word = t_word.lower()
    #     x_text = sents_xml[index][i_index].text.lower()
    #     if (t_word.replace('\'', '') in x_text) or (x_text.replace('\'', '') in t_word) or (t_word == 'n\'t' and x_text == 'not'):
    #         pass
    #     else:
    #         try:
    #             assert t_word == x_text
    #         except Exception as e:
    #             print(index, i_index, t_word, x_text)
    #             raise e

    for s_i, t_i in a:
        try:
            if s_i in s_to_t:
                s_to_t[s_i].append(t_i)
                s_to_t[s_i] = sorted(s_to_t[s_i])
            else:
                s_to_t[s_i] = [t_i]

            if t_i in t_to_s:
                t_to_s[t_i].append(s_i)
                t_to_s[t_i] = sorted(t_to_s[t_i])
            else:
                t_to_s[t_i] = [s_i]
        except Exception as e:
            print('Line: {}, (S, T) Index: {},'.format(index, (s_i, t_i)))
            raise e

    for _, (k, v) in enumerate(list(s_to_t.items())):
        sent = sents_xml[index]
        combo_map = {}
        combo_map['problematic'] = False
        for v_ in v:
            if v_ >= len(sent):
                combo_map['problematic'] = True
        combo_map['_src'] = [t[v_] for v_ in v]
        combo_map['_tgt'] = s[k]
        try:
            combo_map['lemma'] = [sent[v_].attrib['lemma'] for v_ in v]
            ids = [sent[v_].attrib['id'] if (
                sent[v_].tag == 'instance') else None for v_ in v]
            keys = [pred_map[id] if (id is not None and id in pred_map) else None for id in ids]
            combo_map['id'] = ids
            combo_map['sense_key'] = keys
        except Exception as e:
            pending_map_pop_exc = e
            print(sent.attrib['id'], [w.text for w in sent], v)
            continue

        # source is a punctuation
        if s[k] in punks:
            continue
        # target contains multiple words
        if len(v) > 1:
            continue
        # target contains a punctuation
        if t[v[0]] in punks:
            continue

        # TODO: combine multiple source to one target
        combo.append(combo_map)

    combos[index] = combo

if pending_map_pop_exc is not None:
    raise pending_map_pop_exc

print('Saving projection to:', out_path)
proj = open(out_path, 'w')
_ = json.dump(combos, proj,
              indent=2, ensure_ascii=False)
proj.close()

# remove non sense-aligned
senses_only = {}
sense_keys_to_targets = {}
mwn_offsets = {}
for i in combos.keys():
    line = combos[i]
    for projection in line:
        if not projection['problematic'] and len(projection['id']) == 1 and len(projection['id']) == 1 and projection['sense_key'][0] is not None:
            # TODO: heuristically choose best word for sense key
            key = projection['sense_key'][0]
            tgt = projection['_tgt']
            sense_keys_to_targets[key] = tgt
            try:
                syn = wn.synset_from_sense_key(key)
                en_senses = [s.key() for s in syn.lemmas()]
            except reader.wordnet.WordNetError as e:
                print(projection['id'][0], 'WordNetError:', e)
                continue
            offset = tagged_offset(syn)
            ko_words = [ tgt ]
            if offset in mwn_offsets:
                mwn_offsets[offset] = (mwn_offsets[offset][0], mwn_offsets[offset][1] + ',' + ','.join(ko_words))
            else:
                mwn_offsets[offset] = (','.join(en_senses), ','.join(ko_words))

syns = list(wn.all_synsets())
offsets_list = [(tagged_offset(s), s) for s in syns]
for offset, syn in offsets_list:
    if offset not in mwn_offsets:
        mwn_offsets[offset] = (
            ','.join([s.key() for s in syn.lemmas()]),
            '_NONE_'
        )


def p_to_idx(x):
    return {
        'a': 0,
        'n': 1,
        'v': 2,
        's': 3,
        'r': 4,
    }[x]

lines = []
for offset in sorted(mwn_offsets.keys(), key=lambda x: 1e10 * int(x[:-1]) + p_to_idx(x[-1])):
    cols = []
    cols.append(offset)
    en, ko = mwn_offsets[offset]
    cols.append(en)
    cols.append(ko)
    lines.append('\t'.join(cols) + '\n')

# write to tsv
print('Saving EN-KO Multi-WordNet to:', mwn_path)
mwn = open(mwn_path, 'w')
mwn.writelines(lines)
mwn.close()
