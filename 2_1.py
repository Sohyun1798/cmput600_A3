import json
import sys
import xml.etree.ElementTree as ET

dat_pth = sys.argv[1]
align_pth = sys.argv[2]
out_path = sys.argv[3]
rag_path = 'raganato/en.blind.xml'

if len(sys.argv) < 4:
    print('Invalid command-line arguments')
    exit(1)

dat_tups = [i.strip().split(' ||| ') for i in open(dat_pth, 'r').readlines()]
align = list(map(lambda x: [tuple([int(j) for j in i.split('-')])
             for i in x.strip().split(' ')], open(align_pth, 'r').readlines()))
rag = ET.parse(rag_path)
sents_xml = rag.getroot()[0]

assert len(dat_tups) == len(align)
assert len(dat_tups) == len(sents_xml)

combos = {}
punks = set([',', '.', '?', '(', ')', ':', '"', "'", ';', '-', '--'])

for index in range(len(dat_tups)):
    s, t = dat_tups[index]
    s, t = s.split(' '), t.split(' ')
    a = align[index]
    combo = []
    s_to_t = {}
    t_to_s = {}

    for i_index, t_word in enumerate(t):
        t_word = t_word.lower()
        x_text = sents_xml[index][i_index].text.lower()
        if (t_word.replace('\'', '') in x_text) or (x_text.replace('\'', '') in t_word) or (t_word == 'n\'t' and x_text == 'not'):
            pass
        else:
            assert t_word == x_text

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
        combo_map = {}
        combo_map['src'] = s[k]
        combo_map['tgt'] = [t[v_] for v_ in v]
        combo_map['lemma'] = [sents_xml[index][v_].attrib['lemma'] for v_ in v]
        combo_map['id'] = [sents_xml[index][v_].attrib['id'] if (
            sents_xml[index][v_].tag == 'instance') else None for v_ in v]

        # source is a punctuation
        if s[k] in punks:
            continue
        # target contains multiple words
        if len(v) > 1:
            continue
        # target contains a punctuation
        if t[v[0]] in punks:
            continue

        # TODO: Combine multiple source to one target
        combo.append(combo_map)

    combos[index] = combo

_ = json.dump(combos, open(out_path, 'w'),
              indent=2, ensure_ascii=False)
